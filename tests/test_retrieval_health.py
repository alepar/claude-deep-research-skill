"""Retrieval health report: failures, recovery, and recommended actions."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.retrieval_health import analyze, infer_category, main, render_markdown


def write_run(directory, preflight=None, queries=None, retrievals=None):
    d = Path(directory)
    (d / 'run_manifest.json').write_text(json.dumps({'search_preflight': preflight}))
    if queries is not None:
        (d / 'queries.jsonl').write_text(''.join(json.dumps(q) + '\n' for q in queries))
    if retrievals is not None:
        (d / 'retrievals.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in retrievals))


OK_PREFLIGHT = {'status': 'ok', 'reason': None, 'selected_tool': 'search'}


class RetrievalHealthTest(unittest.TestCase):
    def test_clean_run_is_ok(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, OK_PREFLIGHT,
                      [{'query_id': 'q1', 'status': 'success', 'error': None}],
                      [{'retrieval_id': 'r1', 'tool': 'WebFetch', 'url': 'https://a.example/x',
                        'document_key': 'https://a.example/x', 'status': 'retrieved',
                        'content_scope': 'full', 'error': None}])
            report = analyze(d)
            self.assertEqual(report['status'], 'ok')
            self.assertEqual(report['actions'], [])
            self.assertIn('Status: OK', render_markdown(report))

    def test_recovered_fetch_is_not_degraded_but_is_listed(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, OK_PREFLIGHT, [], [
                {'retrieval_id': 'r1', 'tool': 'WebFetch', 'url': 'https://news.example/a',
                 'document_key': 'https://news.example/a', 'status': 'failed',
                 'content_scope': 'none', 'error': 'unable to fetch'},
                {'retrieval_id': 'r2', 'tool': 'search -m extract', 'url': 'https://news.example/a',
                 'document_key': 'https://news.example/a', 'status': 'retrieved',
                 'content_scope': 'full', 'error': None}])
            report = analyze(d)
            self.assertEqual(report['status'], 'ok')
            self.assertEqual(report['fetches']['recovered'][0]['recovered_by'], 'search -m extract')
            self.assertEqual(report['fetches']['documents_retrieved'], 1)
            self.assertIn('Recovered after a failed attempt', render_markdown(report))

    def test_inaccessible_documents_and_provider_failures_degrade_with_actions(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, OK_PREFLIGHT, [
                {'query_id': 'q1', 'query': 'topic', 'status': 'partial', 'error': 'brave failed',
                 'provider_failures': [{'provider': 'brave', 'category': 'bad_request'}]},
                {'query_id': 'q2', 'query': 'other', 'status': 'failed', 'error': 'HTTP 429',
                 'error_category': None}],
                [{'retrieval_id': 'r1', 'tool': 'search -m extract', 'url': 'https://www.linkedin.com/in/x',
                  'document_key': 'https://www.linkedin.com/in/x', 'status': 'failed',
                  'content_scope': 'none', 'error': 'login only', 'error_category': 'no_sanctioned_route'},
                 {'retrieval_id': 'r2', 'tool': 'search -m extract', 'url': 'https://walled.example/p',
                  'document_key': 'https://walled.example/p', 'status': 'failed',
                  'content_scope': 'none', 'error': 'denied by auto mode classifier'}])
            report = analyze(d)
            self.assertEqual(report['status'], 'degraded')
            cats = {a['category'] for a in report['actions']}
            self.assertEqual(cats, {'bad_request', 'rate_limit', 'no_sanctioned_route', 'permission_denied'})
            self.assertEqual(len(report['fetches']['inaccessible']), 2)
            text = render_markdown(report)
            self.assertIn('Status: DEGRADED', text)
            self.assertIn('https://www.linkedin.com/in/x', text)
            self.assertIn('| brave | bad_request | 1 |', text)

    def test_missing_logs_are_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, None)
            report = analyze(d)
            self.assertEqual(report['status'], 'degraded')
            self.assertIsNone(report['queries'])
            self.assertIsNone(report['fetches'])
            self.assertIn('unknown', render_markdown(report))

    def test_fallback_preflight_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, {'status': 'fallback', 'reason': 'search not installed',
                          'selected_tool': 'WebSearch'}, [], [])
            report = analyze(d)
            self.assertEqual(report['status'], 'degraded')
            self.assertIn('search not installed', render_markdown(report))

    def test_non_verbatim_high_priority_quote_degrades(self):
        with tempfile.TemporaryDirectory() as d:
            url = 'https://walled.example/p'
            write_run(d, OK_PREFLIGHT, [], [
                {'retrieval_id': 'r1', 'tool': 'search -m extract', 'url': url,
                 'document_key': url, 'status': 'failed', 'content_scope': 'none',
                 'error': 'blocked', 'error_category': 'blocked'},
                {'retrieval_id': 'r2', 'tool': 'WebFetch', 'url': url, 'document_key': url,
                 'status': 'retrieved', 'content_scope': 'full', 'error': None},
                {'retrieval_id': 'r3', 'tool': 'search -m extract', 'url': 'https://ok.example',
                 'document_key': 'https://ok.example', 'status': 'retrieved',
                 'content_scope': 'full', 'error': None}])
            (Path(d) / 'coverage.json').write_text(json.dumps({'facets': [
                {'id': 'F1', 'priority': 'high', 'active': True, 'evidence_ids': ['e1', 'e2'],
                 'contested_positions': []},
                {'id': 'F2', 'priority': 'supporting', 'active': True, 'evidence_ids': ['e3'],
                 'contested_positions': []}]}))
            (Path(d) / 'evidence.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in [
                {'evidence_id': 'e1', 'retrieval_id': 'r2', 'capture_tool': 'WebFetch',
                 'verbatim': False},
                {'evidence_id': 'e2', 'retrieval_id': 'r3', 'capture_tool': 'search -m extract',
                 'verbatim': True},
                {'evidence_id': 'e3', 'retrieval_id': 'r2', 'capture_tool': 'WebFetch',
                 'verbatim': False}]))
            report = analyze(d)
            self.assertEqual(report['status'], 'degraded')
            self.assertEqual(report['quotes']['high_priority_evidence'], 2)
            self.assertEqual([e['evidence_id'] for e in report['quotes']['non_verbatim']], ['e1'])
            self.assertIn('non_verbatim_quote', {a['category'] for a in report['actions']})
            text = render_markdown(report)
            self.assertIn('1 verbatim from search -m extract, 1 non-verbatim fallback', text)
            self.assertIn(f'| e1 | F1 | WebFetch | {url} |', text)

    def test_verbatim_high_priority_quotes_stay_ok(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, OK_PREFLIGHT, [], [
                {'retrieval_id': 'r1', 'tool': 'search -m extract', 'url': 'https://a.example',
                 'document_key': 'https://a.example', 'status': 'retrieved',
                 'content_scope': 'full', 'error': None}])
            (Path(d) / 'coverage.json').write_text(json.dumps({'facets': [
                {'id': 'F1', 'priority': 'high', 'active': True, 'evidence_ids': ['e1']}]}))
            (Path(d) / 'evidence.jsonl').write_text(json.dumps(
                {'evidence_id': 'e1', 'retrieval_id': 'r1', 'capture_tool': 'search -m extract',
                 'verbatim': True}) + '\n')
            self.assertEqual(analyze(d)['status'], 'ok')

    def test_infer_category(self):
        self.assertEqual(infer_category('blocked', 'whatever'), 'blocked')
        self.assertEqual(infer_category(None, 'no_sanctioned_route for linkedin'), 'no_sanctioned_route')
        self.assertEqual(infer_category(None, 'Request timed out'), 'timeout')
        self.assertEqual(infer_category(None, 'something odd'), 'other')

    def test_cli_json_output(self):
        with tempfile.TemporaryDirectory() as d:
            write_run(d, OK_PREFLIGHT, [], [])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = main(['--dir', d, '--json'])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue())['status'], 'ok')


if __name__ == '__main__':
    unittest.main()
