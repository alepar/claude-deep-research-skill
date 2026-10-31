#!/usr/bin/env python3
"""
Retrieval health report for a deep-research run.

Reads run_manifest.json, queries.jsonl, and retrievals.jsonl from a run folder
and summarizes every search or fetch failure: which queries and URLs failed,
why, whether a later attempt recovered the document, and what the user can do
about it. The output tells the reader whether retrieval quality was degraded.

This is a report, not a gate: it always exits 0 on readable input.

Usage:
    python scripts/retrieval_health.py --dir [run_folder]          # Markdown
    python scripts/retrieval_health.py --dir [run_folder] --json   # JSON
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

# Failure categories. The first group mirrors search CLI's
# envelope.failure_categories; the second covers fetch and host outcomes.
CATEGORIES = (
    'auth', 'billing_quota', 'rate_limit', 'timeout', 'network', 'bad_request',
    'server', 'parse', 'config',
    'blocked', 'no_sanctioned_route', 'permission_denied', 'not_found', 'empty',
    'other',
)

ACTIONS = {
    'auth': 'Check the provider API key: run `search config check`, then `search doctor`.',
    'config': 'Fix search CLI configuration: run `search config check`.',
    'billing_quota': 'Provider credits or quota are exhausted: check `search usage` and top up or wait for the reset.',
    'rate_limit': 'Provider rate limit: rerun later or with fewer concurrent searches.',
    'timeout': 'Transient timeout: rerun the affected queries or fetches.',
    'network': 'Transient network failure: rerun the affected queries or fetches.',
    'server': 'Provider server error: rerun later; if persistent, run `search doctor`.',
    'bad_request': 'Request rejected as invalid: check flags (for example `-c` above a provider cap) and report to the search CLI maintainer if the flags were valid.',
    'parse': 'Provider returned an unreadable response: rerun; report to the search CLI maintainer if persistent.',
    'blocked': 'The site blocks automated reading: supply the document yourself, point to an archive copy, or accept findings that rest on other sources.',
    'no_sanctioned_route': 'Login-only site with no sanctioned reading route: supply the document yourself or accept snippet-only coverage.',
    'permission_denied': 'The host refused the tool call: allow it in the agent permission settings (for example a Bash rule for `search *`) and rerun, or fetch the page manually.',
    'not_found': 'The URL is dead or moved: find a current or archived copy.',
    'empty': 'The page returned no usable text (empty or script-only shell): try another copy of the document.',
    'other': 'Inspect the recorded error text.',
}

_INFER = (
    ('no_sanctioned_route', r'no[_ ]sanctioned[_ ]route'),
    ('permission_denied', r'permission|classifier|denied by|not allowed'),
    ('blocked', r'\bblocked\b|bot wall|login wall|captcha|unable to fetch'),
    ('rate_limit', r'rate[_ -]?limit|\b429\b|too many requests'),
    ('billing_quota', r'quota|billing|credits|payment|\b402\b'),
    ('auth', r'\bauth|unauthori[sz]ed|forbidden|api key|\b401\b|\b403\b'),
    ('timeout', r'time(d)?[ -]?out'),
    ('not_found', r'\b404\b|\b410\b|not found'),
    ('bad_request', r'\b400\b|\b422\b|bad request|invalid|validation'),
    ('server', r'\b5\d\d\b|server error'),
    ('network', r'network|connection|dns|unreachable'),
    ('empty', r'\bempty\b|no content'),
)


def infer_category(category, error):
    """Use the recorded category, or infer one from the error text."""
    if category in CATEGORIES:
        return category
    text = (error or '').lower()
    for name, pattern in _INFER:
        if re.search(pattern, text):
            return name
    return 'other'


def read_jsonl(path):
    """Return rows, or None when the log is missing (unknown, not empty)."""
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as f:
        for number, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f'{path}:{number}: invalid JSON: {exc}') from exc
    return rows


def read_manifest(directory):
    path = os.path.join(directory, 'run_manifest.json')
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def analyze(directory):
    manifest = read_manifest(directory)
    queries = read_jsonl(os.path.join(directory, 'queries.jsonl'))
    retrievals = read_jsonl(os.path.join(directory, 'retrievals.jsonl'))

    report = {
        'status': 'ok',
        'reasons': [],
        'preflight': None,
        'queries': None,
        'provider_failures': [],
        'fetches': None,
        'actions': [],
    }
    categories = OrderedDict()  # category -> list of affected labels

    def note(category, label):
        categories.setdefault(category, []).append(label)

    preflight = (manifest or {}).get('search_preflight')
    report['preflight'] = preflight
    if preflight is None:
        report['reasons'].append('search preflight not recorded')
    elif preflight.get('status') != 'ok':
        report['reasons'].append(
            f"search preflight {preflight.get('status')}: {preflight.get('reason') or 'no reason recorded'}")

    if queries is None:
        report['reasons'].append('queries.jsonl missing: query accounting unknown')
    else:
        statuses = Counter(q.get('status') or 'unknown' for q in queries)
        failed = []
        provider_counts = Counter()
        for q in queries:
            qid = q.get('query_id') or '?'
            if q.get('status') == 'failed':
                cat = infer_category(q.get('error_category'), q.get('error'))
                failed.append({'query_id': qid, 'query': q.get('query'),
                               'category': cat, 'error': q.get('error')})
                note(cat, f'query {qid}')
            for pf in q.get('provider_failures') or []:
                cat = infer_category(pf.get('category'), pf.get('reason'))
                provider_counts[(pf.get('provider') or '?', cat)] += 1
                note(cat, f"provider {pf.get('provider') or '?'}")
        report['queries'] = {'attempts': len(queries), 'by_status': dict(statuses),
                             'failed': failed}
        report['provider_failures'] = [
            {'provider': p, 'category': c, 'queries_affected': n}
            for (p, c), n in sorted(provider_counts.items())]
        if failed:
            report['reasons'].append(f'{len(failed)} search attempt(s) failed')
        if provider_counts:
            report['reasons'].append(
                f'{len(provider_counts)} provider failure type(s) reduced search coverage')

    if retrievals is None:
        report['reasons'].append('retrievals.jsonl missing: fetch accounting unknown')
    else:
        docs = OrderedDict()
        for r in retrievals:
            key = r.get('document_key') or r.get('url') or '?'
            docs.setdefault(key, []).append(r)
        recovered, inaccessible, partial = [], [], []
        for key, attempts in docs.items():
            ok = [a for a in attempts if a.get('status') == 'retrieved']
            failures = [a for a in attempts if a.get('status') != 'retrieved']
            if ok and all(a.get('content_scope') == 'partial' for a in ok):
                partial.append(key)
            if not failures:
                continue
            rows = [{'url': a.get('url'), 'tool': a.get('tool'),
                     'category': infer_category(a.get('error_category'), a.get('error')),
                     'error': a.get('error')} for a in failures]
            entry = {'document_key': key, 'failed_attempts': rows}
            if ok:
                entry['recovered_by'] = ok[0].get('tool')
                recovered.append(entry)
            else:
                inaccessible.append(entry)
                for row in rows:
                    note(row['category'], row['url'] or key)
        report['fetches'] = {
            'attempts': len(retrievals),
            'documents_retrieved': sum(
                1 for a in docs.values() if any(x.get('status') == 'retrieved' for x in a)),
            'failed_attempts': sum(1 for r in retrievals if r.get('status') != 'retrieved'),
            'recovered': recovered,
            'inaccessible': inaccessible,
            'partial_only': partial,
        }
        if inaccessible:
            report['reasons'].append(f'{len(inaccessible)} document(s) still inaccessible')

    for cat, labels in categories.items():
        report['actions'].append({'category': cat, 'action': ACTIONS[cat],
                                  'affected': sorted(set(labels))})
    if report['reasons']:
        report['status'] = 'degraded'
    return report


def _cell(text):
    return str(text if text is not None else '').replace('|', '\\|').replace('\n', ' ')


def render_markdown(report):
    out = ['### Retrieval health', '']
    if report['status'] == 'ok':
        out.append('**Status: OK.** No search or fetch failures left a gap.')
    else:
        out.append('**Status: DEGRADED.** ' + '; '.join(report['reasons']) + '.')
    out.append('')

    pre = report['preflight']
    if pre:
        out.append(f"- Search preflight: {pre.get('status')} "
                   f"({pre.get('selected_tool') or 'no tool recorded'})"
                   + (f" - {pre.get('reason')}" if pre.get('reason') else ''))
    q = report['queries']
    if q is None:
        out.append('- Search attempts: unknown (no queries.jsonl)')
    else:
        parts = ', '.join(f'{v} {k}' for k, v in sorted(q['by_status'].items()))
        out.append(f"- Search attempts: {q['attempts']} ({parts})")
    f = report['fetches']
    if f is None:
        out.append('- Document fetches: unknown (no retrievals.jsonl)')
    else:
        out.append(f"- Document fetches: {f['attempts']} attempts, "
                   f"{f['documents_retrieved']} distinct documents read, "
                   f"{f['failed_attempts']} failed attempts, "
                   f"{len(f['recovered'])} recovered, {len(f['inaccessible'])} still inaccessible")
        if f['partial_only']:
            out.append(f"- Partial text only: {len(f['partial_only'])} document(s)")
    out.append('')

    if report['provider_failures']:
        out += ['Provider failures (search still returned results from other providers):', '',
                '| Provider | Category | Queries affected |', '|---|---|---|']
        out += [f"| {_cell(p['provider'])} | {p['category']} | {p['queries_affected']} |"
                for p in report['provider_failures']]
        out.append('')
    if q and q['failed']:
        out += ['Failed searches:', '', '| Query ID | Query | Category | Error |', '|---|---|---|---|']
        out += [f"| {_cell(x['query_id'])} | {_cell(x['query'])} | {x['category']} | {_cell(x['error'])} |"
                for x in q['failed']]
        out.append('')
    if f and f['inaccessible']:
        out += ['Documents still inaccessible:', '', '| URL | Tools tried | Category | Error |',
                '|---|---|---|---|']
        for d in f['inaccessible']:
            last = d['failed_attempts'][-1]
            tools = ', '.join(OrderedDict.fromkeys(a['tool'] or '?' for a in d['failed_attempts']))
            out.append(f"| {_cell(last['url'] or d['document_key'])} | {_cell(tools)} | "
                       f"{last['category']} | {_cell(last['error'])} |")
        out.append('')
    if f and f['recovered']:
        out += ['Recovered after a failed attempt:', '', '| URL | Failed with | Recovered by |',
                '|---|---|---|']
        for d in f['recovered']:
            failed_tools = ', '.join(f"{a['tool'] or '?'} ({a['category']})" for a in d['failed_attempts'])
            out.append(f"| {_cell(d['failed_attempts'][0]['url'] or d['document_key'])} | "
                       f"{_cell(failed_tools)} | {_cell(d['recovered_by'])} |")
        out.append('')
    if report['actions']:
        out += ['Recommended actions:', '']
        for a in report['actions']:
            affected = ', '.join(a['affected'][:5])
            more = len(a['affected']) - 5
            if more > 0:
                affected += f' and {more} more'
            out.append(f"- **{a['category']}** ({affected}): {a['action']}")
        out.append('')
    return '\n'.join(out).rstrip() + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description='Summarize search and fetch failures for a research run')
    parser.add_argument('--dir', required=True, help='Research run folder')
    parser.add_argument('--json', action='store_true', help='Print JSON instead of Markdown')
    args = parser.parse_args(argv)
    try:
        report = analyze(args.dir)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f'retrieval_health: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(report), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
