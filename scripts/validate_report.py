#!/usr/bin/env python3
"""Check the Markdown surface of a final report or facet dossier.

Canonical evidence, source identity, facet coverage, and claim support are
checked by the package, coverage, citation, and claim-support validators.
"""

import argparse
import html
import html.entities
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


BIBLIOGRAPHY_HEADING = re.compile(r'^## Bibliography\s*$', re.I | re.M)
SECTION_HEADING = re.compile(r'^## ', re.M)
BIB_ENTRY = re.compile(r'^\[(\d+)\]\s+\S', re.M)
CITATION = re.compile(r'\[(\d+(?:,\s*\d+)*)\](?!\()')
# A Markdown link. The text skips backslash pairs, so an escaped bracket does
# not end it, and the opening bracket follows an even run of backslashes (up
# to six), so it is not itself escaped. Group 1 is an angle-bracket
# destination as written (backslash escapes and percent-encoded spaces
# intact); group 2 is a bare destination as written, which may hold one level
# of balanced parentheses.
_TEXT = r'(?:\\[\s\S]|[^\\\]])+'
_UNESCAPED = (r'(?:(?<!\\)|(?<=(?<!\\)\\\\)|(?<=(?<!\\)\\\\\\\\)'
              r'|(?<=(?<!\\)\\\\\\\\\\\\))')
_BARE = r'(?:\\\S|[^\s()\\])'
LINK_TEXT = re.compile(r'\[(' + _TEXT + r')\]')
# An image starts with an unescaped '!'; an escaped one is text before a link.
MARKDOWN_LINK = re.compile(r'(?:(?<!!)|(?<=(?<!\\)\\!))' + _UNESCAPED + r'\[' + _TEXT + r'\]'
                           r'\(\s*(?:<((?:\\.|[^\\<>\n])+)>|'
                           r'((?:' + _BARE + r'|\(' + _BARE + r'*\))+))'
                           r'(?:\s+"[^"]*")?\s*\)')
# A backslash before ASCII punctuation, a code span (left as written), or a
# character reference.
_ESCAPE = r'\\([!-/:-@\[-`{-~])'
_CODE_SPAN = r'(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\2(?!`)'
_REFERENCE = r'&(#[0-9]{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});'
TEXT_ESCAPE = re.compile('|'.join((_ESCAPE, _CODE_SPAN, _REFERENCE)))
# The never-matching group keeps the reference in group 3, as in TEXT_ESCAPE.
DESTINATION_ESCAPE = re.compile(_ESCAPE + '|(?!)()|' + _REFERENCE)
# A percent-encoded space or control byte: the bytes a writer encodes in a
# destination because a destination cannot hold them.
ENCODED_BYTE = re.compile(r'%(?:[01][0-9A-Fa-f]|20|7[Ff])')


def _unescape(match):
    if match.group(1) is not None:
        return match.group(1)
    reference = match.group(3)
    if reference is None:
        return match.group(0)  # a code span
    if reference.startswith('#'):
        # A code point, as CommonMark reads it: NUL, surrogates and values
        # past U+10FFFF become U+FFFD.
        number = int(reference[2:], 16) if reference[1] in 'xX' else int(reference[1:])
        valid = 0 < number <= 0x10FFFF and not 0xD800 <= number <= 0xDFFF
        return chr(number) if valid else '\ufffd'
    return html.entities.html5.get(reference + ';', match.group(0))


def unescape_inline(text: str, code_spans: bool = True) -> str:
    """Read escaped Markdown text back as the literal text it was written from.

    Code spans are left as written; a link destination has none, so its
    backticks are ordinary characters (code_spans=False).
    """
    return (TEXT_ESCAPE if code_spans else DESTINATION_ESCAPE).sub(_unescape, text)


def decode_encoded_bytes(url: str) -> str:
    """Decode only the percent-encoded spaces and control bytes."""
    return ENCODED_BYTE.sub(lambda match: chr(int(match.group(0)[1:], 16)), url)


def link_text(match) -> str:
    """The literal text of a MARKDOWN_LINK match."""
    return unescape_inline(LINK_TEXT.match(match.string, match.start()).group(1))


def link_target(match) -> str:
    """The destination of a MARKDOWN_LINK match as the URL it was written from.

    Backslash escapes and character references are read in both forms; an
    angle-bracket destination also has its encoded spaces and control bytes
    decoded.
    """
    if match.group(1) is None:
        return unescape_inline(match.group(2), code_spans=False)
    return decode_encoded_bytes(unescape_inline(match.group(1), code_spans=False))


