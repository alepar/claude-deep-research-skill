"""End-to-end structural checks for saved coverage decisions."""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest


ROOT = os.path.dirname(os.path.dirname(__file__))
VERIFY = os.path.join(ROOT, 'scripts', 'verify_coverage.py')
INIT = os.path.join(ROOT, 'scripts', 'citation_manager.py')
SOURCE = hashlib.sha256(b'https://example.org/study').hexdigest()[:16]
EVIDENCE = 'a' * 16


def write_json(path, value):
    with open(path, 'w') as f:
        json.dump(value, f)


def write_jsonl(path, rows):
    with open(path, 'w') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')


class TestVerifyCoverage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name
        subprocess.run([sys.executable, INIT, 'init-run', '--out-dir', self.dir,
                        '--query', 'Which approach works?'], check=True, capture_output=True)
        self.manifest = self.read('run_manifest.json')
        self.stop = {'reason': 'coverage-saturated', 'at': '2026-10-03T12:00:00Z',
                     'round': 3, 'unresolved_high_priority_facet_ids': [],
                     'remaining_gaps': [], 'basis': 'Two residual probes found no new evidence.'}
        self.coverage = {
            'schema_version': 1, 'question': 'Which approach works?',
            'initial_facets': [{'id': 'F1', 'question': 'What works?', 'priority': 'high'}],
            'facets': [{'id': 'F1', 'question': 'What works?', 'priority': 'high',
                        'source_types': ['primary documentation'], 'status': 'supported',
                        'active': True, 'query_ids': ['Q1', 'Q2', 'Q3'],
                        'evidence_ids': [EVIDENCE], 'contested_positions': [],
                        'counterevidence': 'searched-none-found', 'gap_note': '',
                        'scope_change': None}],
            'completed_rounds': [
                {'round': 1, 'query_ids': ['Q1'], 'families': ['literal'],
                 'target_high_priority_facet_ids': ['F1'], 'new_relevant_source_ids': [SOURCE],
                 'material_changes': [{'facet_id': 'F1', 'kind': 'status',
                                       'before': 'unsearched', 'after': 'supported'}],
                 'coverage_ready_after': True},
                {'round': 2, 'query_ids': ['Q2'], 'families': ['synonym'],
                 'target_high_priority_facet_ids': ['F1'], 'new_relevant_source_ids': [],
                 'material_changes': [], 'coverage_ready_after': True},
                {'round': 3, 'query_ids': ['Q3'], 'families': ['counterevidence'],
                 'target_high_priority_facet_ids': ['F1'], 'new_relevant_source_ids': [],
                 'material_changes': [], 'coverage_ready_after': True},
            ], 'stop': self.stop,
        }
        self.queries = [
            {'query_id': f'Q{i}', 'round': i, 'facet_ids': ['F1'], 'gap': 'Check evidence',
             'family': family, 'query': f'query {i}', 'provider': 'search-cli',
             'expected_evidence': 'Direct source', 'result_source_ids': results,
             'new_relevant_source_ids': results, 'coverage_changed': i == 1, 'notes': ''}
            for i, family, results in ((1, 'literal', [SOURCE]), (2, 'synonym', []),
                                       (3, 'counterevidence', []))
        ]
        self.sources = [{'source_id': SOURCE, 'canonical_locator': 'https://example.org/study'}]
        self.evidence = [{'evidence_id': EVIDENCE, 'source_id': SOURCE}]
        self.manifest['retrieval_stop'] = copy.deepcopy(self.stop)
        self.save()

    def read(self, name):
        with open(os.path.join(self.dir, name)) as f:
            return json.load(f)

    def save(self):
        write_json(os.path.join(self.dir, 'run_manifest.json'), self.manifest)
        write_json(os.path.join(self.dir, 'coverage.json'), self.coverage)
        write_jsonl(os.path.join(self.dir, 'queries.jsonl'), self.queries)
        write_jsonl(os.path.join(self.dir, 'sources.jsonl'), self.sources)
        write_jsonl(os.path.join(self.dir, 'evidence.jsonl'), self.evidence)

    def check(self):
        self.save()
        proc = subprocess.run([sys.executable, VERIFY, '--dir', self.dir],
                              capture_output=True, text=True)
        return proc.returncode, json.loads(proc.stdout)

    def assert_invalid(self, fragment):
        code, result = self.check()
        self.assertNotEqual(code, 0)
        self.assertEqual(result['status'], 'invalid')
        self.assertIn(fragment, ' '.join(result['errors']))

    def test_complete_loop_accepts_saturated_stop(self):
        code, result = self.check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)

    def test_saturation_requires_initial_facet_snapshot(self):
        self.coverage['initial_facets'] = []
        self.assert_invalid('initial_facets')

    def test_query_coverage_change_cannot_be_hidden_in_low_yield_round(self):
        self.queries[2]['coverage_changed'] = True
        self.assert_invalid('coverage_changed')

    def test_malformed_facet_row_returns_json_invalid(self):
        self.coverage['facets'] = ['oops']
        self.assert_invalid('facet')

    def test_old_run_reports_missing(self):
        os.remove(os.path.join(self.dir, 'coverage.json'))
        os.remove(os.path.join(self.dir, 'queries.jsonl'))
        proc = subprocess.run([sys.executable, VERIFY, '--dir', self.dir],
                              capture_output=True, text=True)
        self.assertEqual(json.loads(proc.stdout)['status'], 'missing')

    def test_duplicate_query_id_rejected(self):
        self.queries.append(copy.deepcopy(self.queries[0]))
        self.assert_invalid('duplicate query_id')

    def test_unknown_evidence_and_source_rejected(self):
        self.coverage['facets'][0]['evidence_ids'] = ['f' * 16]
        self.queries[0]['new_relevant_source_ids'] = ['b' * 16]
        self.assert_invalid('unknown evidence')
        self.assert_invalid('unknown source')

    def test_premature_saturation_rejected(self):
        for status, evidence_ids, counter in [
            ('unsearched', [], 'unchecked'), ('searched', [], 'searched-none-found'),
            ('supported', [EVIDENCE], 'unchecked')]:
            with self.subTest(status=status, counter=counter):
                self.coverage['facets'][0].update(status=status, evidence_ids=evidence_ids,
                                                  counterevidence=counter)
                self.assert_invalid('coverage-saturated')

    def test_contested_side_requires_evidence(self):
        self.coverage['facets'][0].update(status='contested', gap_note='Sources disagree',
            contested_positions=[{'position': 'yes', 'evidence_ids': [EVIDENCE]},
                                 {'position': 'no', 'evidence_ids': []}])
        self.assert_invalid('contested')

    def test_initial_facet_cannot_disappear_or_demote_silently(self):
        self.coverage['facets'] = []
        self.assert_invalid('initial facet F1')
        self.coverage['facets'] = [copy.deepcopy(self.coverage_base_facet())]
        self.coverage['facets'][0]['priority'] = 'supporting'
        self.assert_invalid('scope_change')

    def coverage_base_facet(self):
        return {'id': 'F1', 'question': 'What works?', 'priority': 'high',
                'source_types': ['primary documentation'], 'status': 'supported',
                'active': True, 'query_ids': ['Q1', 'Q2', 'Q3'],
                'evidence_ids': [EVIDENCE], 'contested_positions': [],
                'counterevidence': 'searched-none-found', 'gap_note': '',
                'scope_change': None}

    def test_round_summary_must_match_queries_and_sources(self):
        self.coverage['completed_rounds'][2]['families'] = ['literal']
        self.assert_invalid('families')
        self.coverage['completed_rounds'][2]['families'] = ['counterevidence']
        self.coverage['completed_rounds'][0]['new_relevant_source_ids'] = []
        self.assert_invalid('new_relevant_source_ids')

    def test_residual_rounds_must_follow_readiness(self):
        self.coverage['completed_rounds'][0]['coverage_ready_after'] = False
        self.assert_invalid('after readiness')

    def test_two_low_yield_rounds_need_distinct_families(self):
        self.queries[2]['family'] = 'synonym'
        self.coverage['completed_rounds'][2]['families'] = ['synonym']
        self.assert_invalid('distinct families')

    def test_shared_family_in_both_residual_rounds_is_insufficient(self):
        self.queries[1]['family'] = 'literal'
        self.coverage['completed_rounds'][1]['families'] = ['literal']
        self.coverage['completed_rounds'][2]['families'] = ['literal', 'counterevidence']
        extra = copy.deepcopy(self.queries[2])
        extra['query_id'] = 'Q4'
        extra['family'] = 'literal'
        self.queries.append(extra)
        self.coverage['completed_rounds'][2]['query_ids'].append('Q4')
        self.coverage['facets'][0]['query_ids'].append('Q4')
        self.assert_invalid('distinct families')

    def test_material_change_after_value_must_match_current_facet(self):
        self.coverage['completed_rounds'][0]['material_changes'][0]['after'] = 'unresolved'
        self.assert_invalid('material_changes')

    def test_new_source_or_material_change_resets_saturation(self):
        self.queries[2]['result_source_ids'] = [SOURCE]
        self.queries[2]['new_relevant_source_ids'] = [SOURCE]
        self.coverage['completed_rounds'][2]['new_relevant_source_ids'] = [SOURCE]
        self.assert_invalid('low-yield')
        self.queries[2]['new_relevant_source_ids'] = []
        self.coverage['completed_rounds'][2]['new_relevant_source_ids'] = []
        self.coverage['completed_rounds'][2]['material_changes'] = [
            {'facet_id': 'F1', 'kind': 'counterevidence',
             'before': 'unchecked', 'after': 'searched-none-found'}]
        self.assert_invalid('low-yield')

    def test_budget_stop_records_unresolved_gaps(self):
        self.stop.update(reason='budget-exhausted', round=1,
                         unresolved_high_priority_facet_ids=['F1'],
                         remaining_gaps=['F1: no direct evidence'])
        self.manifest['retrieval_stop'] = copy.deepcopy(self.stop)
        self.coverage['completed_rounds'] = self.coverage['completed_rounds'][:1]
        self.coverage['completed_rounds'][0]['material_changes'][0]['after'] = 'unresolved'
        self.coverage['completed_rounds'][0]['coverage_ready_after'] = False
        self.queries = self.queries[:1]
        self.coverage['facets'][0].update(query_ids=['Q1'], status='unresolved',
                                          evidence_ids=[], counterevidence='unchecked',
                                          gap_note='No direct evidence')
        code, result = self.check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)
        self.stop['remaining_gaps'] = []
        self.manifest['retrieval_stop'] = copy.deepcopy(self.stop)
        self.assert_invalid('remaining_gaps')


if __name__ == '__main__':
    unittest.main()
