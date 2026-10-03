"""Structural checks for a delivered final report and its facet dossiers."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'validate_report_package.py'
SOURCE_A = 'a' * 16
SOURCE_B = 'b' * 16
EVIDENCE_A = 'c' * 16
EVIDENCE_B = 'd' * 16
CLAIM_A = 'e' * 16
CLAIM_B = 'f' * 16


def marker(claim, evidence, source):
    return f'<!-- claim: {claim}; evidence: {evidence}; source: {source} -->'


class TestReportPackage(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.manifest = {
            'version': '3.0.0', 'query': 'Which approach works?', 'mode': 'deep',
            'started_at': '2026-10-03T12:00:00Z', 'report_dir': str(self.dir),
            'artifact_paths': {'sources': 'sources.jsonl', 'evidence': 'evidence.jsonl',
                               'claims': 'claims.jsonl', 'report': 'report.md',
                               'coverage': 'coverage.json', 'queries': 'queries.jsonl'},
            'reporting': {
                'output_mode': 'markdown', 'final_report_path': 'report.md',
                'dossiers': [
                    {'id': 'dossier-alpha', 'path': 'dossiers/alpha.md',
                     'facet_ids': ['facet/alpha'], 'source_ids': [SOURCE_A],
                     'evidence_ids': [EVIDENCE_A], 'claim_ids': [CLAIM_A],
                     'status': 'complete'},
                    {'id': 'dossier-beta', 'path': 'dossiers/beta.md',
                     'facet_ids': ['facet-beta'], 'source_ids': [SOURCE_B],
                     'evidence_ids': [EVIDENCE_B], 'claim_ids': [CLAIM_B],
                     'status': 'complete'},
                ],
            },
        }
        self.coverage = {'initial_facets': [
            {'id': 'facet/alpha', 'priority': 'high', 'question': 'Alpha?'},
            {'id': 'facet-beta', 'priority': 'high', 'question': 'Beta?'},
        ], 'facets': [
            {'id': 'facet/alpha', 'priority': 'high', 'active': True, 'status': 'supported'},
            {'id': 'facet-beta', 'priority': 'high', 'active': True, 'status': 'supported'},
        ]}
        self.sources = [
            {'source_id': SOURCE_A, 'title': 'Alpha source',
             'raw_url': 'https://example.org/alpha'},
            {'source_id': SOURCE_B, 'title': 'Beta source',
             'raw_url': 'https://example.org/beta'},
        ]
        self.evidence = [{'evidence_id': EVIDENCE_A, 'source_id': SOURCE_A},
                         {'evidence_id': EVIDENCE_B, 'source_id': SOURCE_B}]
        self.claims = [
            {'claim_id': CLAIM_A, 'section_id': 'dossier-alpha:findings',
             'support_status': 'supported', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_A], 'cited_source_ids': [SOURCE_A]},
            {'claim_id': CLAIM_B, 'section_id': 'dossier-beta:findings',
             'support_status': 'supported', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_B], 'cited_source_ids': [SOURCE_B]},
            {'claim_id': '1' * 16, 'section_id': 'final:synthesis',
             'support_status': 'supported', 'claim_type': 'factual',
             'evidence_ids': [EVIDENCE_A], 'cited_source_ids': [SOURCE_A]},
        ]
        self.final = ('# Decision\n\nAlpha is supported [1]. '
                      + marker('1' * 16, EVIDENCE_A, SOURCE_A)
                      + '\n\n<!-- facet: facet/alpha -->\n<!-- facet: facet-beta -->\n'
                      + '\nSee [Alpha](dossiers/alpha.md) and [Beta](dossiers/beta.md).\n'
                      + '\n## Bibliography\n\n'
                      + '[1] [Alpha source](https://example.org/alpha).\n')
        self.alpha = ('# Alpha\n\nAlpha works [1]. '
                      + marker(CLAIM_A, EVIDENCE_A, SOURCE_A)
                      + '\n\n## Bibliography\n\n[1] [Alpha source](https://example.org/alpha)\n')
        self.beta = ('# Beta\n\nBeta works [2]. '
                     + marker(CLAIM_B, EVIDENCE_B, SOURCE_B)
                     + '\n\n## Bibliography\n\n[2] [Beta source](https://example.org/beta)\n')

    def save(self):
        (self.dir / 'run_manifest.json').write_text(json.dumps(self.manifest))
        (self.dir / 'coverage.json').write_text(json.dumps(self.coverage))
        for name, rows in [('sources', self.sources), ('evidence', self.evidence),
                           ('claims', self.claims)]:
            (self.dir / (name + '.jsonl')).write_text(
                ''.join(json.dumps(row) + '\n' for row in rows))
        (self.dir / 'report.md').write_text(self.final)
        (self.dir / 'dossiers').mkdir(exist_ok=True)
        (self.dir / 'dossiers/alpha.md').write_text(self.alpha)
        (self.dir / 'dossiers/beta.md').write_text(self.beta)

    def run_check(self):
        self.save()
        result = subprocess.run([sys.executable, str(SCRIPT), '--dir', str(self.dir)],
                                text=True, capture_output=True)
        return result.returncode, json.loads(result.stdout)

    def assert_invalid(self, fragment):
        code, result = self.run_check()
        self.assertNotEqual(code, 0, result)
        self.assertEqual(result['status'], 'invalid')
        self.assertIn(fragment, '\n'.join(result['errors']))

    def test_two_dossiers_and_direct_final_source_validate(self):
        code, result = self.run_check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)

    def test_old_quick_manifest_without_reporting_is_accepted(self):
        self.manifest['mode'] = 'quick'
        del self.manifest['reporting']
        code, result = self.run_check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)

    def test_markdown_package_can_request_both_html_and_pdf(self):
        self.manifest['reporting']['requested_formats'] = ['html', 'pdf']
        code, result = self.run_check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)

    def test_requested_formats_rejects_duplicates_and_unknown_values(self):
        for formats in (['html', 'html'], ['html', 'docx'], 'html'):
            with self.subTest(formats=formats):
                self.manifest['reporting']['requested_formats'] = formats
                self.assert_invalid('requested_formats')

    def test_requested_formats_alone_requires_a_report_package_in_schema_and_validator(self):
        self.manifest['reporting'] = {'requested_formats': ['html']}
        self.assert_invalid('output_mode')
        schema = json.loads((ROOT / 'schemas/run_manifest.schema.json').read_text())
        dependencies = schema['properties']['reporting']['dependentRequired']
        self.assertEqual(set(dependencies['requested_formats']),
                         {'output_mode', 'final_report_path', 'dossiers'})

    def test_duplicate_dossier_id_fails(self):
        self.manifest['reporting']['dossiers'][1]['id'] = 'dossier-alpha'
        self.assert_invalid('duplicate dossier ID')

    def test_unknown_references_fail(self):
        for field, value, fragment in [('facet_ids', 'missing-facet', 'unknown facet'),
                                       ('source_ids', '0' * 16, 'unknown source'),
                                       ('evidence_ids', '0' * 16, 'unknown evidence'),
                                       ('claim_ids', '0' * 16, 'unknown claim')]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.manifest['reporting']['dossiers'][0][field])
                self.manifest['reporting']['dossiers'][0][field] = [value]
                self.assert_invalid(fragment)
                self.manifest['reporting']['dossiers'][0][field] = original

    def test_path_traversal_fails_even_when_file_exists(self):
        self.manifest['reporting']['dossiers'][0]['path'] = '../outside.md'
        self.assert_invalid('relative path')

    def test_missing_dossier_link_fails(self):
        self.final = self.final.replace('[Beta](dossiers/beta.md)', 'Beta')
        self.assert_invalid('missing link')

    def test_external_markdown_source_link_is_not_package_path(self):
        self.final += '\n[Source readme](https://example.org/project/README.md)\n'
        code, result = self.run_check()
        self.assertEqual((code, result['status']), (0, 'ok'), result)

    def test_missing_active_high_facet_fails(self):
        self.final = self.final.replace('<!-- facet: facet-beta -->', '')
        self.assert_invalid('omits active high-priority facet')

    def test_unknown_or_unsupported_final_claim_fails(self):
        self.claims[-1]['support_status'] = 'needs_review'
        self.assert_invalid('not supported')
        self.claims[-1]['support_status'] = 'supported'
        self.final = self.final.replace('1' * 16, '9' * 16)
        self.assert_invalid('unknown claim')

    def test_final_cannot_cite_dossier_as_original_source(self):
        self.claims[-1]['cited_source_ids'] = []
        self.final = self.final.replace(f'source: {SOURCE_A}', 'source: dossier-alpha')
        self.assert_invalid('unknown source')

    def test_claim_anchor_must_match_registered_claim_evidence_source(self):
        self.final = self.final.replace(f'evidence: {EVIDENCE_A}', f'evidence: {EVIDENCE_B}')
        self.assert_invalid('not linked to evidence')

    def test_visible_citation_number_must_match_source_registry(self):
        self.final = self.final.replace('Alpha is supported [1].', 'Alpha is supported [2].')
        self.assert_invalid('visible citation does not match source')

    def test_declared_dossier_claim_must_be_present_in_its_file(self):
        self.alpha = self.alpha.replace(marker(CLAIM_A, EVIDENCE_A, SOURCE_A), '')
        self.assert_invalid('missing claim anchor')

    def test_final_citation_requires_bibliography_entry(self):
        self.final = self.final.replace(
            '[1] [Alpha source](https://example.org/alpha).', '')
        self.assert_invalid('missing bibliography entry: [1]')

    def test_dossier_only_source_requires_its_own_bibliography_entry(self):
        self.beta = self.beta.replace(
            '[2] [Beta source](https://example.org/beta)', '')
        self.assert_invalid('dossier dossier-beta missing bibliography entry: [2]')

    def test_dossier_bibliography_must_match_canonical_source(self):
        self.beta = self.beta.replace('https://example.org/beta',
                                      'https://example.org/fabricated')
        self.assert_invalid('dossier dossier-beta bibliography [2] does not match registered source')

    def test_bibliography_entry_must_match_registered_source(self):
        self.final = self.final.replace('https://example.org/alpha',
                                        'https://example.org/fabricated')
        self.assert_invalid('bibliography [1] does not match registered source')

    def test_bibliography_entry_cannot_swap_source_numbers(self):
        self.final = self.final.replace(
            '[1] [Alpha source](https://example.org/alpha)',
            '[1] [Beta source](https://example.org/beta)')
        self.assert_invalid('bibliography [1] does not match registered source')

    def test_dossier_anchor_claim_must_be_declared(self):
        self.manifest['reporting']['dossiers'][0]['claim_ids'] = []
        self.assert_invalid('anchor claim missing from dossier manifest')

    def test_dossier_anchor_evidence_must_be_declared(self):
        self.manifest['reporting']['dossiers'][0]['evidence_ids'] = []
        self.assert_invalid('anchor evidence missing from dossier manifest')

    def test_dossier_anchor_source_must_be_declared(self):
        self.manifest['reporting']['dossiers'][0]['source_ids'] = []
        self.assert_invalid('anchor source missing from dossier manifest')

    def test_malformed_dossier_path_returns_structured_error(self):
        del self.manifest['reporting']['dossiers'][0]['path']
        self.assert_invalid('relative path')

    def test_malformed_reference_list_returns_structured_error(self):
        self.manifest['reporting']['dossiers'][0]['claim_ids'] = [{'id': CLAIM_A}]
        self.assert_invalid('invalid claim ID')


if __name__ == '__main__':
    unittest.main()
