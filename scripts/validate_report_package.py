#!/usr/bin/env python3
"""Validate links and canonical references in a layered research package.

This is a structural check. A human must judge whether prose follows from evidence.
"""

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


ANCHOR = re.compile(r'<!--\s*claim:\s*([^;\s]+);\s*evidence:\s*([^;\s]+);\s*source:\s*([^\s]+)\s*-->')
FACET = re.compile(r'<!--\s*facet:\s*(.*?)\s*-->')
LINK = re.compile(r'(?<!!)\[[^\]]+\]\(([^)]+)\)')
ID = re.compile(r'^[0-9a-f]{16}$')


def load_json(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


def load_jsonl(path):
    with path.open(encoding='utf-8') as handle:
        return [json.loads(line) for line in handle if line.strip()]


def resolved_path(directory, raw, label, errors, package_root=None):
    """Return a package-local Markdown path, rejecting traversal and symlinks out."""
    root = Path(package_root or directory).resolve()
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or \
            Path(raw).suffix.lower() != '.md':
        errors.append(f'{label} must be a relative path to a Markdown file')
        return None
    path = (directory / raw).resolve()
    if not path.is_relative_to(root):
        errors.append(f'{label} must be a relative path inside the package')
        return None
    if not path.is_file():
        errors.append(f'{label} missing file: {raw}')
        return None
    return path


def unique_index(rows, key, label, errors):
    result = {}
    if not isinstance(rows, list):
        errors.append(f'{label} rows must be an array')
        return result
    for row in rows:
        if not isinstance(row, dict):
            errors.append(f'{label} row must be an object')
            continue
        value = row.get(key)
        if not isinstance(value, str) or not value:
            errors.append(f'{label} missing {key}')
        elif value in result:
            errors.append(f'duplicate {label} ID: {value}')
        else:
            result[value] = row
    return result


def check_ids(values, index, label, kind, errors):
    if not isinstance(values, list):
        errors.append(f'{label} must be an array')
        return []
    valid = []
    for value in values:
        if not isinstance(value, str):
            errors.append(f'{label} has invalid {kind} ID: {value!r}')
        else:
            valid.append(value)
    if len(valid) != len(set(valid)):
        errors.append(f'{label} has duplicate IDs')
    for value in valid:
        if value not in index:
            errors.append(f'{label} references unknown {kind}: {value}')
    return valid


def check_anchors(markdown, label, expected_claim_ids, claims, evidence, sources,
                  display_numbers, errors, declared=None):
    found = set()
    for match in ANCHOR.finditer(markdown):
        claim_id, evidence_id, source_id = match.groups()
        found.add(claim_id)
        if declared is not None:
            for kind, value in [('claim', claim_id), ('evidence', evidence_id),
                                ('source', source_id)]:
                if value not in declared[kind]:
                    errors.append(f'{label} anchor {kind} missing from dossier manifest: {value}')
        if not ID.fullmatch(claim_id) or claim_id not in claims:
            errors.append(f'{label} references unknown claim: {claim_id}')
            continue
        claim = claims[claim_id]
        if claim.get('support_status') != 'supported':
            errors.append(f'{label} claim {claim_id} is not supported')
        if evidence_id not in evidence:
            errors.append(f'{label} references unknown evidence: {evidence_id}')
        if source_id not in sources:
            errors.append(f'{label} references unknown source: {source_id}')
        if evidence_id not in claim.get('evidence_ids', []):
            errors.append(f'{label} claim {claim_id} not linked to evidence {evidence_id}')
        if source_id not in claim.get('cited_source_ids', []):
            errors.append(f'{label} claim {claim_id} not linked to source {source_id}')
        if evidence_id in evidence and evidence[evidence_id].get('source_id') != source_id:
            errors.append(f'{label} evidence {evidence_id} does not belong to source {source_id}')
        citation = re.search(r'\[(\d+(?:,\s*\d+)*)\]\s*[.?!]?\s*$',
                             markdown[max(0, match.start()-160):match.start()])
        if not citation:
            errors.append(f'{label} claim {claim_id} lacks a visible numeric citation before anchor')
        elif source_id in display_numbers and str(display_numbers[source_id]) not in \
                [number.strip() for number in citation.group(1).split(',')]:
            errors.append(f'{label} claim {claim_id} visible citation does not match source {source_id}')
    for claim_id in expected_claim_ids - found:
        errors.append(f'{label} missing claim anchor: {claim_id}')
    return found


def check_bibliography(markdown, sources, errors, label='final report'):
    """Match visible numbers and identifying fields to canonical sources."""
    heading = re.search(r'^## Bibliography\s*$', markdown, re.MULTILINE | re.IGNORECASE)
    if not heading:
        errors.append(f'{label} missing Bibliography section')
        return
    body = markdown[:heading.start()]
    section = markdown[heading.end():]
    next_heading = re.search(r'^##\s+', section, re.MULTILINE)
    if next_heading:
        section = section[:next_heading.start()]
    entries = {}
    entry_matches = list(re.finditer(r'^\[(\d+)\]\s+(.+)$', section, re.MULTILINE))
    for i, match in enumerate(entry_matches):
        number = int(match.group(1))
        end = entry_matches[i + 1].start() if i + 1 < len(entry_matches) else len(section)
        entry = section[match.start(2):end].strip()
        if number in entries:
            errors.append(f'{label} duplicate bibliography entry: [{number}]')
        entries[number] = entry
    source_order = list(sources.values())
    for number, entry in entries.items():
        if number < 1 or number > len(source_order):
            errors.append(f'{label} bibliography [{number}] has no registered source')
            continue
        source = source_order[number - 1]
        title = source.get('title')
        locator = source.get('raw_url')
        if not title or not locator or title.casefold() not in entry.casefold() or locator not in entry:
            errors.append(f'{label} bibliography [{number}] does not match registered source')
    for group in re.findall(r'\[(\d+(?:,\s*\d+)*)\]', body):
        for raw_number in group.split(','):
            number = int(raw_number.strip())
            if number not in entries:
                errors.append(f'{label} missing bibliography entry: [{number}]')


def verify(directory, delivery=False):
    directory = Path(directory)
    errors = []
    try:
        manifest = load_json(directory / 'run_manifest.json')
    except (OSError, ValueError) as exc:
        return {'status': 'invalid', 'errors': [f'run_manifest.json: {exc}']}
    reporting = manifest.get('reporting')
    if reporting is None and 'reporting' not in manifest:
        if delivery:
            return {'status': 'invalid', 'errors': ['delivery requires reporting package']}
        return {'status': 'ok', 'errors': []}
    if not isinstance(reporting, dict):
        return {'status': 'invalid', 'errors': ['reporting must be an object']}
    if reporting.get('output_mode') not in {'markdown', 'html', 'pdf'}:
        errors.append('reporting output_mode must be markdown, html, or pdf')
    requested_formats = reporting.get('requested_formats', [])
    if (not isinstance(requested_formats, list) or
            any(not isinstance(value, str) or value not in {'html', 'pdf'}
                for value in requested_formats) or
            len(requested_formats) != len(set(requested_formats))):
        errors.append('reporting requested_formats must be a unique array of html/pdf')
    for field in ('final_report_path', 'dossiers'):
        if field not in reporting:
            errors.append(f'reporting missing {field}')
    paths = manifest.get('artifact_paths', {})
    try:
        coverage = load_json(directory / paths.get('coverage', 'coverage.json'))
        sources = unique_index(load_jsonl(directory / paths.get('sources', 'sources.jsonl')),
                               'source_id', 'source', errors)
        display_numbers = {sid: number for number, sid in enumerate(sources, 1)}
        evidence = unique_index(load_jsonl(directory / paths.get('evidence', 'evidence.jsonl')),
                                'evidence_id', 'evidence', errors)
        claims = unique_index(load_jsonl(directory / paths.get('claims', 'claims.jsonl')),
                              'claim_id', 'claim', errors)
    except (OSError, ValueError) as exc:
        return {'status': 'invalid', 'errors': [f'canonical artifact read: {exc}']}
    facets = unique_index(coverage.get('facets', []), 'id', 'facet', errors)
    if delivery:
        stop = manifest.get('retrieval_stop')
        if not isinstance(stop, dict) or not stop.get('reason') or stop != coverage.get('stop'):
            errors.append('delivery requires matching persisted retrieval_stop in manifest and coverage')
    active_high = {fid for fid, facet in facets.items()
                   if facet.get('active') and facet.get('priority') == 'high'}
    final_path = resolved_path(directory, reporting.get('final_report_path'),
                               'final report', errors)
    dossier_rows = reporting.get('dossiers', [])
    dossiers = unique_index(dossier_rows, 'id', 'dossier', errors)
    dossier_paths = set()
    covered = set()
    for did, dossier in dossiers.items():
        label = f'dossier {did}'
        path = resolved_path(directory, dossier.get('path'), label, errors)
        if path in dossier_paths:
            errors.append(f'duplicate dossier path: {dossier.get("path")}')
        dossier_paths.add(path)
        facet_ids = check_ids(dossier.get('facet_ids'), facets, label, 'facet', errors)
        covered.update(facet_ids)
        source_ids = check_ids(dossier.get('source_ids'), sources, label, 'source', errors)
        evidence_ids = check_ids(dossier.get('evidence_ids'), evidence, label, 'evidence', errors)
        claim_ids = check_ids(dossier.get('claim_ids'), claims, label, 'claim', errors)
        if dossier.get('status') not in {'draft', 'complete', 'partial'}:
            errors.append(f'{label} has invalid status')
        elif delivery and dossier.get('status') == 'draft':
            errors.append(f'{label} is draft and cannot be delivered')
        for eid in evidence_ids:
            if eid in evidence and evidence[eid].get('source_id') not in source_ids:
                errors.append(f'{label} evidence {eid} source missing from dossier')
        for cid in claim_ids:
            claim = claims.get(cid)
            if claim and not str(claim.get('section_id', '')).startswith(did + ':'):
                errors.append(f'{label} claim {cid} has wrong section ID')
            if claim and claim.get('claim_type') == 'factual' and claim.get('support_status') != 'supported':
                errors.append(f'{label} claim {cid} is not supported')
        if path:
            dossier_text = path.read_text(encoding='utf-8')
            check_anchors(dossier_text, label,
                          set(claim_ids), claims, evidence, sources, display_numbers, errors,
                          declared={'claim': set(claim_ids), 'evidence': set(evidence_ids),
                                    'source': set(source_ids)})
            check_bibliography(dossier_text, sources, errors, label)
    if dossiers or manifest.get('mode') not in {'quick', 'standard'}:
        for fid in active_high - covered:
            errors.append(f'active high-priority facet {fid} has no dossier')
    if final_path:
        final = final_path.read_text(encoding='utf-8')
        check_bibliography(final, sources, errors)
        found_facets = set(FACET.findall(final))
        for fid in active_high - found_facets:
            errors.append(f'final report omits active high-priority facet: {fid}')
        linked = set()
        for raw in LINK.findall(final):
            raw = raw.strip()
            if raw.startswith('<') and raw.endswith('>'):
                raw = raw[1:-1]
            parsed = urlsplit(raw)
            if parsed.scheme or parsed.netloc:
                continue
            target = parsed.path
            if target.endswith('.md'):
                link_path = resolved_path(final_path.parent, target, 'final report link',
                                          errors, package_root=directory)
                if link_path:
                    linked.add(link_path)
        for did, dossier in dossiers.items():
            path = resolved_path(directory, dossier.get('path'), f'dossier {did}', [])
            if path and path not in linked:
                errors.append(f'final report missing link to dossier {did}')
        final_claims = {cid for cid, claim in claims.items()
                        if str(claim.get('section_id', '')).startswith('final:')
                        and (claim.get('claim_type') == 'factual' or
                             (claim.get('claim_type') == 'synthesis' and
                              claim.get('support_status') == 'supported' and
                              (claim.get('evidence_ids') or claim.get('cited_source_ids'))))}
        check_anchors(final, 'final report', final_claims,
                      claims, evidence, sources, display_numbers, errors)
    return {'status': 'invalid' if errors else 'ok', 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', required=True, help='Research run directory')
    parser.add_argument('--delivery', action='store_true',
                        help='Require a complete delivered package and persisted retrieval stop')
    args = parser.parse_args()
    result = verify(args.dir, delivery=args.delivery)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'ok' else 1)


if __name__ == '__main__':
    main()
