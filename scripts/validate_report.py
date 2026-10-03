#!/usr/bin/env python3
"""Check the Markdown surface of a final report or facet dossier.

Canonical evidence, source identity, facet coverage, and claim support are
checked by the package, coverage, citation, and claim-support validators.
"""

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit


BIBLIOGRAPHY_HEADING = re.compile(r'^## Bibliography\s*$', re.I | re.M)
SECTION_HEADING = re.compile(r'^## ', re.M)
BIB_ENTRY = re.compile(r'^\[(\d+)\]\s+\S', re.M)
CITATION = re.compile(r'\[(\d+(?:,\s*\d+)*)\](?!\()')
MARKDOWN_LINK = re.compile(r'(?<!!)\[[^\]]+\]\((?:<([^>]+)>|([^\s)]+))(?:\s+"[^"]*")?\)')


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
            target = match.group(1) or match.group(2)
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
