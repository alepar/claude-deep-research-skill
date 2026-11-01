#!/usr/bin/env python3
"""
Evidence Store — append-only evidence persistence for deep-research v3.0.

CLI subcommands:
  init         Create empty evidence.jsonl in a run directory
  add          Append an evidence row, return evidence_id
  list         List evidence rows, optionally filtered by source_id
  export       Export evidence as JSON array

Evidence identity:
  evidence_id = sha256(source_id + normalized_quote + locator)[:16]

All state is append-only JSONL. Evidence is never modified after capture.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Evidence ID computation
# ---------------------------------------------------------------------------

_WHITESPACE_RE = re.compile(r'\s+')


def normalize_quote(quote: str) -> str:
    """Normalize whitespace for stable hashing."""
    return _WHITESPACE_RE.sub(' ', quote.strip()).lower()


def compute_evidence_id(source_id: str, quote: str, locator: str | None) -> str:
    """sha256(source_id + normalized_quote + locator)[:16] hex."""
    payload = source_id + normalize_quote(quote) + (locator or '')
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]


# ---------------------------------------------------------------------------
# JSONL helpers (shared pattern with citation_manager)
# ---------------------------------------------------------------------------

def append_jsonl(path: str, obj: dict) -> None:
    with open(path, 'a') as f:
        f.write(json.dumps(obj, ensure_ascii=False) + '\n')


def read_jsonl(path: str) -> list[dict]:
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Provider relevance signal
# ---------------------------------------------------------------------------

MARK_TIMEOUT_SECS = 5


def source_url(run_dir: str, source_id: str) -> str | None:
    """The registered http(s) URL of a source, if it has one."""
    for row in read_jsonl(os.path.join(run_dir, 'sources.jsonl')):
        if row.get('source_id') == source_id:
            url = row.get('raw_url') or row.get('canonical_locator')
            if isinstance(url, str) and url.startswith(('http://', 'https://')):
                return url
    return None


def supports_mark_relevant(search: str) -> bool:
    """Ask agent-info, never the command itself: an older binary reads
    `search mark-relevant URL` as a query and runs a paid web search."""
    info = subprocess.run(
        [search, 'agent-info'], capture_output=True, text=True,
        stdin=subprocess.DEVNULL, timeout=MARK_TIMEOUT_SECS,
    )
    return 'mark-relevant' in json.loads(info.stdout).get('commands', [])


def mark_source_relevant(run_dir: str, source_id: str) -> None:
    """Tell the search CLI this source was useful, whichever tool fetched it,
    so `search stats` can credit the providers that returned it. Best effort:
    provider monitoring must never affect a research run, so every failure is
    swallowed."""
    try:
        search = shutil.which('search')
        url = source_url(run_dir, source_id)
        if search and url and supports_mark_relevant(search):
            subprocess.run(
                [search, 'mark-relevant', url],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, timeout=MARK_TIMEOUT_SECS,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    """Create empty evidence.jsonl if it doesn't exist."""
    out_dir = os.path.abspath(args.dir)
    path = os.path.join(out_dir, 'evidence.jsonl')
    if not os.path.exists(path):
        os.makedirs(out_dir, exist_ok=True)
        open(path, 'w').close()
    print(json.dumps({'status': 'ok', 'path': path}))


