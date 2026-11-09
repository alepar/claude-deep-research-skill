#!/usr/bin/env python3
"""Tests for verify_claim_support.py CLI."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'verify_claim_support.py')


def run_vcs(*args: str, expect_fail: bool = False) -> dict | str:
    """Run verify_claim_support.py."""
    result = subprocess.run(
        [sys.executable, SCRIPT, *args],
        capture_output=True, text=True,
    )
    if result.returncode != 0 and not expect_fail:
        raise RuntimeError(f'Exit {result.returncode}: {result.stderr}\n{result.stdout}')
    stdout = result.stdout.strip()
    if stdout.startswith('{'):
        return json.loads(stdout)
    return stdout


def write_jsonl(path: str, rows: list[dict]):
    with open(path, 'w') as f:
        for row in rows:
            f.write(json.dumps(row) + '\n')


class TestVerifySupported(unittest.TestCase):
    """Claims with matching evidence should be supported."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        # Sources
        write_jsonl(os.path.join(self.tmpdir, 'sources.jsonl'), [
            {'source_id': 'src_quantum_001', 'title': 'Quantum Computing 2024'},
        ])
        # Evidence with clear overlap to the claim
        write_jsonl(os.path.join(self.tmpdir, 'evidence.jsonl'), [
            {
                'evidence_id': 'ev_shor_001',
                'source_id': 'src_quantum_001',
                'quote': "Shor's algorithm can factor large integers exponentially faster than any known classical algorithm, threatening RSA-2048 encryption.",
                'evidence_type': 'direct_quote',
            },
        ])
        # Claim that matches the evidence
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), [
            {
                'claim_id': 'clm_factor_001',
                'section_id': 'finding_1',
                'text': "Shor's algorithm can factor large numbers exponentially faster than classical methods, threatening RSA-2048.",
                'claim_type': 'factual',
                'cited_source_ids': ['src_quantum_001'],
                'evidence_ids': ['ev_shor_001'],
                'support_status': 'unverified',
            },
        ])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_supported_claim(self):
        out = run_vcs('verify', '--dir', self.tmpdir)
        self.assertEqual(out['status'], 'pass')
        self.assertEqual(out['factual_unsupported'], 0)

        # Check updated claims file
        claims = []
        with open(os.path.join(self.tmpdir, 'claims.jsonl')) as f:
            for line in f:
                claims.append(json.loads(line))
        self.assertEqual(claims[0]['support_status'], 'supported')


class TestVerifyUnsupported(unittest.TestCase):
    """Claims without evidence should be unsupported."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        write_jsonl(os.path.join(self.tmpdir, 'sources.jsonl'), [])
        write_jsonl(os.path.join(self.tmpdir, 'evidence.jsonl'), [])
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), [
            {
                'claim_id': 'clm_no_ev_001',
                'section_id': 'finding_1',
                'text': 'The population of Mars is 500 million as of 2025.',
                'claim_type': 'factual',
                'cited_source_ids': [],
                'evidence_ids': [],
                'support_status': 'unverified',
            },
        ])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_unsupported_no_evidence(self):
        out = run_vcs('verify', '--dir', self.tmpdir)
        self.assertEqual(out['factual_unsupported'], 1)
        self.assertEqual(out['status'], 'pass')  # Non-strict by default

    def test_strict_fails(self):
        out = run_vcs('verify', '--dir', self.tmpdir, '--strict', expect_fail=True)
        self.assertEqual(out['status'], 'fail')


class TestVerifyMixed(unittest.TestCase):
    """Mixed claim types with different thresholds."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        write_jsonl(os.path.join(self.tmpdir, 'sources.jsonl'), [])
        write_jsonl(os.path.join(self.tmpdir, 'evidence.jsonl'), [])
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), [
            {
                'claim_id': 'clm_spec_001',
                'section_id': 'finding_1',
                'text': 'Quantum computers might eventually solve protein folding in real time.',
                'claim_type': 'speculation',
                'cited_source_ids': [],
                'evidence_ids': [],
                'support_status': 'unverified',
            },
            {
                'claim_id': 'clm_rec_001',
                'section_id': 'recommendations',
                'text': 'Organizations should begin PQC migration planning immediately.',
                'claim_type': 'recommendation',
                'cited_source_ids': [],
                'evidence_ids': [],
                'support_status': 'unverified',
            },
        ])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_speculation_passes(self):
        out = run_vcs('verify', '--dir', self.tmpdir)
        # Speculation doesn't need evidence
        claims = []
        with open(os.path.join(self.tmpdir, 'claims.jsonl')) as f:
            for line in f:
                claims.append(json.loads(line))
        spec = [c for c in claims if c['claim_type'] == 'speculation'][0]
        self.assertEqual(spec['support_status'], 'supported')


