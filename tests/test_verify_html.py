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


if __name__ == '__main__':
    unittest.main()
