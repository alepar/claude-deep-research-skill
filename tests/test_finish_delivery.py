"""One read-only delivery command for the session that wrote the report."""

import hashlib
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import finish_delivery, retrieval_health, validate_report_package
from tests import test_layered_package_e2e as e2e


def url_verified(self, entry):
    return {'num': entry['num'], 'status': 'url_verified', 'issues': []}


def snapshot(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(Path(directory).rglob('*')) if p.is_file()}


class FinishDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.package = e2e.LayeredPackageEndToEnd('test_registered_sources_to_two_dossiers_and_final')
        self.package.setUp()
        self.addCleanup(self.package.doCleanups)
        self.path = self.package.path
        support = self.package.run_script('verify_claim_support.py', 'verify',
                                          '--dir', str(self.path), '--strict')
        self.assertEqual(support.returncode, 0, support.stdout + support.stderr)
        self.report = self.path / 'report.md'
        health = retrieval_health.render_markdown(retrieval_health.analyze(str(self.path)))
        text = self.report.read_text()
        self.report.write_text(text.replace('\n## Bibliography',
                                            '\n## Methodology\n\n' + health + '\n## Bibliography'))
        # verify_citations checks each URL over the network; stand in for that.
        patcher = patch.object(finish_delivery.verify_citations.CitationVerifier,
                               'verify_entry', url_verified)
        patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(finish_delivery.verify_citations.time, 'sleep', lambda _: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_complete_package_is_ready_and_nothing_is_written(self):
        before = snapshot(self.path)
        code, summary = finish_delivery.finish(self.path)
        self.assertEqual(code, 0, summary)
        for name in ('coverage', 'package', 'surface', 'citations', 'health'):
            self.assertIn(f'PASS {name}', summary)
        self.assertIn('Retrieval health: ', summary)
        self.assertTrue(summary.rstrip().endswith('Result: READY'), summary)
        self.assertEqual(snapshot(self.path), before)

    def test_unwritten_final_report_fails_before_any_check(self):
        self.report.unlink()
        code, summary = finish_delivery.finish(self.path)
        self.assertEqual(code, 1)
        self.assertIn('not yet written: report.md', summary)
        self.assertIn('no delivery checks ran', summary)
        self.assertNotIn('PASS', summary)

    def test_report_without_current_health_status_fails(self):
        text = self.report.read_text()
        start = text.index('## Methodology')
        self.report.write_text(text[:start] + text[text.index('## Bibliography'):])
        code, summary = finish_delivery.finish(self.path)
        self.assertEqual(code, 1)
        self.assertIn('FAIL health', summary)
        self.assertIn('NOT READY (1 check(s) failed)', summary)

    def test_missing_reporting_path_is_reported(self):
        manifest = self.path / 'run_manifest.json'
        manifest.write_text(manifest.read_text().replace('"final_report_path"', '"other"'))
        code, summary = finish_delivery.finish(self.path)
        self.assertEqual(code, 1)
        self.assertIn('no reporting.final_report_path', summary)

    def test_package_validator_names_unwritten_dossier(self):
        (self.path / 'dossiers' / 'second.md').unlink()
        result = validate_report_package.verify(str(self.path), delivery=True)
        self.assertIn('dossier second not yet written: dossiers/second.md '
                      '(path is recorded but the file is missing)', result['errors'])



def no_network(*_args, **_kwargs):
    raise AssertionError('network lookup attempted')


class BoundedCitationNetworkTests(FinishDeliveryTests):
    """The real entry check, with any DOI/URL lookup treated as a test failure."""

    def setUp(self):
        super().setUp()
        patch.stopall()  # use the real verify_entry from here on
        for name in ('verify_doi', 'verify_url'):
            patcher = patch.object(finish_delivery.verify_citations.CitationVerifier, name, no_network)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_offline_skips_lookups_and_records_it(self):
        code, summary = finish_delivery.finish(self.path, network=False)
        self.assertEqual(code, 0, summary)
        self.assertIn('PASS citations', summary)
        self.assertRegex(summary, r'network checks: 0 run, [1-9]\d* skipped \(offline\)')

    def test_spent_budget_skips_remaining_lookups(self):
        code, summary = finish_delivery.finish(self.path, budget=0)
        self.assertEqual(code, 0, summary)
        self.assertRegex(summary, r'network checks: 0 run, [1-9]\d* skipped \(time budget spent\)')

    def test_strict_verifier_fails_when_offline(self):
        verifier = finish_delivery.verify_citations.CitationVerifier(
            self.report, strict_mode=True, network=False)
        ok, _ = finish_delivery.quiet(verifier.verify_all)
        self.assertFalse(ok)

    # The inherited tests need lookups to succeed; they run in the parent class.
    test_complete_package_is_ready_and_nothing_is_written = None
    test_unwritten_final_report_fails_before_any_check = None
    test_report_without_current_health_status_fails = None
    test_missing_reporting_path_is_reported = None
    test_package_validator_names_unwritten_dossier = None


if __name__ == '__main__':
    unittest.main()
