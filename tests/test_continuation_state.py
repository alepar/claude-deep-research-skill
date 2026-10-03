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
