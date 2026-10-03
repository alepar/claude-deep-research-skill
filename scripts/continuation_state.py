#!/usr/bin/env python3
"""Persist report handoffs and choose the next action from available capacity."""

import argparse
import json
import os
from pathlib import Path


STATE_NAME = 'continuation_state.json'
FALLBACK_WORDS = 18000
REQUIRED_VALIDATION_CHECKS = (
    'coverage_stop', 'claim_support', 'report_surface', 'dossier_surface',
    'citation_identity', 'package', 'semantic_review',
)


def _read_json(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


def _write_state(run_dir, state):
    destination = Path(run_dir) / STATE_NAME
    temporary = destination.with_name(destination.name + '.tmp')
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    os.replace(temporary, destination)


def save_checkpoint(run_dir, progress):
    """Snapshot manifest paths and progress at a section or dossier boundary."""
    run_dir = Path(run_dir)
    manifest = _read_json(run_dir / 'run_manifest.json')
    required = ('completed_sections', 'open_gaps', 'next_task', 'words_generated')
    missing = [name for name in required if name not in progress]
    if missing:
        raise ValueError('progress missing: ' + ', '.join(missing))
    if not isinstance(progress['completed_sections'], list) or \
            not isinstance(progress['open_gaps'], list) or \
            not isinstance(progress['next_task'], (dict, type(None))) or \
            not isinstance(progress['words_generated'], int) or \
            progress['words_generated'] < 0:
        raise ValueError('progress has invalid section, gap, task, or word fields')
    if not isinstance(progress.get('required_worker_ids', []), list) or \
            not isinstance(progress.get('worker_returns', []), list) or \
            not isinstance(progress.get('final_validation', {}), dict):
        raise ValueError('progress has invalid worker or validation fields')
    paths = manifest.get('artifact_paths', {})
    reporting = manifest.get('reporting') or {}
    previous_path = run_dir / STATE_NAME
    previous = load_checkpoint(run_dir) if previous_path.exists() else {}
    artifacts = {'run_manifest': 'run_manifest.json'}
    for name, default in (('coverage', 'coverage.json'), ('queries', 'queries.jsonl'),
                          ('sources', 'sources.jsonl'), ('evidence', 'evidence.jsonl'),
                          ('claims', 'claims.jsonl')):
        artifacts[name] = paths.get(name, default)
    artifacts['final_report'] = reporting.get('final_report_path',
                                             paths.get('report', 'report.md'))
    state = {
        'version': 1,
        'research_question': manifest.get('query', ''),
        'mode': manifest.get('mode'),
        'artifacts': artifacts,
        'dossiers': reporting.get('dossiers', []),
        'completed_sections': progress['completed_sections'],
        'open_gaps': progress['open_gaps'],
        'next_task': progress['next_task'],
        'words_generated': progress['words_generated'],
        'worker_returns': progress.get('worker_returns', previous.get('worker_returns', [])),
        'required_worker_ids': progress.get(
            'required_worker_ids', previous.get('required_worker_ids', [])),
        'final_validation': progress.get('final_validation', {}),
        'delivery_status': progress.get('delivery_status', 'complete'),
        'retrieval_stop_reason': progress.get(
            'retrieval_stop_reason', (manifest.get('retrieval_stop') or {}).get('reason')),
        'requested_formats': reporting.get('requested_formats', []),
    }
    state['completed_stretches'] = previous.get('completed_stretches', [])
    _write_state(run_dir, state)
    return state


def load_checkpoint(run_dir):
    """Read a previously persisted boundary without reconstructing from prose."""
    return _read_json(Path(run_dir) / STATE_NAME)


def begin_new_stretch(run_dir):
    """Persist a fresh writer counter while retaining the prior stretch."""
    state = load_checkpoint(run_dir)
    if select_action(state)['action'] in ('complete', 'partial'):
        raise ValueError('cannot resume a completed report')
    if state.get('words_generated', 0) <= 0:
        raise ValueError('current writer stretch has no words to preserve')
    state.setdefault('completed_stretches', []).append({
        'words_generated': state['words_generated'],
        'next_task': state['next_task'],
    })
    state['words_generated'] = 0
    _write_state(run_dir, state)
    return state


def select_action(state, available_words=None, estimated_next_words=None,
                  subagents_available=False):
    """Prefer capacity signals; use 18K words only when signals are unavailable."""
    if state.get('next_task') is None:
        blockers = []
        returns = state.get('worker_returns', [])
        by_id = {item.get('worker_id'): item for item in returns
                 if isinstance(item, dict) and item.get('worker_id')}
        for worker_id in state.get('required_worker_ids', []):
            result = by_id.get(worker_id)
            if not result or result.get('status') not in ('complete', 'success') or \
                    result.get('joined') is not True:
                blockers.append('required worker not successfully joined: ' + str(worker_id))
        for item in returns:
            if isinstance(item, dict) and item.get('worker_id') not in \
                    state.get('required_worker_ids', []) and \
                    (item.get('status') not in ('complete', 'success') or
                     item.get('joined') is not True):
                blockers.append('worker return not joined: ' + str(item.get('worker_id')))
        for dossier in state.get('dossiers', []):
            if not isinstance(dossier, dict) or dossier.get('status') == 'draft':
                blockers.append('draft dossier: ' + str(dossier.get('id') if
                                                       isinstance(dossier, dict) else dossier))
        checks = state.get('final_validation') or {}
        required = list(REQUIRED_VALIDATION_CHECKS)
        if not state.get('dossiers'):
            required.remove('dossier_surface')
        formats = state.get('requested_formats') or []
        required.extend(name for name in ('html', 'pdf') if name in formats)
        failed = [name for name in required if checks.get(name) == 'failed']
        blockers.extend('failed final validation: ' + name for name in failed)
        gaps = state.get('open_gaps') or []
        partial = (state.get('delivery_status') == 'partial' and
                   state.get('retrieval_stop_reason') == 'budget-exhausted')
        if gaps and not partial:
            blockers.append('open material gaps require a qualified budget-limited partial')
        if blockers:
            return {'action': 'blocked', 'mechanism': None,
                    'basis': 'completion-gates', 'blockers': blockers}
        unrun = [name for name in required if checks.get(name) != 'passed']
        if unrun:
            return {'action': 'validate', 'mechanism': None,
                    'basis': 'completion-gates', 'checks': unrun}
        return {'action': 'partial' if partial else 'complete',
                'mechanism': None, 'basis': 'completion-gates'}
    if available_words is not None:
        if estimated_next_words is None:
            raise ValueError('estimated_next_words is required with available_words')
        if available_words < 0 or estimated_next_words < 0:
            raise ValueError('capacity and estimate must be nonnegative')
        handoff = available_words < estimated_next_words
        basis = 'capacity-signal'
    else:
        handoff = state.get('words_generated', 0) >= FALLBACK_WORDS
        basis = 'word-fallback'
    return {
        'action': 'handoff' if handoff else 'continue',
        'mechanism': ('subagent' if subagents_available else 'sequential-resume')
        if handoff else None,
        'basis': basis,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    save = commands.add_parser('save', help='Persist progress with canonical artifact paths')
    save.add_argument('--dir', required=True)
    save.add_argument('--progress-json', required=True)
    decide = commands.add_parser('decide', help='Choose continue or handoff')
    decide.add_argument('--dir', required=True)
    decide.add_argument('--available-words', type=int)
    decide.add_argument('--estimated-next-words', type=int)
    decide.add_argument('--subagents-available', action='store_true')
    resume = commands.add_parser('resume', help='Begin a new writer stretch from checkpoint')
    resume.add_argument('--dir', required=True)
    args = parser.parse_args()
    if args.command == 'save':
        result = save_checkpoint(args.dir, _read_json(Path(args.progress_json)))
    elif args.command == 'resume':
        result = begin_new_stretch(args.dir)
    else:
        result = select_action(load_checkpoint(args.dir), args.available_words,
                               args.estimated_next_words, args.subagents_available)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
