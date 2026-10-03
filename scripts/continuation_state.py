#!/usr/bin/env python3
"""Persist report handoffs and choose the next action from available capacity."""

import argparse
import json
import os
from pathlib import Path


STATE_NAME = 'continuation_state.json'
FALLBACK_WORDS = 18000


def _read_json(path):
    with path.open(encoding='utf-8') as handle:
        return json.load(handle)


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
    paths = manifest.get('artifact_paths', {})
    reporting = manifest.get('reporting') or {}
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
        'worker_returns': progress.get('worker_returns', []),
    }
    destination = run_dir / STATE_NAME
    temporary = destination.with_name(destination.name + '.tmp')
    temporary.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n',
                         encoding='utf-8')
    os.replace(temporary, destination)
    return state


def load_checkpoint(run_dir):
    """Read a previously persisted boundary without reconstructing from prose."""
    return _read_json(Path(run_dir) / STATE_NAME)


def select_action(state, available_words=None, estimated_next_words=None,
                  subagents_available=False):
    """Prefer capacity signals; use 18K words only when signals are unavailable."""
    if state.get('next_task') is None:
        return {'action': 'complete', 'mechanism': None, 'basis': 'no-next-task'}
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
    args = parser.parse_args()
    if args.command == 'save':
        result = save_checkpoint(args.dir, _read_json(Path(args.progress_json)))
    else:
        result = select_action(load_checkpoint(args.dir), args.available_words,
                               args.estimated_next_words, args.subagents_available)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
