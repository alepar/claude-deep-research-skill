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
    def extract(self, bibliography):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n\n## Bibliography\n\n' + bibliography,
                              encoding='utf-8')
            return CitationVerifier(report).extract_bibliography()

    def test_escaped_link_title_and_angle_destination_are_decoded(self):
        cases = [
            (r'[Alpha \[draft\] \& \`co\`](<https://example.org/a%20b\&c=\<d\>>).',
             'Alpha [draft] & `co`', 'https://example.org/a b&c=<d>'),
            (r'[1\. \*Bold\* \_x\_ \~y\~ \!z](<https://example.org/topic_(alpha)>)',
             '1. *Bold* _x_ ~y~ !z', 'https://example.org/topic_(alpha)'),
            (r'[&#32;Edge&#32;](<https://example.org/back\\slash%09tab>)',
             ' Edge ', 'https://example.org/back\\slash\ttab'),
            (r'[Line one&#13;&#10;Line two](<https://doi.org/10.1234/alpha>)',
             'Line one\r\nLine two', 'https://doi.org/10.1234/alpha'),
            (r'[\[text\](http://example.com/a\_(b))](<https://example.org/a_(b)>)',
             '[text](http://example.com/a_(b))', 'https://example.org/a_(b)'),
        ]
        for line, title, url in cases:
            with self.subTest(line=line):
                entry = self.extract('[1] ' + line + '\n')[0]
                self.assertEqual(entry['title'], title)
                self.assertEqual(entry['url'], url)

    def test_angle_destination_yields_doi(self):
        entry = self.extract('[1] [Title](<https://doi.org/10.1234/alpha>)\n')[0]
        self.assertEqual(entry['doi'], '10.1234/alpha')

    def test_heading_marks_inside_title_do_not_end_bibliography(self):
        entries = self.extract('[1] [C## in practice](<https://example.org/c>)\n'
                               '[2] [Second](<https://example.org/second>)\n')
        self.assertEqual([entry['url'] for entry in entries],
                         ['https://example.org/c', 'https://example.org/second'])

    def test_url_check_sends_spaces_percent_encoded(self):
        with tempfile.TemporaryDirectory() as temporary:
            report = Path(temporary) / 'report.md'
            report.write_text('# Report\n', encoding='utf-8')
            verifier = CitationVerifier(report)
            with patch('verify_citations.request.urlopen',
                       side_effect=OSError('stop')) as urlopen:
                verifier.verify_url('https://example.org/a b\tc')
        self.assertEqual(urlopen.call_args[0][0].full_url, 'https://example.org/a%20b%09c')

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