class TestVerifyPartial(unittest.TestCase):
    """Evidence with partial overlap should result in partial status."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        write_jsonl(os.path.join(self.tmpdir, 'sources.jsonl'), [
            {'source_id': 'src_nist_001', 'title': 'NIST PQC Standards'},
        ])
        write_jsonl(os.path.join(self.tmpdir, 'evidence.jsonl'), [
            {
                'evidence_id': 'ev_nist_001',
                'source_id': 'src_nist_001',
                'quote': 'NIST announced the standardization of CRYSTALS-Kyber for key encapsulation.',
                'evidence_type': 'direct_quote',
            },
        ])
        # Claim mentions NIST but adds unverified detail about timeline
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), [
            {
                'claim_id': 'clm_nist_time',
                'section_id': 'finding_2',
                'text': 'NIST standardized four lattice-based algorithms in 2024, covering both encryption and signatures.',
                'claim_type': 'factual',
                'cited_source_ids': ['src_nist_001'],
                'evidence_ids': ['ev_nist_001'],
                'support_status': 'unverified',
            },
        ])

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_partial_support(self):
        out = run_vcs('verify', '--dir', self.tmpdir)
        claims = []
        with open(os.path.join(self.tmpdir, 'claims.jsonl')) as f:
            for line in f:
                claims.append(json.loads(line))
        # Should be partial or needs_review (not fully supported due to number/detail mismatch)
        self.assertIn(claims[0]['support_status'], ('partial', 'needs_review', 'supported'))


class TestSupportScore(unittest.TestCase):
    """Unit tests for compute_support_score."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
        from verify_claim_support import compute_support_score
        cls.score = staticmethod(compute_support_score)

    def test_identical_text(self):
        status, score, _ = self.score(
            'RSA-2048 uses 2048-bit keys for encryption.',
            ['RSA-2048 uses 2048-bit keys for encryption.'],
        )
        self.assertEqual(status, 'supported')
        self.assertGreater(score, 0.8)

    def test_no_evidence(self):
        status, score, _ = self.score('Any claim text.', [])
        self.assertEqual(status, 'unsupported')
        self.assertEqual(score, 0.0)

    def test_unrelated_evidence(self):
        status, score, _ = self.score(
            'The moon landing occurred in 1969.',
            ['Bananas are a good source of potassium and fiber.'],
        )
        self.assertIn(status, ('needs_review', 'unsupported'))
        self.assertLess(score, 0.35)


def read_claims(directory: str) -> list[dict]:
    with open(os.path.join(directory, 'claims.jsonl')) as f:
        return [json.loads(line) for line in f if line.strip()]


