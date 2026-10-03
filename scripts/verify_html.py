#!/usr/bin/env python3
"""Check that an optional HTML rendering preserves its Markdown report."""

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

if __package__:
    from .validate_report import MARKDOWN_LINK, citation_numbers
else:
    from validate_report import MARKDOWN_LINK, citation_numbers


def words(value: str) -> str:
    """Normalize visible text for comparison across Markdown and HTML markup."""
    return ' '.join(re.findall(r'\w+', value.casefold(), re.UNICODE))


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = set()
        self.body_depth = 0
        self.body_parts = []
        self.headings = []
        self.heading = None
        self.links = []
        self.current_href = None
        self.link_text = []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        if tag == 'body':
            self.body_depth += 1
        if re.fullmatch(r'h[1-6]', tag):
            self.heading = []
        if tag == 'a':
            self.current_href = dict(attrs).get('href')
            self.link_text = []

    def handle_endtag(self, tag):
        if re.fullmatch(r'h[1-6]', tag) and self.heading is not None:
            self.headings.append((''.join(self.heading).strip(), len(self.body_parts)))
            self.heading = None
        if tag == 'a' and self.current_href is not None:
            self.links.append((self.current_href, ''.join(self.link_text).strip()))
            self.current_href = None
        if tag == 'body':
            self.body_depth = max(0, self.body_depth - 1)

    def handle_data(self, data):
        if self.body_depth:
            self.body_parts.append(data)
        if self.heading is not None:
            self.heading.append(data)
        if self.current_href is not None:
            self.link_text.append(data)


class HTMLVerifier:
    """Verify content and links without requiring a particular HTML template."""

    def __init__(self, html_path: Path, md_path: Path):
        self.html_path = Path(html_path)
        self.md_path = Path(md_path)
        self.errors = []

    def verify(self) -> bool:
        self.errors.clear()
        try:
            html = self.html_path.read_text(encoding='utf-8')
            md = self.md_path.read_text(encoding='utf-8')
        except OSError as exc:
            self.errors.append(f'Failed to read files: {exc}')
            self._print_results()
            return False

        doc = Document()
        doc.feed(html)
        for tag in ('html', 'head', 'body', 'title'):
            if tag not in doc.tags:
                self.errors.append(f'Missing <{tag}> element')
        if re.search(r'\{\{[A-Z_]+\}\}|\b(?:TODO|TBD|FIXME)\b', html, re.I):
            self.errors.append('Unreplaced placeholder in HTML')

        md_body, bibliography = self._markdown_sections(md)
        bib_heading = next((offset for heading, offset in doc.headings
                            if words(heading) == 'bibliography'), None)
        body_parts = doc.body_parts[:bib_heading] if bib_heading is not None else doc.body_parts
        html_body = ' '.join(body_parts)
        html_bib = ' '.join(doc.body_parts[bib_heading:]) if bib_heading is not None else ''

        self._check_content(md_body, html_body, doc)
        self._check_citations(md_body, html_body)
        self._check_bibliography(bibliography, html_bib, doc)
        self._check_local_links(md, doc)
        self._print_results()
        return not self.errors

    @staticmethod
    def _markdown_sections(md):
        match = re.search(r'^## Bibliography\s*$', md, re.M | re.I)
        if not match:
            return md, None
        next_heading = re.search(r'^## ', md[match.end():], re.M)
        end = match.end() + next_heading.start() if next_heading else len(md)
        return md[:match.start()] + md[end:], md[match.end():end]

    def _check_content(self, md_body, html_body, doc):
        html_words = words(re.sub(r'\[\d+(?:,\s*\d+)*\]', '', html_body))
        html_headings = {words(heading) for heading, _ in doc.headings}
        for heading in re.findall(r'^#{1,6}\s+(.+)$', md_body, re.M):
            if words(heading) not in html_headings:
                self.errors.append(f'Missing heading in HTML: {heading}')
        for paragraph in re.split(r'\n\s*\n', md_body):
            if re.match(r'^#{1,6}\s+', paragraph):
                paragraph = re.sub(r'^#{1,6}\s+.*$', '', paragraph, flags=re.M)
            paragraph = re.sub(MARKDOWN_LINK, lambda match: match.group(0).split('](')[0][1:], paragraph)
            paragraph = re.sub(r'\[\d+(?:,\s*\d+)*\]', '', paragraph)
            expected = words(paragraph)
            if len(expected.split()) >= 4 and expected not in html_words:
                self.errors.append(f'Missing Markdown passage in HTML: {expected[:70]}')

    def _check_citations(self, md_body, html_body):
        missing = citation_numbers(md_body) - citation_numbers(html_body)
        if missing:
            self.errors.append('Missing source citations in HTML body: ' +
                               ', '.join(sorted(missing, key=int)))

    def _check_bibliography(self, bibliography, html_bib, doc):
        if bibliography is None:
            return
        if not html_bib:
            self.errors.append('Bibliography section missing from HTML')
            return
        for number, entry in re.findall(r'^\[(\d+)\]\s+(.+)$', bibliography, re.M):
            entry_title = re.sub(r'https?://\S+', '', entry)
            entry_title = re.sub(MARKDOWN_LINK,
                                 lambda match: match.group(0).split('](')[0][1:], entry_title)
            entry_title = words(entry_title)
            urls = re.findall(r'https?://[^\s)]+', entry)
            if (not re.search(rf'\[{re.escape(number)}\]|(?<!\d){re.escape(number)}\.', html_bib)
                    or (entry_title and entry_title not in words(html_bib))
                    or any(url not in html_bib and url not in [href for href, _ in doc.links]
                           for url in urls)):
                self.errors.append(f'Missing or changed bibliography entry [{number}] in HTML')

    def _check_local_links(self, md, doc):
        local_hrefs = set()
        for href, _ in doc.links:
            parsed_href = urlsplit(href)
            if not parsed_href.scheme and not parsed_href.netloc and parsed_href.path:
                path = Path(unquote(parsed_href.path))
                if not path.is_absolute():
                    local_hrefs.add((self.html_path.parent / path).resolve())
        for match in MARKDOWN_LINK.finditer(md):
            target = match.group(1) or match.group(2)
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = Path(unquote(parsed.path))
            expected = (self.md_path.parent / path).resolve()
            if path.is_absolute() or expected not in local_hrefs:
                self.errors.append(f'Missing dossier/local link in HTML: {target}')
            elif not expected.exists():
                self.errors.append(f'Broken dossier/local link from HTML: {target}')

    def _print_results(self):
        if self.errors:
            for error in self.errors:
                print(f'ERROR: {error}')
        else:
            print(f'PASS: {self.html_path} preserves Markdown content and links')


def main():
    parser = argparse.ArgumentParser(description='Verify an optional HTML report')
    parser.add_argument('--html', type=Path, required=True)
    parser.add_argument('--md', type=Path, required=True)
    args = parser.parse_args()
    if not args.html.is_file() or not args.md.is_file():
        parser.error('Both --html and --md must be existing files')
    return 0 if HTMLVerifier(args.html, args.md).verify() else 1


if __name__ == '__main__':
    raise SystemExit(main())
