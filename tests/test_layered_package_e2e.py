"""One registered two-facet run through coverage, support, and delivery checks."""

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

from tests import test_verify_coverage as coverage_fixture


ROOT = Path(__file__).resolve().parents[1]
SOURCE_A = coverage_fixture.SOURCE
EVIDENCE_A = coverage_fixture.EVIDENCE
SOURCE_B = hashlib.sha256(b'https://example.org/second').hexdigest()[:16]
EVIDENCE_B = 'b' * 16
CLAIM_A = 'c' * 16
CLAIM_B = 'd' * 16
CLAIM_FINAL = 'e' * 16
CLAIM_FINAL_B = 'f' * 16
CLAIM_SYNTHESIS = '0' * 16


def marker(claim, evidence, source):
    return f'<!-- claim: {claim}; evidence: {evidence}; source: {source} -->'


class LayeredPackageEndToEnd(unittest.TestCase):
    def setUp(self):
        # The coverage fixture starts with an initialized run and a valid stop.
        self.base = coverage_fixture.TestVerifyCoverage('test_complete_loop_accepts_saturated_stop')
        self.base.setUp()
        self.addCleanup(self.base.doCleanups)
        self.path = Path(self.base.dir)
        f2 = dict(self.base.coverage['facets'][0])
        f2.update(id='F2', question='What does the second source show?',
                  evidence_ids=[EVIDENCE_B])
        self.base.coverage['facets'].append(f2)
        self.base.coverage['initial_facets'].append(
            {'id': 'F2', 'question': f2['question'], 'priority': 'high'})
        self.base.sources.append({
            'source_id': SOURCE_B, 'canonical_locator': 'https://example.org/second',
            'raw_url': 'https://example.org/second', 'title': 'Second study'})
        self.base.sources[0].update(raw_url='https://example.org/study',
                                    title='First study')
        self.base.evidence[0]['quote'] = (
            'The first approach improved access; reliability was not measured.')
        self.base.evidence.append({'evidence_id': EVIDENCE_B, 'source_id': SOURCE_B,
                                   'quote': ('The second approach improved reliability; '
                                             'access was not measured.')})
        for query in self.base.queries:
            query['facet_ids'].append('F2')
        # The base fixture intentionally shares its result list across fields.
        self.base.queries[1]['result_source_ids'] = [SOURCE_A, SOURCE_B]
        self.base.queries[1]['new_relevant_source_ids'] = [SOURCE_A, SOURCE_B]
        for completed in self.base.coverage['completed_rounds']:
            completed['target_high_priority_facet_ids'].append('F2')
        self.base.coverage['completed_rounds'][0]['new_relevant_source_ids'].append(SOURCE_B)
        self.base.coverage['completed_rounds'][0]['material_changes'].extend([
            {'facet_id': 'F2', 'kind': 'status', 'before': 'unsearched',
             'after': 'supported'},
            {'facet_id': 'F2', 'kind': 'counterevidence', 'before': 'unchecked',
             'after': 'searched-none-found'},
        ])
        self.base.manifest['reporting'] = {
            'output_mode': 'markdown', 'requested_formats': [],
            'final_report_path': 'report.md',
            'dossiers': [
                {'id': 'first', 'path': 'dossiers/first.md', 'facet_ids': ['F1'],
                 'source_ids': [SOURCE_A], 'evidence_ids': [EVIDENCE_A],
                 'claim_ids': [CLAIM_A], 'status': 'complete'},
                {'id': 'second', 'path': 'dossiers/second.md', 'facet_ids': ['F2'],
                 'source_ids': [SOURCE_B], 'evidence_ids': [EVIDENCE_B],
                 'claim_ids': [CLAIM_B], 'status': 'complete'},
            ],
        }
        self.base.save()
        claims = [
            {'claim_id': CLAIM_A, 'section_id': 'first:findings',
             'text': 'The first approach improved access.', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_A], 'cited_source_ids': [SOURCE_A],
             'support_status': 'unverified'},
            {'claim_id': CLAIM_B, 'section_id': 'second:findings',
             'text': 'The second approach improved reliability.', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_B], 'cited_source_ids': [SOURCE_B],
             'support_status': 'unverified'},
            {'claim_id': CLAIM_FINAL, 'section_id': 'final:synthesis',
             'text': 'The first approach improved access.', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_A], 'cited_source_ids': [SOURCE_A],
             'support_status': 'unverified'},
            {'claim_id': CLAIM_FINAL_B, 'section_id': 'final:synthesis',
             'text': 'The second approach improved reliability.',
             'claim_type': 'factual', 'evidence_ids': [EVIDENCE_B],
             'cited_source_ids': [SOURCE_B], 'support_status': 'unverified'},
            {'claim_id': CLAIM_SYNTHESIS, 'section_id': 'final:synthesis',
             'text': ('The first approach improved access but did not measure '
                      'reliability; the second improved reliability but did not '
                      'measure access, so neither study establishes an overall winner.'),
             'claim_type': 'synthesis',
             'evidence_ids': [EVIDENCE_A, EVIDENCE_B],
             'cited_source_ids': [SOURCE_A, SOURCE_B],
             'support_status': 'unverified'},
        ]
        (self.path / 'claims.jsonl').write_text(
            ''.join(json.dumps(row) + '\n' for row in claims))
        dossiers = self.path / 'dossiers'
        dossiers.mkdir()
        (dossiers / 'first.md').write_text(
            '# Access\n\nThe first approach improved access [1]. ' +
            marker(CLAIM_A, EVIDENCE_A, SOURCE_A) +
            '\n\n## Bibliography\n\n[1] [First study](https://example.org/study)\n')
        (dossiers / 'second.md').write_text(
            '# Reliability\n\nThe second approach improved reliability [2]. ' +
            marker(CLAIM_B, EVIDENCE_B, SOURCE_B) +
            '\n\n## Bibliography\n\n[2] [Second study](https://example.org/second)\n')
        (self.path / 'report.md').write_text(
            '# Decision\n\nThe first approach improved access [1]. ' +
            marker(CLAIM_FINAL, EVIDENCE_A, SOURCE_A) +
            '\n\nThe second approach improved reliability [2]. ' +
            marker(CLAIM_FINAL_B, EVIDENCE_B, SOURCE_B) + '\n'
            '\n## Synthesis\n\nThe access study did not measure '
            'reliability [1]. ' + marker(CLAIM_SYNTHESIS, EVIDENCE_A, SOURCE_A) +
            '\nThe reliability study did not measure access [2]. ' +
            marker(CLAIM_SYNTHESIS, EVIDENCE_B, SOURCE_B) +
            '\nNeither study establishes an overall winner. Prioritize the '
            'outcome that matters more to the decision before choosing an approach.\n'
            '<!-- facet: F1 -->\n<!-- facet: F2 -->\n'
            'Evidence: [Access](dossiers/first.md) and '
            '[Reliability](dossiers/second.md).\n'
            '\n## Bibliography\n\n[1] [First study](https://example.org/study)\n'
            '[2] [Second study](https://example.org/second)\n')

    def run_script(self, name, *args):
        return subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *args],
                              capture_output=True, text=True)

    def test_registered_sources_to_two_dossiers_and_final(self):
        coverage = self.run_script('verify_coverage.py', '--dir', str(self.path))
        self.assertEqual(coverage.returncode, 0, coverage.stdout + coverage.stderr)
        support = self.run_script('verify_claim_support.py', 'verify',
                                  '--dir', str(self.path), '--strict')
        self.assertEqual(support.returncode, 0, support.stdout + support.stderr)
        for relative in ('dossiers/first.md', 'dossiers/second.md', 'report.md'):
            surface = self.run_script('validate_report.py', '--report',
                                      str(self.path / relative))
            self.assertEqual(surface.returncode, 0, relative + ': ' + surface.stdout)
        package = self.run_script('validate_report_package.py', '--dir', str(self.path))
        self.assertEqual(package.returncode, 0, package.stdout + package.stderr)

    def test_final_synthesis_traces_to_both_original_sources(self):
        support = self.run_script('verify_claim_support.py', 'verify',
                                  '--dir', str(self.path), '--strict')
        self.assertEqual(support.returncode, 0, support.stdout + support.stderr)
        claims = [json.loads(line) for line in
                  (self.path / 'claims.jsonl').read_text().splitlines()]
        synthesis = next(c for c in claims if c['claim_id'] == CLAIM_SYNTHESIS)
        self.assertEqual(synthesis['claim_type'], 'synthesis')
        self.assertEqual(synthesis['support_status'], 'supported')
        self.assertEqual(set(synthesis['evidence_ids']), {EVIDENCE_A, EVIDENCE_B})
        self.assertEqual(set(synthesis['cited_source_ids']), {SOURCE_A, SOURCE_B})
        final = (self.path / 'report.md').read_text()
        self.assertIn(marker(CLAIM_SYNTHESIS, EVIDENCE_A, SOURCE_A), final)
        self.assertIn(marker(CLAIM_SYNTHESIS, EVIDENCE_B, SOURCE_B), final)

    def test_final_cannot_cite_dossier_as_original_source(self):
        support = self.run_script('verify_claim_support.py', 'verify',
                                  '--dir', str(self.path), '--strict')
        self.assertEqual(support.returncode, 0, support.stdout)
        report = self.path / 'report.md'
        report.write_text(report.read_text().replace(
            f'source: {SOURCE_A}', 'source: dossiers/first.md'))
        package = self.run_script('validate_report_package.py', '--dir', str(self.path))
        self.assertNotEqual(package.returncode, 0)
        self.assertIn('unknown source', package.stdout)


if __name__ == '__main__':
    unittest.main()
