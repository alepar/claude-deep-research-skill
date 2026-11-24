#!/usr/bin/env python3
"""Run the read-only delivery checks for a research run and print one summary.

Run it from the session that wrote the final report, after claim support has
been judged and verified. It writes nothing. Checks, in order: coverage with a
persisted stop, the delivery package, the Markdown surface of the final report
and each dossier, citations, and retrieval health (the report must embed the
current status line). Exit 0 means every check passed; a DEGRADED retrieval
health status does not fail delivery but must be disclosed to the user.
"""

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

try:
    from . import retrieval_health, validate_report, validate_report_package
    from . import verify_citations, verify_coverage
except ImportError:
    import retrieval_health
    import validate_report
    import validate_report_package
    import verify_citations
    import verify_coverage


MAX_DETAIL_LINES = 12
# Wall-clock seconds for bibliography DOI/URL lookups before the rest are
# reported as not checked, so an offline or blocked network cannot stall delivery.
DEFAULT_URL_BUDGET = 120


def quiet(function, *args, **kwargs):
    """Call a validator, keeping its own console output out of the summary."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        result = function(*args, **kwargs)
    return result, buffer.getvalue()


def planned_artifacts(directory):
    """Return (final path, dossier paths) or a list of blocking problems."""
    try:
        manifest = json.loads((directory / 'run_manifest.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as exc:
        return None, None, [f'cannot read run_manifest.json: {exc}']
    reporting = manifest.get('reporting')
    if not isinstance(reporting, dict) or not reporting.get('final_report_path'):
        return None, None, ['run_manifest.json has no reporting.final_report_path; '
                            'record the planned report path, write the report, then rerun']
    final = directory / reporting['final_report_path']
    dossiers = [directory / row['path'] for row in reporting.get('dossiers') or []
                if isinstance(row, dict) and isinstance(row.get('path'), str)]
    missing = [path for path in [final, *dossiers] if not path.is_file()]
    problems = [f'not yet written: {path.relative_to(directory)}' for path in missing]
    if problems:
        problems.append('the top-level session writes the report and dossiers from the '
                        'ledgers (reference/report-assembly.md), then reruns this command')
    return final, dossiers, problems


def check_coverage(directory, **_):
    try:
        result = verify_coverage.verify(str(directory), require_stop=True)
    except (TypeError, AttributeError, KeyError, IndexError) as exc:
        result = {'status': 'invalid', 'errors': [f'malformed coverage structure: {exc}']}
    return result['status'] == 'ok', result.get('errors', [])


def check_package(directory, **_):
    result = validate_report_package.verify(str(directory), delivery=True)
    return result['status'] == 'ok', result.get('errors', [])


def check_surface(directory, final, dossiers, **_):
    errors = []
    for path in [final, *dossiers]:
        validator = validate_report.ReportValidator(path)
        ok, _ = quiet(validator.validate)
        if not ok:
            errors.extend(f'{path.relative_to(directory)}: {e}' for e in validator.errors)
    return not errors, errors


def check_citations(directory, final, network=True, budget=None, **_):
    verifier = verify_citations.CitationVerifier(final, network=network, budget=budget)
    ok, output = quiet(verifier.verify_all)
    reach = (f'network checks: {verifier.checked} run, {verifier.not_checked} skipped'
             + ('' if network else ' (offline)')
             + (' (time budget spent)' if network and verifier.not_checked else ''))
    if ok:
        return True, [reach]
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    return False, (lines[-MAX_DETAIL_LINES + 1:] or ['citation verification failed']) + [reach]


def check_health(directory, final, health, **_):
    status_line = retrieval_health.render_markdown(health).splitlines()[2]
    if status_line not in final.read_text(encoding='utf-8'):
        return False, ['final report does not embed the current retrieval health status; '
                       'paste the output of retrieval_health.py into its Methodology section',
                       f'expected: {status_line}']
    return True, []


CHECKS = [
    ('coverage', 'verify_coverage.py --require-stop', check_coverage),
    ('package', 'validate_report_package.py --delivery', check_package),
    ('surface', 'validate_report.py on final report and dossiers', check_surface),
    ('citations', 'verify_citations.py', check_citations),
    ('health', 'retrieval_health.py status embedded in report', check_health),
]


def finish(directory, network=True, budget=DEFAULT_URL_BUDGET):
    """Return (exit code, summary text)."""
    directory = Path(directory)
    out = [f'finish_delivery: {directory}']
    final, dossiers, problems = planned_artifacts(directory)
    if problems:
        out.append('FAIL report package is not written')
        out.extend(f'  - {p}' for p in problems)
        out.append('Result: NOT READY (no delivery checks ran)')
        return 1, '\n'.join(out) + '\n'
    try:
        health = retrieval_health.analyze(str(directory))
    except (ValueError, json.JSONDecodeError) as exc:
        health = None
        health_error = str(exc)
    failed = 0
    for name, command, check in CHECKS:
        if name == 'health' and health is None:
            ok, details = False, [f'retrieval_health failed: {health_error}']
        else:
            ok, details = check(directory, final=final, dossiers=dossiers, health=health,
                                network=network, budget=budget)
        failed += not ok
        out.append(f'{"PASS" if ok else "FAIL"} {name} ({command})')
        out.extend(f'  - {d}' for d in details[:MAX_DETAIL_LINES])
        if len(details) > MAX_DETAIL_LINES:
            out.append(f'  - ... {len(details) - MAX_DETAIL_LINES} more')
    if health is not None:
        out.append('Retrieval health: ' + health['status'].upper() +
                   ('' if health['status'] == 'ok' else ' - ' + '; '.join(health['reasons'])))
        for action in health['actions']:
            out.append(f'  - {action["category"]}: {action["action"]}')
    out.append('Result: READY' if not failed else f'Result: NOT READY ({failed} check(s) failed)')
    return (0 if not failed else 1), '\n'.join(out) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', required=True, help='Research run directory')
    parser.add_argument('--offline', action='store_true',
                        help='Skip bibliography DOI/URL lookups (recorded in the summary)')
    parser.add_argument('--url-budget', type=float, default=DEFAULT_URL_BUDGET, metavar='SECONDS',
                        help=f'Seconds for bibliography lookups (default {DEFAULT_URL_BUDGET})')
    args = parser.parse_args(argv)
    code, summary = finish(args.dir, network=not args.offline, budget=args.url_budget)
    print(summary, end='')
    return code


if __name__ == '__main__':
    sys.exit(main())