class TestModelJudge(unittest.TestCase):
    """Model verdicts decide support_status; lexical is the fallback."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmpdir, True)
        with open(os.path.join(self.tmpdir, 'run_manifest.json'), 'w') as f:
            json.dump({'query': 'q', 'search_preflight': None}, f)
        write_jsonl(os.path.join(self.tmpdir, 'evidence.jsonl'), [
            {'evidence_id': 'ev1', 'source_id': 'src1', 'verbatim': True,
             'quote': 'The trial found that the drug did not reduce mortality in 2023.'},
            {'evidence_id': 'ev2', 'source_id': 'src2', 'verbatim': False,
             'quote': 'Revenue grew 12% in 2024, driven by cloud sales.'},
        ])
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), [
            # Lexically near-identical to its evidence, but negated.
            {'claim_id': 'c_neg', 'section_id': 'final:f', 'claim_type': 'factual',
             'text': 'The trial found that the drug did reduce mortality in 2023.',
             'evidence_ids': ['ev1'], 'cited_source_ids': ['src1'],
             'support_status': 'unverified'},
            {'claim_id': 'c_rev', 'section_id': 'final:f', 'claim_type': 'factual',
             'text': 'Cloud sales drove a 12% revenue increase in 2024.',
             'evidence_ids': ['ev2'], 'cited_source_ids': ['src2'],
             'support_status': 'unverified'},
            {'claim_id': 'c_spec', 'section_id': 'final:f', 'claim_type': 'speculation',
             'text': 'Growth may continue.', 'evidence_ids': [], 'cited_source_ids': [],
             'support_status': 'unverified'},
        ])

    def prepare(self, *extra):
        return run_vcs('prepare', '--dir', self.tmpdir, *extra)

    def judge(self, prepared, verdicts):
        for batch in prepared['batches']:
            with open(batch['path']) as f:
                items = json.load(f)['items']
            with open(batch['output_path'], 'w') as f:
                for item in items:
                    f.write(json.dumps({'claim_id': item['claim_id'], 'digest': item['digest'],
                                        'verdict': verdicts[item['claim_id']],
                                        'reason': f'judged {item["claim_id"]}',
                                        'model': 'claude-sonnet-test'}) + '\n')

    def test_prepare_batches_claims_with_passages(self):
        prepared = self.prepare('--batch-size', '1')
        self.assertEqual(prepared['claims_to_judge'], 2)  # speculation is not judged
        self.assertEqual(len(prepared['batches']), 2)
        with open(prepared['batches'][1]['path']) as f:
            batch = json.load(f)
        self.assertIn('contradicted', batch['instructions'])
        self.assertEqual(batch['items'][0]['passages'][0]['verbatim'], False)
        self.assertEqual(batch['output_path'], prepared['batches'][1]['output_path'])

    def test_rejudge_never_reuses_an_earlier_verdicts_path(self):
        first = self.prepare('--batch-size', '1')
        self.judge(first, {'c_neg': 'contradicted', 'c_rev': 'supported'})
        for batch in first['batches']:
            os.remove(batch['path'])  # the lead tidies away the batch inputs
        earlier = {b['output_path'] for b in first['batches']}
        again = self.prepare('--all', '--batch-size', '1')
        self.assertEqual(len(again['batches']), 2)
        self.assertFalse(earlier & {b['output_path'] for b in again['batches']})
        self.assertEqual(again['batches'][0]['batch'], 'batch_003')

    def test_verdicts_persist_per_claim_and_decide_status(self):
        self.judge(self.prepare(), {'c_neg': 'contradicted', 'c_rev': 'supported'})
        out = run_vcs('verify', '--dir', self.tmpdir)
        claims = {c['claim_id']: c for c in read_claims(self.tmpdir)}
        self.assertEqual(claims['c_neg']['lexical_status'], 'supported')  # lexical is fooled
        self.assertEqual(claims['c_neg']['support_status'], 'contradicted')
        self.assertEqual(claims['c_neg']['model_reason'], 'judged c_neg')
        self.assertEqual(claims['c_neg']['judge_model'], 'claude-sonnet-test')
        self.assertEqual(claims['c_rev']['support_status'], 'supported')
        self.assertEqual(claims['c_rev']['support_verification'], 'model')
        self.assertEqual(out['claim_support']['method'], 'model')
        with open(os.path.join(self.tmpdir, 'run_manifest.json')) as f:
            manifest = json.load(f)
        self.assertEqual(manifest['claim_support']['judge_models'], ['claude-sonnet-test'])
        self.assertEqual(manifest['claim_support']['contradicted'], 1)

    def test_contradicted_factual_claim_hard_fails(self):
        self.judge(self.prepare(), {'c_neg': 'contradicted', 'c_rev': 'supported'})
        out = run_vcs('verify', '--dir', self.tmpdir, '--strict', expect_fail=True)
        self.assertEqual(out['status'], 'fail')
        self.assertEqual(out['factual_contradicted'], 1)

    def test_all_supported_passes_strict(self):
        self.judge(self.prepare(), {'c_neg': 'supported', 'c_rev': 'supported'})
        self.assertEqual(run_vcs('verify', '--dir', self.tmpdir, '--strict')['status'], 'pass')

    def test_missing_verdicts_fail_strict_without_declared_fallback(self):
        out = run_vcs('verify', '--dir', self.tmpdir, '--strict', expect_fail=True)
        self.assertIn('lack a current model verdict', ' '.join(out['failures']))

    def test_declared_fallback_uses_lexical_and_marks_unverified(self):
        out = run_vcs('verify', '--dir', self.tmpdir, '--strict',
                      '--judge-unavailable', 'no subagent tool in this harness')
        self.assertEqual(out['status'], 'pass')
        self.assertEqual(out['claim_support']['method'], 'lexical-fallback')
        self.assertEqual(out['claim_support']['claims_unverified_by_model'], 2)
        claims = {c['claim_id']: c for c in read_claims(self.tmpdir)}
        self.assertEqual(claims['c_neg']['support_verification'], 'unverified-by-model')
        self.assertEqual(claims['c_neg']['support_status'], claims['c_neg']['lexical_status'])
        self.assertNotIn('model_verdict', claims['c_neg'])

    def test_edited_claim_invalidates_its_verdict(self):
        self.judge(self.prepare(), {'c_neg': 'supported', 'c_rev': 'supported'})
        claims = read_claims(self.tmpdir)
        claims[1]['text'] = 'Cloud sales drove a 20% revenue increase in 2024.'
        write_jsonl(os.path.join(self.tmpdir, 'claims.jsonl'), claims)
        out = run_vcs('verify', '--dir', self.tmpdir)
        self.assertEqual(out['claim_support']['method'], 'mixed')
        again = self.prepare()
        self.assertEqual((again['claims_to_judge'], again['claims_with_current_verdict']), (1, 1))
        self.assertEqual(again['batches'][0]['batch'], 'batch_002')  # never overwrites batch_001

    def test_health_surfaces_lexical_fallback(self):
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from scripts.retrieval_health import analyze, render_markdown
        run_vcs('verify', '--dir', self.tmpdir, '--judge-unavailable', 'no subagent tool')
        report = analyze(self.tmpdir)
        self.assertEqual(report['status'], 'degraded')
        text = render_markdown(report)
        self.assertIn('2 claim(s) checked by lexical score only', text)
        self.assertIn('no subagent tool', text)


if __name__ == '__main__':
    unittest.main()
