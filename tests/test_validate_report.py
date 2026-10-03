import tempfile
import unittest
from pathlib import Path

from scripts.validate_report import ReportValidator


class TestReportValidator(unittest.TestCase):
    def validate_text(self, text, files=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / 'report.md'
            report.write_text(text, encoding='utf-8')
            for name in files or []:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('# Dossier\n', encoding='utf-8')
            validator = ReportValidator(report)
            passed = validator.validate()
            return passed, validator.errors, validator.warnings

    def test_compact_final_with_one_source_and_linked_dossier_passes(self):
        report = ('# Answer\n\nThe answer follows from one source [1].\n\n'
                  '[Detailed evidence](dossiers/facet-a.md)\n\n'
                  '## Bibliography\n\n[1] [Source](https://example.org/source)\n')
        passed, errors, warnings = self.validate_text(report, ['dossiers/facet-a.md'])
        self.assertTrue(passed, errors)
        self.assertEqual(warnings, [])

    def test_dossier_without_eight_legacy_sections_passes(self):
        dossier = ('# Facet A\n\n## Answer\n\nThe result is supported [7].\n\n'
                   '## Bibliography\n\n[7] [Source](https://example.org/source)\n')
        passed, errors, _ = self.validate_text(dossier)
        self.assertTrue(passed, errors)

    def test_missing_citation_entry_is_focused_error(self):
        report = ('# Answer\n\nClaim [2].\n\n## Bibliography\n\n'
                  '[1] [Source](https://example.org/source)\n')
        passed, errors, _ = self.validate_text(report)
        self.assertFalse(passed)
        self.assertTrue(any('2' in error and 'bibliography' in error.lower() for error in errors))

    def test_bibliography_only_number_does_not_count_as_body_citation(self):
        report = ('# Answer\n\nAn unsupported factual answer.\n\n'
                  '## Bibliography\n\n[1] [Source](https://example.org/source)\n')
        passed, errors, _ = self.validate_text(report)
        self.assertFalse(passed)
        self.assertTrue(any('body has no source citations' in error for error in errors))

    def test_duplicate_bibliography_number_is_error(self):
        report = ('# Answer\n\nClaim [1].\n\n## Bibliography\n\n'
                  '[1] Source A https://example.org/a\n[1] Source B https://example.org/b\n')
        passed, errors, _ = self.validate_text(report)
        self.assertFalse(passed)
        self.assertTrue(any('duplicate' in error.lower() for error in errors))

    def test_relative_dossier_link_without_dot_prefix_is_checked(self):
        report = ('# Answer\n\nClaim [1]. [Details](dossiers/missing.md)\n\n'
                  '## Bibliography\n\n[1] [Source](https://example.org/source)\n')
        passed, errors, _ = self.validate_text(report)
        self.assertFalse(passed)
        self.assertTrue(any('dossiers/missing.md' in error for error in errors))

    def test_citation_and_placeholder_truncation_still_fail(self):
        report = ('# Answer\n\nClaim [1]. TODO. Content continues.\n\n'
                  '## Bibliography\n\n[1] [Source](https://example.org/source)\n'
                  '[2-8] Additional citations\n')
        passed, errors, _ = self.validate_text(report)
        self.assertFalse(passed)
        self.assertTrue(any('placeholder' in error.lower() for error in errors))
        self.assertTrue(any('truncat' in error.lower() for error in errors))


if __name__ == '__main__':
    unittest.main()
