"""Durable report checkpoints and capacity-led continuation decisions."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import continuation_state  # noqa: E402


class ContinuationStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run_dir = Path(self.temp.name)
        self.manifest = {
            'query': 'Which approach works?', 'mode': 'deep',
            'artifact_paths': {'sources': 'sources.jsonl', 'evidence': 'evidence.jsonl',
                               'claims': 'claims.jsonl', 'queries': 'queries.jsonl',
                               'coverage': 'coverage.json', 'report': 'report.md'},
            'reporting': {'output_mode': 'markdown', 'final_report_path': 'report.md',
                          'dossiers': [{'id': 'dossier-a', 'path': 'dossiers/a.md',
                                        'facet_ids': ['facet-a'], 'status': 'complete'},
                                       {'id': 'dossier-b', 'path': 'dossiers/b.md',
                                        'facet_ids': ['facet-b'], 'status': 'draft'}]},
        }
        (self.run_dir / 'run_manifest.json').write_text(json.dumps(self.manifest))

    def ready_progress(self):
        self.manifest['reporting']['dossiers'][1]['status'] = 'complete'
        (self.run_dir / 'run_manifest.json').write_text(json.dumps(self.manifest))
        return {
            'completed_sections': ['final:synthesis'], 'open_gaps': [],
            'next_task': None, 'words_generated': 1200,
            'required_worker_ids': ['worker-a'],
            'worker_returns': [{'worker_id': 'worker-a', 'status': 'complete',
                                'joined': True}],
            'final_validation': {name: 'passed' for name in
                                 continuation_state.REQUIRED_VALIDATION_CHECKS},
            'delivery_status': 'complete',
        }

    def test_null_next_task_waits_for_required_join(self):
        progress = self.ready_progress()
        progress['worker_returns'][0]['joined'] = False
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        decision = continuation_state.select_action(state)
        self.assertEqual(decision['action'], 'blocked')
        self.assertIn('worker-a', decision['blockers'][0])

    def test_null_next_task_requires_validation_and_rejects_failed_check(self):
        progress = self.ready_progress()
        progress['final_validation']['package'] = 'unrun'
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(continuation_state.select_action(state)['action'], 'validate')
        progress['final_validation']['package'] = 'failed'
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        decision = continuation_state.select_action(state)
        self.assertEqual(decision['action'], 'blocked')
        self.assertIn('package', decision['blockers'][0])

    def test_null_next_task_rejects_draft_dossier_and_open_gap(self):
        progress = self.ready_progress()
        self.manifest['reporting']['dossiers'][1]['status'] = 'draft'
        (self.run_dir / 'run_manifest.json').write_text(json.dumps(self.manifest))
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(continuation_state.select_action(state)['action'], 'blocked')
        self.manifest['reporting']['dossiers'][1]['status'] = 'complete'
        (self.run_dir / 'run_manifest.json').write_text(json.dumps(self.manifest))
        progress['open_gaps'] = [{'facet_id': 'facet-b', 'question': 'unknown'}]
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(continuation_state.select_action(state)['action'], 'blocked')

    def test_complete_and_truthful_budget_partial_are_distinct(self):
        progress = self.ready_progress()
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(continuation_state.select_action(state)['action'], 'complete')
        progress['open_gaps'] = [{'facet_id': 'facet-b', 'question': 'unknown'}]
        progress['delivery_status'] = 'partial'
        progress['retrieval_stop_reason'] = 'budget-exhausted'
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(continuation_state.select_action(state)['action'], 'partial')

    def test_resume_when_final_checks_pending(self):
        progress = self.ready_progress()
        progress['final_validation']['package'] = 'unrun'
        continuation_state.save_checkpoint(self.run_dir, progress)
        resumed = continuation_state.begin_new_stretch(self.run_dir)
        self.assertEqual(resumed['words_generated'], 0)
        self.assertEqual(resumed['final_validation']['package'], 'unrun')
        self.assertEqual(continuation_state.select_action(resumed)['action'], 'validate')

    def test_later_checkpoint_cannot_silently_drop_required_worker_ids(self):
        progress = self.ready_progress()
        progress['worker_returns'] = []
        continuation_state.save_checkpoint(self.run_dir, progress)
        progress.pop('required_worker_ids')
        progress.pop('worker_returns')
        state = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(state['required_worker_ids'], ['worker-a'])
        self.assertEqual(continuation_state.select_action(state)['action'], 'blocked')

    def test_checkpoint_preserves_canonical_artifacts_and_completed_dossier(self):
        progress = {'completed_sections': ['dossier-a:summary'],
                    'open_gaps': [{'facet_id': 'facet-b', 'question': 'Missing evidence?'}],
                    'next_task': {'id': 'dossier-b:findings', 'path': 'dossiers/b.md',
                                  'facet_ids': ['facet-b'], 'goal': 'Draft supported findings'},
                    'words_generated': 2100}
        saved = continuation_state.save_checkpoint(self.run_dir, progress)
        resumed = continuation_state.load_checkpoint(self.run_dir)
        self.assertEqual(resumed, saved)
        self.assertEqual(resumed['artifacts']['coverage'], 'coverage.json')
        self.assertEqual(resumed['artifacts']['queries'], 'queries.jsonl')
        self.assertEqual(resumed['artifacts']['run_manifest'], 'run_manifest.json')
        self.assertEqual(resumed['artifacts']['final_report'], 'report.md')
        self.assertEqual(resumed['dossiers'][0]['status'], 'complete')
        self.assertEqual(resumed['completed_sections'], ['dossier-a:summary'])
        self.assertEqual(resumed['next_task']['id'], 'dossier-b:findings')
        self.assertNotIn('citations', resumed)

    def test_capacity_signal_overrides_word_fallback(self):
        state = {'words_generated': 19000, 'next_task': {'id': 'final:synthesis'}}
        self.assertEqual(continuation_state.select_action(
            state, available_words=5000, estimated_next_words=1000,
            subagents_available=True)['action'], 'continue')
        result = continuation_state.select_action(
            state, available_words=800, estimated_next_words=1000,
            subagents_available=True)
        self.assertEqual((result['action'], result['mechanism']), ('handoff', 'subagent'))

    def test_fallback_only_without_capacity_signal(self):
        state = {'words_generated': 17999, 'next_task': {'id': 'final:synthesis'}}
        self.assertEqual(continuation_state.select_action(state)['action'], 'continue')
        state['words_generated'] = 18000
        result = continuation_state.select_action(state)
        self.assertEqual((result['action'], result['mechanism']),
                         ('handoff', 'sequential-resume'))
        self.assertEqual(result['basis'], 'word-fallback')

    def test_subagent_unavailable_uses_sequential_resume(self):
        state = {'words_generated': 100, 'next_task': {'id': 'dossier-b:findings'}}
        result = continuation_state.select_action(
            state, available_words=0, estimated_next_words=1000,
            subagents_available=False)
        self.assertEqual((result['action'], result['mechanism']),
                         ('handoff', 'sequential-resume'))

    def test_resume_starts_new_stretch_and_preserves_previous_count(self):
        progress = {'completed_sections': ['dossier-a:summary'], 'open_gaps': [],
                    'next_task': {'id': 'dossier-b:findings'}, 'words_generated': 18000}
        continuation_state.save_checkpoint(self.run_dir, progress)
        resumed = continuation_state.begin_new_stretch(self.run_dir)
        self.assertEqual(resumed['words_generated'], 0)
        self.assertEqual(resumed['completed_stretches'][0]['words_generated'], 18000)
        self.assertEqual(resumed['completed_stretches'][0]['next_task']['id'],
                         'dossier-b:findings')
        self.assertEqual(continuation_state.select_action(resumed)['action'], 'continue')
        self.assertEqual(continuation_state.load_checkpoint(self.run_dir), resumed)
        progress['words_generated'] = 50
        after_save = continuation_state.save_checkpoint(self.run_dir, progress)
        self.assertEqual(after_save['completed_stretches'], resumed['completed_stretches'])
        self.assertEqual(after_save['words_generated'], 50)

    def test_cli_resume_after_fallback_handoff(self):
        progress = {'completed_sections': [], 'open_gaps': [],
                    'next_task': {'id': 'final:synthesis'}, 'words_generated': 18000}
        continuation_state.save_checkpoint(self.run_dir, progress)
        command = [sys.executable, str(ROOT / 'scripts/continuation_state.py')]
        resumed = subprocess.run(command + ['resume', '--dir', str(self.run_dir)],
                                 capture_output=True, text=True)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        decided = subprocess.run(command + ['decide', '--dir', str(self.run_dir)],
                                 capture_output=True, text=True)
        self.assertEqual(json.loads(decided.stdout)['action'], 'continue')

    def test_cli_save_and_decide_uses_saved_checkpoint(self):
        progress = self.run_dir / 'progress.json'
        progress.write_text(json.dumps({
            'completed_sections': [], 'open_gaps': [],
            'next_task': {'id': 'dossier-a:summary', 'path': 'dossiers/a.md',
                          'facet_ids': ['facet-a'], 'goal': 'Summarize evidence'},
            'words_generated': 18000}))
        command = [sys.executable, str(ROOT / 'scripts/continuation_state.py')]
        saved = subprocess.run(command + ['save', '--dir', str(self.run_dir),
                                          '--progress-json', str(progress)],
                               capture_output=True, text=True)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        decided = subprocess.run(command + ['decide', '--dir', str(self.run_dir)],
                                 capture_output=True, text=True)
        self.assertEqual(decided.returncode, 0, decided.stderr)
        self.assertEqual(json.loads(decided.stdout)['mechanism'], 'sequential-resume')


if __name__ == '__main__':
    unittest.main()
