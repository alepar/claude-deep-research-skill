#!/usr/bin/env python3
"""Smoke tests for evidence_store.py CLI."""

import atexit
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'evidence_store.py')


# `add` calls the `search` CLI when it finds a registered source. Every run here
# gets this module's PATH, holding only a fake `search`, so no test can write
# marks into the user's live logs; the real binary is out of reach.
FAKE_DIR = tempfile.mkdtemp(prefix='fake-search-')
FAKE_CALLS = os.path.join(FAKE_DIR, 'calls')
FAKE_SEARCH = """#!/bin/sh
echo "$*" >> "{calls}"
if [ "$1" = agent-info ]; then
  echo '{{"commands": ["search", "stats", "mark-relevant"]}}'
fi
"""
OLD_SEARCH = """#!/bin/sh
echo "$*" >> "{calls}"
if [ "$1" = agent-info ]; then
  echo '{{"commands": ["search", "stats"]}}'
fi
"""
BROKEN_SEARCH = """#!/bin/sh
echo "$*" >> "{calls}"
echo not json
exit 1
"""


def install_fake_search(script: str = FAKE_SEARCH) -> None:
    path = os.path.join(FAKE_DIR, 'search')
    with open(path, 'w') as f:
        f.write(script.format(calls=FAKE_CALLS))
    os.chmod(path, 0o755)
    if os.path.exists(FAKE_CALLS):
        os.remove(FAKE_CALLS)


def fake_calls() -> list[str]:
    if not os.path.exists(FAKE_CALLS):
        return []
    with open(FAKE_CALLS) as f:
        return f.read().splitlines()


install_fake_search()
atexit.register(shutil.rmtree, FAKE_DIR, ignore_errors=True)
TEST_ENV = {**os.environ, 'PATH': FAKE_DIR, 'SEARCH_LOG': 'off'}


def run_es(*args: str, env: dict | None = None) -> dict | list:
    """Run evidence_store.py with args, return parsed JSON from stdout."""
    result = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True, env=env or TEST_ENV,
    )
    if result.returncode != 0:
        raise RuntimeError(f'Exit {result.returncode}: {result.stderr}')
    return json.loads(result.stdout)


class TestInit(unittest.TestCase):
    def test_creates_empty_file(self):
        with tempfile.TemporaryDirectory() as d:
            out = run_es('init', '--dir', d)
            self.assertEqual(out['status'], 'ok')
            path = os.path.join(d, 'evidence.jsonl')
            self.assertTrue(os.path.exists(path))
            self.assertEqual(os.path.getsize(path), 0)