def same_url(target: str, url: str) -> bool:
    """Whether a link target names url, reading %20 and a space as one.

    A registered URL scraped from HTML may still hold character references
    (&amp;); it also matches once they are read.
    """
    target = decode_encoded_bytes(target)
    return target in (decode_encoded_bytes(url),
                      decode_encoded_bytes(unescape_inline(url, code_spans=False)))


def citation_numbers(text: str) -> set[str]:
    """Read every number in a visible citation group, as package checks do."""
    return {number.strip() for group in CITATION.findall(text)
            for number in group.split(',')}


class ReportValidator:
    """Validate concrete Markdown defects without imposing a report outline."""

    def __init__(self, report_path: Path):
        self.report_path = Path(report_path)
        self.content = self.report_path.read_text(encoding='utf-8')
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def _sections(self):
        match = BIBLIOGRAPHY_HEADING.search(self.content)
        if not match:
            return self.content, None
        next_heading = SECTION_HEADING.search(self.content, match.end())
        end = next_heading.start() if next_heading else len(self.content)
        return self.content[:match.start()] + self.content[end:], self.content[match.end():end]

    def validate(self) -> bool:
        """Run six surface checks; each failure identifies its local repair."""
        self.errors.clear()
        self.warnings.clear()
        checks = [
            self._check_content,
            self._check_citations,
            self._check_bibliography,
            self._check_placeholders,
            self._check_truncation,
            self._check_local_links,
        ]
        for check in checks:
            check()
        if self.errors:
            for error in self.errors:
                print(f'ERROR: {error}')
        else:
            print(f'PASS: {self.report_path} ({len(checks)} Markdown checks)')
        return not self.errors

    def _check_content(self):
        body, _ = self._sections()
        if not re.search(r'^#{1,2}\s+\S', body, re.M):
            self.errors.append('Report needs a Markdown title or heading')
        prose = re.sub(MARKDOWN_LINK, '', body)
        prose = re.sub(r'^#.*$', '', prose, flags=re.M).strip()
        if not prose:
            self.errors.append('Report body is empty')

    def _check_citations(self):
        body, _ = self._sections()
        if not CITATION.search(body):
            self.errors.append('Report body has no source citations [N]')

    def _check_bibliography(self):
        body, bibliography = self._sections()
        if bibliography is None:
            self.errors.append('Missing ## Bibliography section')
            return
        if re.search(r'\[\d+\s*[-–]\s*\d+\]|additional\s+citations|would be included|\[\.\.\.\s*continue|\[continue with', bibliography, re.I):
            self.errors.append('Bibliography contains a citation range or truncation placeholder')
        entries = BIB_ENTRY.findall(bibliography)
        if not entries:
            self.errors.append('Bibliography has no numbered source entries')
            return
        duplicates = sorted({number for number in entries if entries.count(number) > 1}, key=int)
        if duplicates:
            self.errors.append(f'Duplicate bibliography numbers: {", ".join(duplicates)}')
        cited = citation_numbers(body)
        listed = set(entries)
        missing = sorted(cited - listed, key=int)
        if missing:
            self.errors.append(f'Citations missing from bibliography: {", ".join(missing)}')
        unused = sorted(listed - cited, key=int)
        if unused:
            self.warnings.append(f'Unused bibliography entries: {", ".join(unused)}')

    def _check_placeholders(self):
        matches = re.findall(r'\b(?:TBD|TODO|FIXME|XXX)\b|\[(?:citation needed|needs citation|placeholder)\]', self.content, re.I)
        if matches:
            self.errors.append(f'Placeholder text: {", ".join(sorted(set(matches)))}')

    def _check_truncation(self):
        if re.search(r'content continues|due to length|would continue|\[sections\s+\d+\s*[-–]\s*\d+|additional sections', self.content, re.I):
            self.errors.append('Content truncation marker found; complete the affected passage')

    def _check_local_links(self):
        broken = []
        for match in MARKDOWN_LINK.finditer(self.content):
            target = link_target(match)
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            path = Path(unquote(parsed.path))
            if path.is_absolute() or not (self.report_path.parent / path).exists():
                broken.append(target)
        if broken:
            self.errors.append(f'Broken or nonrelative local links: {", ".join(broken)}')


def main():
    parser = argparse.ArgumentParser(description='Validate Markdown report or dossier surface')
    parser.add_argument('--report', '-r', type=Path, required=True)
    args = parser.parse_args()
    if not args.report.is_file():
        parser.error(f'Report file not found: {args.report}')
    return 0 if ReportValidator(args.report).validate() else 1


if __name__ == '__main__':
    sys.exit(main())
