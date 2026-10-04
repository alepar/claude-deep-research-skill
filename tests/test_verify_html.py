import tempfile
import unittest
from pathlib import Path

from scripts.verify_html import HTMLVerifier


class TestHTMLVerifier(unittest.TestCase):
    def verify_text(self, md, html, files=None, html_name='report.html'):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            md_path = root / 'report.md'
            html_path = root / html_name
            html_path.parent.mkdir(parents=True, exist_ok=True)
            md_path.write_text(md, encoding='utf-8')
            html_path.write_text(html, encoding='utf-8')
            for name in files or []:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('# Dossier\n', encoding='utf-8')
            verifier = HTMLVerifier(html_path, md_path)
            return verifier.verify(), verifier.errors

    def test_compact_custom_rendering_preserves_content_sources_and_dossier_link(self):
        md = ('# Answer\n\nThe evidence supports this answer [1, 2]. '
              '[Detailed evidence](dossiers/facet-a.md)\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n'
              '[2] Source B https://example.org/b\n')
        html = ('<!doctype html><html><head><title>Answer</title></head><body>'
                '<main><h1>Answer</h1><p>The evidence supports this answer '
                '[1, 2]. <a href="dossiers/facet-a.md">Detailed evidence</a></p>'
                '<h2>Bibliography</h2><ol><li>[1] Source A '
                '<a href="https://example.org/a">https://example.org/a</a></li>'
                '<li>[2] Source B <a href="https://example.org/b">'
                'https://example.org/b</a></li></ol></main></body></html>')
        passed, errors = self.verify_text(md, html, ['dossiers/facet-a.md'])
        self.assertTrue(passed, errors)

    def test_rendering_in_subfolder_can_adjust_relative_dossier_link(self):
        md = ('# Answer\n\nEvidence [1]. [Details](dossiers/facet-a.md)\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>Evidence [1]. <a href="../dossiers/facet-a.md">Details</a></p>'
                '<h2>Bibliography</h2><p>[1] Source A https://example.org/a</p>'
                '</body></html>')
        passed, errors = self.verify_text(md, html, ['dossiers/facet-a.md'],
                                          'rendered/report.html')
        self.assertTrue(passed, errors)

    def test_missing_source_and_dossier_are_reported(self):
        md = ('# Answer\n\nEvidence [1]. [Details](dossiers/facet-a.md)\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>Evidence [1].</p><h2>Bibliography</h2></body></html>')
        passed, errors = self.verify_text(md, html, ['dossiers/facet-a.md'])
        self.assertFalse(passed)
        self.assertTrue(any('dossier' in error.lower() for error in errors))
        self.assertTrue(any('bibliography' in error.lower() for error in errors))

    def test_invisible_claim_and_facet_comments_do_not_break_rendering(self):
        md = ('# Answer\n\n<!-- facet: facet-a -->\n\n'
              'A clear factual finding appears here [1]. '
              '<!-- claim: abc; evidence: def; source: ghi -->\n\n'
              '## Bibliography\n\n[1] [Source A](https://example.org/a)\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>A clear factual finding appears here [1].</p>'
                '<h2>Bibliography</h2><p>[1] '
                '<a href="https://example.org/a">Source A</a></p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertTrue(passed, errors)

    def test_swapped_citations_between_claims_fail(self):
        md = ('# Answer\n\nFirst distinct claim cites alpha [1]. '
              'Second distinct claim cites beta [2].\n\n'
              '## Bibliography\n\n[1] Alpha https://example.org/a\n'
              '[2] Beta https://example.org/b\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>First distinct claim cites alpha [2]. '
                'Second distinct claim cites beta [1].</p>'
                '<h2>Bibliography</h2><p>[1] Alpha https://example.org/a</p>'
                '<p>[2] Beta https://example.org/b</p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertFalse(passed)
        self.assertTrue(any('citation' in error.lower() for error in errors), errors)

    def test_missing_url_on_second_bibliography_line_fails(self):
        md = ('# Answer\n\nA clear factual finding appears here [1].\n\n'
              '## Bibliography\n\n[1] Source A\n'
              'https://example.org/second-line\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>A clear factual finding appears here [1].</p>'
                '<h2>Bibliography</h2><p>[1] Source A</p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertFalse(passed)
        self.assertTrue(any('bibliography entry' in error.lower() for error in errors), errors)

    def test_body_link_does_not_replace_missing_bibliography_url(self):
        md = ('# Answer\n\nThe source has a specific finding [1]. '
              '[Read it](https://example.org/source)\n\n'
              '## Bibliography\n\n[1] Source A\n'
              'https://example.org/source\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>The source has a specific finding [1]. '
                '<a href="https://example.org/source">Read it</a></p>'
                '<h2>Bibliography</h2><p>[1] Source A</p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertFalse(passed)
        self.assertTrue(any('bibliography entry' in error.lower() for error in errors), errors)

    def test_swapped_bibliography_links_fail_for_each_entry(self):
        md = ('# Answer\n\nA finding supported by two sources [1, 2].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n'
              '[2] Source B https://example.org/b\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>A finding supported by two sources [1, 2].</p>'
                '<h2>Bibliography</h2><ol>'
                '<li>[1] Source A <a href="https://example.org/b">B link</a></li>'
                '<li>[2] Source B <a href="https://example.org/a">A link</a></li>'
                '</ol></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertFalse(passed)
        self.assertTrue(any('entry [1]' in error for error in errors), errors)
        self.assertTrue(any('entry [2]' in error for error in errors), errors)

    def test_adjacent_rendered_citations_preserve_grouped_attribution(self):
        md = ('# Answer\n\nThe finding has two sources [1, 2].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n'
              '[2] Source B https://example.org/b\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>The finding has two sources [1] [2].</p>'
                '<h2>Bibliography</h2><p>[1] Source A https://example.org/a</p>'
                '<p>[2] Source B https://example.org/b</p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertTrue(passed, errors)

    def test_missing_visible_heading_is_reported(self):
        md = ('# Answer\n\n## Important Finding\n\n'
              'A clear factual finding appears here [1].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        html = ('<html><head><title>Answer</title></head><body><h1>Answer</h1>'
                '<p>Important Finding</p>'
                '<p>A clear factual finding appears here [1].</p>'
                '<h2>Bibliography</h2><p>[1] Source A https://example.org/a</p>'
                '</body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertFalse(passed)
        self.assertTrue(any('Missing heading' in error for error in errors), errors)

    def test_script_or_style_cannot_supply_only_body_finding_and_citation(self):
        md = ('# Answer\n\nA clear factual finding appears here [1].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        for tag in ('script', 'style'):
            with self.subTest(tag=tag):
                html = ('<html><head><title>Answer</title></head><body>'
                        '<h1>Answer</h1>'
                        f'<{tag}>A clear factual finding appears here [1].</{tag}>'
                        '<h2>Bibliography</h2><p>[1] Source A '
                        'https://example.org/a</p></body></html>')
                passed, errors = self.verify_text(md, html)
                self.assertFalse(passed)
                self.assertTrue(any('Missing Markdown passage' in error for error in errors), errors)
                self.assertTrue(any('citation' in error.lower() for error in errors), errors)

    def test_template_cannot_supply_visible_heading_or_local_link(self):
        md = ('# Answer\n\n## Important Finding\n\n'
              'A clear factual finding appears here [1]. '
              '[Details](dossiers/facet-a.md)\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        html = ('<html><head><title>Answer</title></head><body>'
                '<h1>Answer</h1><template><h2>Important Finding</h2>'
                '<p>A clear factual finding appears here [1]. '
                '<a href="dossiers/facet-a.md">Details</a></p></template>'
                '<h2>Bibliography</h2><p>[1] Source A '
                'https://example.org/a</p></body></html>')
        passed, errors = self.verify_text(md, html, ['dossiers/facet-a.md'])
        self.assertFalse(passed)
        self.assertTrue(any('Missing heading' in error for error in errors), errors)
        self.assertTrue(any('Missing Markdown passage' in error for error in errors), errors)
        self.assertTrue(any('citation' in error.lower() for error in errors), errors)
        self.assertTrue(any('Missing dossier/local link' in error for error in errors), errors)

    def test_script_or_style_cannot_supply_bibliography_entry(self):
        md = ('# Answer\n\nA clear factual finding appears here [1].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        for tag in ('script', 'style'):
            with self.subTest(tag=tag):
                html = ('<html><head><title>Answer</title></head><body>'
                        '<h1>Answer</h1><p>A clear factual finding appears here [1].</p>'
                        '<h2>Bibliography</h2>'
                        f'<{tag}>[1] Source A https://example.org/a</{tag}>'
                        '</body></html>')
                passed, errors = self.verify_text(md, html)
                self.assertFalse(passed)
                self.assertTrue(any('bibliography' in error.lower() for error in errors), errors)

    def test_visible_report_can_include_nonrendered_metadata(self):
        md = ('# Answer\n\nA clear factual finding appears here [1].\n\n'
              '## Bibliography\n\n[1] Source A https://example.org/a\n')
        html = ('<html><head><title>Answer</title><style>.x { color: red }</style>'
                '</head><body><script>const metadata = "hidden";</script>'
                '<h1>Answer</h1><p>A clear factual finding appears here [1].</p>'
                '<template><p>Unused draft text</p></template>'
                '<h2>Bibliography</h2><p>[1] Source A '
                'https://example.org/a</p></body></html>')
        passed, errors = self.verify_text(md, html)
        self.assertTrue(passed, errors)


if __name__ == '__main__':
    unittest.main()