class TestAddEvidence(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        run_es('init', '--dir', self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_add_and_dedup(self):
        ev = json.dumps({
            'source_id': 'abcdef0123456789',
            'quote': 'FActScore decomposes generation into atomic facts.',
            'evidence_type': 'direct_quote',
            'locator': 'page 3',
            'retrieval_query': 'factuality evaluation methods',
        })
        out1 = run_es('add', '--json', ev, '--dir', self.tmpdir)
        self.assertEqual(out1['status'], 'added')
        self.assertEqual(len(out1['evidence_id']), 16)

        # Same quote -> duplicate
        out2 = run_es('add', '--json', ev, '--dir', self.tmpdir)
        self.assertEqual(out2['status'], 'duplicate')
        self.assertEqual(out2['evidence_id'], out1['evidence_id'])

    def test_whitespace_normalization(self):
        ev1 = json.dumps({
            'source_id': 'abcdef0123456789',
            'quote': '  FActScore   decomposes   generation  into atomic facts.  ',
            'evidence_type': 'direct_quote',
        })
        ev2 = json.dumps({
            'source_id': 'abcdef0123456789',
            'quote': 'FActScore decomposes generation into atomic facts.',
            'evidence_type': 'direct_quote',
        })
        out1 = run_es('add', '--json', ev1, '--dir', self.tmpdir)
        out2 = run_es('add', '--json', ev2, '--dir', self.tmpdir)
        # Should be same ID due to normalization
        self.assertEqual(out1['evidence_id'], out2['evidence_id'])
        self.assertEqual(out2['status'], 'duplicate')

    def test_different_sources_different_ids(self):
        ev1 = json.dumps({
            'source_id': 'aaaaaaaaaaaaaaaa',
            'quote': 'Same quote text.',
            'evidence_type': 'paraphrase',
        })
        ev2 = json.dumps({
            'source_id': 'bbbbbbbbbbbbbbbb',
            'quote': 'Same quote text.',
            'evidence_type': 'paraphrase',
        })
        out1 = run_es('add', '--json', ev1, '--dir', self.tmpdir)
        out2 = run_es('add', '--json', ev2, '--dir', self.tmpdir)
        self.assertNotEqual(out1['evidence_id'], out2['evidence_id'])
        self.assertEqual(out2['status'], 'added')


class TestQuoteProvenance(unittest.TestCase):
    def test_verbatim_flag_and_capture_tool_are_stored(self):
        with tempfile.TemporaryDirectory() as d:
            run_es('init', '--dir', d)
            run_es('add', '--dir', d, '--json', json.dumps({
                'source_id': 'a' * 16, 'quote': 'Raw extract text.', 'locator': 'p. 2',
                'retrieval_id': 'R1', 'capture_tool': 'search -m extract', 'verbatim': True}))
            run_es('add', '--dir', d, '--json', json.dumps({
                'source_id': 'b' * 16, 'quote': 'Summarized text.', 'locator': None,
                'retrieval_id': 'R2', 'capture_tool': 'WebFetch', 'verbatim': False}))
            rows = run_es('export', '--dir', d)
            self.assertEqual([(r['capture_tool'], r['verbatim'], r['retrieval_id']) for r in rows],
                             [('search -m extract', True, 'R1'), ('WebFetch', False, 'R2')])

    def test_non_boolean_verbatim_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            run_es('init', '--dir', d)
            with self.assertRaises(RuntimeError):
                run_es('add', '--dir', d, '--json', json.dumps({
                    'source_id': 'a' * 16, 'quote': 'x', 'verbatim': 'yes'}))


class TestListAndExport(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        run_es('init', '--dir', self.tmpdir)
        # Add 3 evidence items from 2 sources
        for src, quote in [
            ('src_aaa', 'First quote from source A.'),
            ('src_aaa', 'Second quote from source A.'),
            ('src_bbb', 'Quote from source B.'),
        ]:
            run_es('add', '--json', json.dumps({
                'source_id': src,
                'quote': quote,
                'evidence_type': 'direct_quote',
            }), '--dir', self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_list_all(self):
        out = run_es('list', '--dir', self.tmpdir)
        self.assertEqual(out['count'], 3)

    def test_list_filtered(self):
        out = run_es('list', '--dir', self.tmpdir, '--source-id', 'src_aaa')
        self.assertEqual(out['count'], 2)

        out = run_es('list', '--dir', self.tmpdir, '--source-id', 'src_bbb')
        self.assertEqual(out['count'], 1)

    def test_export(self):
        out = run_es('export', '--dir', self.tmpdir)
        self.assertIsInstance(out, list)
        self.assertEqual(len(out), 3)
        # Each has required fields
        for row in out:
            self.assertIn('evidence_id', row)
            self.assertIn('source_id', row)
            self.assertIn('quote', row)
            self.assertIn('evidence_type', row)
            self.assertIn('captured_at', row)


class TestEvidenceID(unittest.TestCase):
    """Unit tests for compute_evidence_id."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from evidence_store import compute_evidence_id, normalize_quote
        cls.compute_id = staticmethod(compute_evidence_id)
        cls.normalize = staticmethod(normalize_quote)

    def test_deterministic(self):
        id1 = self.compute_id('src_a', 'test quote', 'page 1')
        id2 = self.compute_id('src_a', 'test quote', 'page 1')
        self.assertEqual(id1, id2)

    def test_locator_matters(self):
        id1 = self.compute_id('src_a', 'test quote', 'page 1')
        id2 = self.compute_id('src_a', 'test quote', 'page 2')
        self.assertNotEqual(id1, id2)

    def test_normalize_whitespace(self):
        self.assertEqual(
            self.normalize('  hello   world  '),
            'hello world',
        )


class TestMarkRelevant(unittest.TestCase):
    URL = 'https://example.test/paper'

    def setUp(self):
        install_fake_search()
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.addCleanup(install_fake_search)

    def register(self, source_id: str, **fields) -> None:
        row = {'source_id': source_id, **fields}
        with open(os.path.join(self.dir, 'sources.jsonl'), 'a') as f:
            f.write(json.dumps(row) + '\n')

    def add(self, source_id: str = 's1', quote: str = 'q', env: dict | None = None) -> dict:
        return run_es('add', '--dir', self.dir, '--json',
                      json.dumps({'source_id': source_id, 'quote': quote}), env=env)

    def marks(self) -> list[str]:
        return [c for c in fake_calls() if c.startswith('mark-relevant')]

    def test_tests_cannot_reach_the_real_binary(self):
        self.assertEqual(TEST_ENV['PATH'], FAKE_DIR)
        self.assertEqual(shutil.which('search', path=TEST_ENV['PATH']),
                         os.path.join(FAKE_DIR, 'search'))
        self.register('s1', raw_url=self.URL)
        self.add()
        self.assertEqual(fake_calls(), ['agent-info', f'mark-relevant {self.URL}'])

    def test_first_passage_of_a_source_marks_it_once(self):
        self.register('s1', raw_url=self.URL)
        self.register('s2', raw_url='https://example.test/other')
        self.add('s1', 'first')
        self.add('s1', 'second')
        self.add('s1', 'first')
        self.add('s2', 'third')
        self.assertEqual(self.marks(), [
            f'mark-relevant {self.URL}',
            'mark-relevant https://example.test/other',
        ])

    def test_canonical_locator_is_the_fallback(self):
        self.register('s1', canonical_locator=self.URL)
        self.add()
        self.assertEqual(self.marks(), [f'mark-relevant {self.URL}'])

    def test_older_binary_never_receives_the_command(self):
        # It would treat "mark-relevant URL" as a paid web search.
        install_fake_search(OLD_SEARCH)
        self.register('s1', raw_url=self.URL)
        self.assertEqual(self.add()['status'], 'added')
        self.assertEqual(fake_calls(), ['agent-info'])

    def test_failing_binary_does_not_affect_add(self):
        install_fake_search(BROKEN_SEARCH)
        self.register('s1', raw_url=self.URL)
        self.assertEqual(self.add()['status'], 'added')
        self.assertEqual(self.marks(), [])

    def test_missing_binary_does_not_affect_add(self):
        self.register('s1', raw_url=self.URL)
        with tempfile.TemporaryDirectory() as empty:
            out = self.add(env={**TEST_ENV, 'PATH': empty})
        self.assertEqual(out['status'], 'added')

    def test_unregistered_or_non_web_sources_are_not_marked(self):
        self.register('doi', canonical_locator='doi:10.1000/x')
        self.add('doi')
        self.add('unregistered')
        self.assertEqual(fake_calls(), [])

    def test_corrupt_sources_file_does_not_affect_add(self):
        with open(os.path.join(self.dir, 'sources.jsonl'), 'w') as f:
            f.write('{broken\n')
        self.assertEqual(self.add()['status'], 'added')

    def test_hung_binary_is_abandoned_at_the_timeout(self):
        install_fake_search('#!/bin/sh\nexec sleep 30\n')
        self.register('s1', raw_url=self.URL)
        spec = importlib.util.spec_from_file_location('evidence_store', SCRIPT)
        store = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(store)
        store.MARK_TIMEOUT_SECS = 0.2
        with mock.patch.dict(os.environ, {'PATH': FAKE_DIR}):
            store.mark_source_relevant(self.dir, 's1')  # Must return, not raise.


if __name__ == '__main__':
    unittest.main()
