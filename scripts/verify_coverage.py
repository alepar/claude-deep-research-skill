#!/usr/bin/env python3
"""Check saved retrieval coverage and stop decisions for structural consistency.

This cannot judge whether evidence is relevant, independent, or persuasive.
"""

import argparse
import hashlib
import json
import os
import sys


FAMILIES = {'literal', 'synonym', 'disciplinary', 'entity', 'source-specific',
            'counterevidence', 'citation-neighborhood', 'vocabulary-probe', 'delta'}
STATUSES = {'unsearched', 'searched', 'supported', 'contested', 'unresolved'}
COUNTER = {'unchecked', 'searched-none-found', 'found', 'not-applicable'}
CHANGE_KINDS = {'status', 'counterevidence', 'contested_position', 'priority',
                'facet_added', 'scope_change'}
STOP_REASONS = {'coverage-saturated', 'budget-exhausted', 'critical-error'}


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    with open(path, encoding='utf-8') as f:
        for number, line in enumerate(f, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f'{os.path.basename(path)} line {number} is not an object')
                rows.append(value)
    return rows


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def unique_ids(rows, key, label, errors):
    result = {}
    for row in rows:
        identity = row.get(key)
        if not nonempty(identity):
            errors.append(f'{label} missing {key}')
        elif identity in result:
            errors.append(f'duplicate {key}: {identity}')
        else:
            result[identity] = row
    return result


def check_references(values, known, label, errors):
    if not isinstance(values, list):
        errors.append(f'{label} must be an array')
        return
    if len(values) != len(set(map(str, values))):
        errors.append(f'{label} contains duplicate IDs')
    for value in values:
        if value not in known:
            errors.append(f'{label} references unknown {"evidence" if "evidence" in label else "source" if "source" in label else "query" if "query" in label else "facet"}: {value}')


def facet_ready(facet, evidence):
    if not facet.get('active') or facet.get('priority') != 'high':
        return True
    if facet.get('status') not in {'supported', 'contested'}:
        return False
    if not facet.get('evidence_ids') or facet.get('counterevidence') == 'unchecked':
        return False
    if facet.get('counterevidence') == 'not-applicable' and not nonempty(facet.get('gap_note')):
        return False
    if facet.get('status') == 'contested':
        positions = facet.get('contested_positions', [])
        if len(positions) < 2 or not nonempty(facet.get('gap_note')):
            return False
        if any(not p.get('evidence_ids') for p in positions):
            return False
        if len({tuple(p.get('evidence_ids', [])) for p in positions}) < 2:
            return False
        if any(eid not in evidence for p in positions for eid in p.get('evidence_ids', [])):
            return False
    return True


