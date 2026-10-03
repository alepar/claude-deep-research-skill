"""The documented Markdown bibliography form must yield the exact source URL."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from verify_citations import CitationVerifier  # noqa: E402


class CitationTemplateTests(unittest.TestCase):
    def test_markdown_link_keeps_trailing_punctuation_out_of_url(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n'
                              '[1] [Alpha source](https://example.org/alpha).\n',
                              encoding='utf-8')
            entry = CitationVerifier(report).extract_bibliography()[0]
        self.assertEqual(entry['url'], 'https://example.org/alpha')

    def test_markdown_link_title_and_url_are_extracted(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n'
                              '[1] [Real Research Title](https://example.org/alpha)\n',
                              encoding='utf-8')
            entry = CitationVerifier(report).extract_bibliography()[0]
        self.assertEqual(entry['title'], 'Real Research Title')
        self.assertEqual(entry['url'], 'https://example.org/alpha')

    def test_multiline_markdown_link_url_and_doi_are_extracted(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n'
                              '[1] [Real Research Title](\n'
                              'https://doi.org/10.1234/alpha)\n', encoding='utf-8')
            entry = CitationVerifier(report).extract_bibliography()[0]
        self.assertEqual(entry['title'], 'Real Research Title')
        self.assertEqual(entry['url'], 'https://doi.org/10.1234/alpha')
        self.assertEqual(entry['doi'], '10.1234/alpha')

    def test_legacy_quoted_title_and_second_line_url_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n'
                              '[1] Author (2024). "Legacy Title". Journal.\n'
                              'https://example.org/legacy\n', encoding='utf-8')
            entry = CitationVerifier(report).extract_bibliography()[0]
        self.assertEqual(entry['title'], 'Legacy Title')
        self.assertEqual(entry['year'], '2024')
        self.assertEqual(entry['url'], 'https://example.org/legacy')

    def test_markdown_link_title_is_compared_with_doi_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n'
                              '[1] [Unrelated Fabricated Title]'
                              '(https://doi.org/10.1234/alpha)\n', encoding='utf-8')
            verifier = CitationVerifier(report)
            entry = verifier.extract_bibliography()[0]
            with patch.object(verifier, 'verify_doi', return_value=(True, {
                    'title': 'Actual Research Title', 'year': None})):
                with patch.object(verifier, 'verify_url', return_value=(True, 'OK')):
                    result = verifier.verify_entry(entry)
        self.assertEqual(result['status'], 'suspicious')
        self.assertTrue(any('Title mismatch' in issue for issue in result['issues']))


if __name__ == '__main__':
    unittest.main()
