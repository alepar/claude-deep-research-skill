"""The documented Markdown bibliography form must yield the exact source URL."""

import sys
import tempfile
import unittest
from pathlib import Path


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


if __name__ == '__main__':
    unittest.main()