def cmd_add(args: argparse.Namespace) -> None:
    """Append evidence row, print evidence_id."""
    data = json.loads(args.json)
    source_id = data.get('source_id', '')
    quote = data.get('quote', '')
    if not source_id or not quote:
        print(json.dumps({'error': 'source_id and quote are required'}), file=sys.stderr)
        sys.exit(1)

    locator = data.get('locator')
    evidence_id = compute_evidence_id(source_id, quote, locator)
    evidence_path = os.path.join(args.dir, 'evidence.jsonl')

    # Check for duplicate
    existing = read_jsonl(evidence_path)
    for row in existing:
        if row.get('evidence_id') == evidence_id:
            print(json.dumps({
                'status': 'duplicate',
                'evidence_id': evidence_id,
            }))
            return

    valid_types = {'direct_quote', 'paraphrase', 'data_point', 'figure_reference', 'methodology'}
    evidence_type = data.get('evidence_type', 'direct_quote')
    if evidence_type not in valid_types:
        evidence_type = 'direct_quote'

    row = {
        'evidence_id': evidence_id,
        'source_id': source_id,
        'retrieval_query': data.get('retrieval_query'),
        'locator': locator,
        'quote': quote,
        'evidence_type': evidence_type,
        'captured_at': datetime.now(timezone.utc).isoformat(),
    }
    # Quote provenance: which retrieval attempt and tool produced the text, and
    # whether it is copied from raw page text (search -m extract) or from a
    # summarizing fetch tool. Required for high-priority facets by
    # verify_coverage.py; absent fields stay absent for legacy callers.
    for field in ('retrieval_id', 'capture_tool'):
        if data.get(field) is not None:
            row[field] = data[field]
    if 'verbatim' in data:
        if not isinstance(data['verbatim'], bool):
            print(json.dumps({'error': 'verbatim must be true or false'}), file=sys.stderr)
            sys.exit(1)
        row['verbatim'] = data['verbatim']
    # A paraphrase stays one: an extract attempt logged with verbatim false
    # (a Reddit search_index copy) marks every quote taken from it.
    attempt = next((r for r in read_jsonl(os.path.join(args.dir, 'retrievals.jsonl'))
                    if r.get('retrieval_id') == row.get('retrieval_id')), {})
    if attempt.get('verbatim') is False:
        if row.get('verbatim') is True:
            print(json.dumps({'error': f"retrieval {row['retrieval_id']} returned a paraphrase: "
                                       'its quotes cannot be verbatim'}), file=sys.stderr)
            sys.exit(1)
        row['verbatim'] = False
    append_jsonl(evidence_path, row)
    print(json.dumps({
        'status': 'added',
        'evidence_id': evidence_id,
        'source_id': source_id,
    }), flush=True)
    # The first retained passage is what makes a document useful; more
    # passages from it are not a new signal.
    if not any(row.get('source_id') == source_id for row in existing):
        mark_source_relevant(args.dir, source_id)


def cmd_list(args: argparse.Namespace) -> None:
    """List evidence rows, optionally filtered."""
    evidence_path = os.path.join(args.dir, 'evidence.jsonl')
    rows = read_jsonl(evidence_path)

    if args.source_id:
        rows = [r for r in rows if r.get('source_id') == args.source_id]

    # Deduplicate by evidence_id
    seen = set()
    unique = []
    for r in rows:
        eid = r.get('evidence_id')
        if eid not in seen:
            seen.add(eid)
            unique.append(r)

    print(json.dumps({
        'count': len(unique),
        'evidence': unique,
    }, indent=2, ensure_ascii=False))


def cmd_export(args: argparse.Namespace) -> None:
    """Export all evidence as JSON array."""
    evidence_path = os.path.join(args.dir, 'evidence.jsonl')
    rows = read_jsonl(evidence_path)

    # Deduplicate
    seen = set()
    unique = []
    for r in rows:
        eid = r.get('evidence_id')
        if eid not in seen:
            seen.add(eid)
            unique.append(r)

    print(json.dumps(unique, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog='evidence_store',
        description='Append-only evidence persistence for deep-research v3.0',
    )
    sub = parser.add_subparsers(dest='command', required=True)

    # init
    p_init = sub.add_parser('init', help='Create empty evidence.jsonl')
    p_init.add_argument('--dir', required=True, help='Run directory')

    # add
    p_add = sub.add_parser('add', help='Append evidence row')
    p_add.add_argument('--json', required=True, help='JSON with source_id, quote, locator, evidence_type, retrieval_query, '
                       'and quote provenance: retrieval_id, capture_tool, verbatim')
    p_add.add_argument('--dir', required=True, help='Run directory containing evidence.jsonl')

    # list
    p_list = sub.add_parser('list', help='List evidence rows')
    p_list.add_argument('--dir', required=True, help='Run directory')
    p_list.add_argument('--source-id', default=None, help='Filter by source_id')

    # export
    p_export = sub.add_parser('export', help='Export all evidence as JSON array')
    p_export.add_argument('--dir', required=True, help='Run directory')

    args = parser.parse_args()

    dispatch = {
        'init': cmd_init,
        'add': cmd_add,
        'list': cmd_list,
        'export': cmd_export,
    }
    dispatch[args.command](args)


if __name__ == '__main__':
    main()