def verify(directory, require_stop=False):
    errors = []
    try:
        manifest = load_json(os.path.join(directory, 'run_manifest.json'))
    except (OSError, ValueError) as exc:
        return {'status': 'invalid', 'errors': [f'run_manifest.json: {exc}']}
    paths = manifest.get('artifact_paths', {})
    needed = {'coverage': 'coverage.json', 'queries': 'queries.jsonl'}
    absent = [name for name, default in needed.items()
              if not os.path.isfile(os.path.join(directory, paths.get(name, default)))]
    if absent:
        return {'status': 'missing', 'missing': absent,
                'errors': ['coverage unavailable: missing ' + ', '.join(absent)]}
    try:
        coverage = load_json(os.path.join(directory, paths['coverage']))
        queries = load_jsonl(os.path.join(directory, paths['queries']))
        sources = load_jsonl(os.path.join(directory, paths.get('sources', 'sources.jsonl')))
        evidence_rows = load_jsonl(os.path.join(directory, paths.get('evidence', 'evidence.jsonl')))
    except (OSError, ValueError, KeyError) as exc:
        return {'status': 'invalid', 'errors': [f'artifact read: {exc}']}
    if not isinstance(coverage, dict) or coverage.get('schema_version') != 1:
        return {'status': 'invalid', 'errors': ['coverage schema_version must be 1']}
    for field in ('question', 'initial_facets', 'facets', 'completed_rounds', 'stop'):
        if field not in coverage:
            errors.append(f'coverage missing {field}')
    if coverage.get('question') != manifest.get('query'):
        errors.append('coverage question differs from manifest query')

    source_by_id = unique_ids(sources, 'source_id', 'source', errors)
    for sid, source in source_by_id.items():
        locator = source.get('canonical_locator')
        if not nonempty(locator) or hashlib.sha256(locator.encode()).hexdigest()[:16] != sid:
            errors.append(f'source {sid} has invalid canonical source ID')
    evidence = unique_ids(evidence_rows, 'evidence_id', 'evidence', errors)
    for eid, row in evidence.items():
        if row.get('source_id') not in source_by_id:
            errors.append(f'evidence {eid} references unknown source')
    query_by_id = unique_ids(queries, 'query_id', 'query', errors)
    facets_list = coverage.get('facets', [])
    initial_list = coverage.get('initial_facets', [])
    rounds = coverage.get('completed_rounds', [])
    if not all(isinstance(x, list) for x in (facets_list, initial_list, rounds)):
        return {'status': 'invalid', 'errors': errors + ['facet and round collections must be arrays']}
    for label, rows in (('facet', facets_list), ('initial facet', initial_list),
                        ('completed round', rounds)):
        if any(not isinstance(row, dict) for row in rows):
            return {'status': 'invalid', 'errors': errors + [f'{label} rows must be objects']}
    facets = unique_ids(facets_list, 'id', 'facet', errors)
    initials = unique_ids(initial_list, 'id', 'initial facet', errors)
    for initial_id, initial in initials.items():
        if not nonempty(initial.get('question')) or initial.get('priority') not in {'high', 'supporting'}:
            errors.append(f'initial facet {initial_id} invalid question or priority')
        current = facets.get(initial_id)
        if current is None:
            errors.append(f'initial facet {initial_id} missing from facets')
            continue
        if initial.get('question') != current.get('question'):
            errors.append(f'initial facet {initial_id} question changed')
        prior = initial.get('priority')
        if prior not in {'high', 'supporting'}:
            errors.append(f'initial facet {initial_id} invalid priority')
        changed = not current.get('active') or prior != current.get('priority')
        if changed:
            change = current.get('scope_change')
            if not isinstance(change, dict) or change.get('previous_priority') != prior or \
                    change.get('new_priority') != current.get('priority') or not nonempty(change.get('reason')):
                errors.append(f'initial facet {initial_id} needs scope_change rationale')
            elif not change.get('supporting_evidence_ids') and not nonempty(change.get('user_scope_reason')):
                errors.append(f'initial facet {initial_id} scope_change needs evidence or user-scope reason')
            elif change.get('supporting_evidence_ids'):
                check_references(change['supporting_evidence_ids'], evidence,
                                 f'initial facet {initial_id} scope_change evidence', errors)
    for fid, facet in facets.items():
        for field in ('source_types', 'status', 'active', 'query_ids', 'evidence_ids',
                      'contested_positions', 'counterevidence', 'gap_note', 'scope_change'):
            if field not in facet:
                errors.append(f'facet {fid} missing {field}')
        if not isinstance(facet.get('source_types'), list) or any(
                not isinstance(item, str) for item in facet.get('source_types', [])):
            errors.append(f'facet {fid} source_types must be an array of strings')
        if not isinstance(facet.get('gap_note'), str):
            errors.append(f'facet {fid} gap_note must be a string')
        if facet.get('scope_change') is not None and not isinstance(facet.get('scope_change'), dict):
            errors.append(f'facet {fid} scope_change must be an object or null')
        if not nonempty(facet.get('question')) or facet.get('priority') not in {'high', 'supporting'}:
            errors.append(f'facet {fid} invalid question or priority')
        if facet.get('status') not in STATUSES or facet.get('counterevidence') not in COUNTER:
            errors.append(f'facet {fid} invalid status or counterevidence')
        if not isinstance(facet.get('active'), bool):
            errors.append(f'facet {fid} active must be boolean')
        if facet.get('status') == 'supported' and not facet.get('evidence_ids'):
            errors.append(f'facet {fid} supported without direct evidence')
        if facet.get('counterevidence') == 'not-applicable' and not nonempty(facet.get('gap_note')):
            errors.append(f'facet {fid} not-applicable counterevidence needs gap_note')
        check_references(facet.get('query_ids'), query_by_id, f'facet {fid} query_ids', errors)
        check_references(facet.get('evidence_ids'), evidence, f'facet {fid} evidence_ids', errors)
        positions = facet.get('contested_positions', [])
        if facet.get('status') == 'contested':
            if not isinstance(positions, list) or len(positions) < 2 or not nonempty(facet.get('gap_note')):
                errors.append(f'facet {fid} contested needs two positions and conflict note')
            else:
                for position in positions:
                    if not nonempty(position.get('position')) or not position.get('evidence_ids'):
                        errors.append(f'facet {fid} contested position lacks evidence')
                    check_references(position.get('evidence_ids'), evidence,
                                     f'facet {fid} contested evidence_ids', errors)
                if len({tuple(p.get('evidence_ids', [])) for p in positions}) < 2:
                    errors.append(f'facet {fid} contested positions reuse the same evidence')
        elif positions:
            errors.append(f'facet {fid} contested_positions requires contested status')

    by_round = {}
    seen_new = set()
    final_changes = {}
    for qid, query in query_by_id.items():
        for field in ('round', 'facet_ids', 'gap', 'family', 'query', 'provider',
                      'expected_evidence', 'result_source_ids', 'new_relevant_source_ids',
                      'coverage_changed', 'notes'):
            if field not in query:
                errors.append(f'query {qid} missing {field}')
        if not isinstance(query.get('notes'), str):
            errors.append(f'query {qid} notes must be a string')
        round_number = query.get('round')
        if type(round_number) is not int or round_number < 1:
            errors.append(f'query {qid} invalid round')
            continue
        by_round.setdefault(round_number, []).append(query)
        if query.get('family') not in FAMILIES:
            errors.append(f'query {qid} invalid family')
        for field in ('gap', 'query', 'provider', 'expected_evidence'):
            if not nonempty(query.get(field)):
                errors.append(f'query {qid} missing {field}')
        check_references(query.get('facet_ids'), facets, f'query {qid} facet_ids', errors)
        check_references(query.get('result_source_ids'), source_by_id,
                         f'query {qid} result_source_ids', errors)
        check_references(query.get('new_relevant_source_ids'), source_by_id,
                         f'query {qid} new_relevant_source_ids', errors)
        if not set(query.get('new_relevant_source_ids') or []).issubset(
                set(query.get('result_source_ids') or [])):
            errors.append(f'query {qid} new source not in results')
        for fid in query.get('facet_ids') or []:
            if fid in facets and qid not in facets[fid].get('query_ids', []):
                errors.append(f'query {qid} absent from facet {fid} query_ids')
    if set(by_round) != set(range(1, len(rounds) + 1)):
        errors.append('completed_rounds must cover every consecutive query round')
    for index, round_row in enumerate(rounds, 1):
        for field in ('round', 'query_ids', 'families', 'target_high_priority_facet_ids',
                      'new_relevant_source_ids', 'material_changes', 'coverage_ready_after'):
            if field not in round_row:
                errors.append(f'round {index} missing {field}')
        if round_row.get('round') != index:
            errors.append(f'completed_rounds nonconsecutive round {index}')
        logged = by_round.get(index, [])
        qids = [q['query_id'] for q in logged]
        if set(round_row.get('query_ids', [])) != set(qids) or len(round_row.get('query_ids', [])) != len(qids):
            errors.append(f'round {index} query_ids mismatch')
        if set(round_row.get('families', [])) != {q.get('family') for q in logged}:
            errors.append(f'round {index} families mismatch')
        expected_new = {sid for q in logged for sid in q.get('new_relevant_source_ids', [])}
        actual_new = set(round_row.get('new_relevant_source_ids', []))
        if actual_new != expected_new or len(round_row.get('new_relevant_source_ids', [])) != len(actual_new):
            errors.append(f'round {index} new_relevant_source_ids mismatch')
        for sid in expected_new:
            if sid in seen_new:
                errors.append(f'round {index} repeats new relevant source {sid}')
            seen_new.add(sid)
        targets = set(round_row.get('target_high_priority_facet_ids', []))
        if not targets.issubset({fid for fid, facet in facets.items()
                                if facet.get('active') and facet.get('priority') == 'high'}):
            errors.append(f'round {index} targets invalid high-priority facet')
        if not targets.issubset({fid for q in logged for fid in q.get('facet_ids', [])}):
            errors.append(f'round {index} targets absent from queries')
        changes = round_row.get('material_changes', [])
        if not isinstance(changes, list):
            errors.append(f'round {index} material_changes must be array')
            continue
        for change in changes:
            if change.get('kind') not in CHANGE_KINDS or change.get('facet_id') not in facets or \
                    'before' not in change or 'after' not in change:
                errors.append(f'round {index} invalid material_changes entry')
            else:
                final_changes[(change['facet_id'], change['kind'])] = change['after']
        if any(q.get('coverage_changed') is not False and
               q.get('coverage_changed') is not True for q in logged):
            errors.append(f'round {index} query coverage_changed must be boolean')
        if any(q.get('coverage_changed') for q in logged) != bool(changes):
            errors.append(f'round {index} coverage_changed conflicts with material_changes')
        if not isinstance(round_row.get('coverage_ready_after'), bool):
            errors.append(f'round {index} coverage_ready_after must be boolean')

    for (fid, kind), after in final_changes.items():
        field = {'status': 'status', 'counterevidence': 'counterevidence',
                 'priority': 'priority', 'scope_change': 'scope_change'}.get(kind)
        if field and facets[fid].get(field) != after:
            errors.append(f'material_changes final {kind} for {fid} disagrees with current facet')

    checked_counter = {(change.get('facet_id'), change.get('after')) for round_row in rounds
                       for change in round_row.get('material_changes', [])
                       if isinstance(change, dict) and change.get('kind') == 'counterevidence'}
    for fid, facet in facets.items():
        state = facet.get('counterevidence')
        if not facet.get('active') or facet.get('priority') != 'high' or \
                state not in {'found', 'searched-none-found'}:
            continue
        if (fid, state) not in checked_counter:
            errors.append(f'facet {fid} checked counterevidence lacks material transition')
            continue
        if not any(any(change.get('facet_id') == fid and
                       change.get('kind') == 'counterevidence' and change.get('after') == state
                       for change in round_row.get('material_changes', [])) and
                   any(fid in q.get('facet_ids', []) and
                       q.get('coverage_changed') is True
                       for q in by_round.get(round_row.get('round'), []))
                   for round_row in rounds):
            errors.append(f'facet {fid} checked counterevidence lacks supporting query provenance')

    stop = coverage.get('stop')
    if require_stop and stop is None:
        errors.append('retrieval_stop required for delivery')
    if stop != manifest.get('retrieval_stop'):
        errors.append('coverage stop and manifest retrieval_stop differ')
    if stop is not None:
        if not isinstance(stop, dict) or stop.get('reason') not in STOP_REASONS:
            errors.append('invalid retrieval_stop reason')
        else:
            if not nonempty(stop.get('at')) or not nonempty(stop.get('basis')):
                errors.append('retrieval_stop needs at and basis')
            if stop.get('round') != len(rounds):
                errors.append('retrieval_stop round must equal last completed round')
            high_open = [fid for fid, f in facets.items() if f.get('active') and
                         f.get('priority') == 'high' and not facet_ready(f, evidence)]
            unresolved = stop.get('unresolved_high_priority_facet_ids')
            if not isinstance(unresolved, list) or set(unresolved) != set(high_open):
                errors.append('retrieval_stop unresolved_high_priority_facet_ids mismatch')
            gaps = stop.get('remaining_gaps')
            if not isinstance(gaps, list) or (high_open and not all(nonempty(g) for g in gaps)):
                errors.append('retrieval_stop remaining_gaps invalid')
            if stop['reason'] == 'budget-exhausted' and high_open and not gaps:
                errors.append('budget-exhausted requires remaining_gaps')
            if stop['reason'] == 'coverage-saturated':
                if not initials:
                    errors.append('coverage-saturated requires nonempty initial_facets snapshot')
                if high_open:
                    errors.append('coverage-saturated with unready high-priority facets')
                if len(rounds) < 3 or not rounds[-3].get('coverage_ready_after'):
                    errors.append('coverage-saturated needs two rounds after readiness')
                else:
                    residual = rounds[-2:]
                    if any(not r.get('coverage_ready_after') or r.get('material_changes') or
                           r.get('new_relevant_source_ids') for r in residual):
                        errors.append('coverage-saturated residual rounds must be low-yield')
                    if not all(r.get('target_high_priority_facet_ids') for r in residual):
                        errors.append('coverage-saturated residual rounds must target high-priority facets')
                    families = [set(r.get('families', [])) for r in residual]
                    if not families[0] or not families[1] or families[0] & families[1]:
                        errors.append('coverage-saturated residual rounds need distinct families')
    return {'status': 'invalid' if errors else 'ok', 'errors': errors,
            'rounds_checked': len(rounds)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dir', required=True, help='Research run directory')
    parser.add_argument('--require-stop', action='store_true',
                        help='Reject an unfinished run without a persisted retrieval stop')
    args = parser.parse_args()
    try:
        result = verify(args.dir, require_stop=args.require_stop)
    except (TypeError, AttributeError, KeyError, IndexError) as exc:
        result = {'status': 'invalid', 'errors': [f'malformed coverage structure: {exc}']}
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'ok' else 1


if __name__ == '__main__':
    sys.exit(main())
