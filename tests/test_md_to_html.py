"""The HTML bibliography reads escaped and older Markdown entries."""

import html
import re
import unittest

from scripts.md_to_html import convert_markdown_to_html


def bibliography_html(*entries):
    _, bib = convert_markdown_to_html('# R\n\n## Summary\n\nText.\n\n## Bibliography\n\n'
                                      + ''.join(entry + '\n' for entry in entries))
    return bib


def anchors(bib):
    return [(html.unescape(href), html.unescape(text)) for href, text in
            re.findall(r'<a href="([^"]*)" target="_blank">(.*?)</a>', bib, re.S)]


class BibliographyHTMLTests(unittest.TestCase):
    def test_escaped_entries_render_literal_title_and_safe_href(self):
        cases = [
            (r'[Alpha \[draft\] \& co](<https://example.org/a%20b>)',
             'Alpha [draft] & co', 'https://example.org/a%20b'),
            (r'[\<script\>alert(1)\</script\>](<https://example.org/x?a=\<b\>\&c=d>)',
             '<script>alert(1)</script>', 'https://example.org/x?a=<b>&c=d'),
            (r'[The \`grep\` \*manual\* \_x\_ \~y\~ \!z](<https://example.org/topic_(alpha)>)',
             'The `grep` *manual* _x_ ~y~ !z', 'https://example.org/topic_(alpha)'),
            (r'[1\. Line one&#13;&#10;Line two](<https://example.org/back\\slash>)',
             '1. Line one\r\nLine two', 'https://example.org/back\\slash'),
            (r'[\[text\](http://example.com/a\_(b))](<https://example.org/q "x">)',
             '[text](http://example.com/a_(b))', 'https://example.org/q%20"x"'),
        ]
        for entry, title, href in cases:
            with self.subTest(entry=entry):
                bib = bibliography_html('[1] ' + entry)
                self.assertNotIn('<script>', bib)
                self.assertEqual(len(anchors(bib)), 1, bib)
                rendered_href, rendered_title = anchors(bib)[0]
                self.assertEqual(rendered_title, title)
                # The attribute holds the decoded URL, spaces percent-encoded.
                self.assertEqual(rendered_href, href)

    def test_attribute_cannot_be_broken_out_of(self):
        bib = bibliography_html(r'[1] [T](<https://example.org/"onmouseover="x>)')
        self.assertIn('href="https://example.org/&quot;onmouseover=&quot;x"', bib)

    def test_old_forms_still_render(self):
        bib = bibliography_html('[1] [Raw title](https://example.org/raw).',
                                '[2] Author (2024). Legacy Title - https://example.org/legacy',
                                '[3] Tom & Jerry - https://example.org/tj')
        self.assertEqual(anchors(bib), [
            ('https://example.org/raw', 'Raw title'),
            ('https://example.org/legacy', 'Author (2024). Legacy Title'),
            ('https://example.org/tj', 'Tom & Jerry'),
        ])
        self.assertIn('<span class="bib-number">[2]</span>', bib)
        self.assertIn('Tom &amp; Jerry', bib)

    def test_text_around_the_link_is_kept_and_escaped(self):
        bib = bibliography_html(r'[1] Author \& Co (2024). [Title](<https://example.org/t>). J <x>')
        self.assertIn('Author &amp; Co (2024). <a href="https://example.org/t"', bib)
        self.assertIn('</a>. J &lt;x&gt;</div>', bib)

    def test_non_entry_bibliography_lines_are_escaped(self):
        bib = bibliography_html('[3] <img src=x onerror=alert(1)>', 'Note: <b>raw</b> & **bold**')
        self.assertNotIn('<img', bib)
        self.assertNotIn('<b>', bib)
        self.assertIn('[3] &lt;img src=x onerror=alert(1)&gt;', bib)
        self.assertIn('&amp; <strong>bold</strong>', bib)

    def test_non_entry_lines_are_unescaped_once_then_escaped(self):
        bib = bibliography_html(r'Tom &amp; Jerry \*not emphasis\* **bold**')
        self.assertIn('Tom &amp; Jerry *not emphasis* <strong>bold</strong>', bib)
        self.assertNotIn('&amp;amp;', bib)
        self.assertNotIn('\\*', bib)


if __name__ == '__main__':
    unittest.main()
