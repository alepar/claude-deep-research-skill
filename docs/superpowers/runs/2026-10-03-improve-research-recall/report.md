status: clean
metrics: none (Workflow fallback feedback delivered through Herdr; no duplicate issue filed)

# Recall retrieval run report

## Implemented

- Facet-led scope, distinct query families, gap-led follow-ups, and explicit coverage or budget stops across the skill instructions. Source: closed bead `claude-deep-research-skill-2mu.2`; `main...super-auto/recall-retrieval` diff.
- Persisted `coverage.json` and `queries.jsonl`, with a structural validator for source/query references, round summaries, scope, counterevidence provenance, and stop decisions. Source: closed bead `claude-deep-research-skill-2mu.1`; branch diff.
- Aligned the engine instruction scaffold, quality gates, report assembly, and README; added tests for the scaffold and validator. Source: closed bead `claude-deep-research-skill-2mu.3`; branch diff.

## Remaining

- No task in the Beads epic remains open. Empirical recall improvement is unmeasured; a pooled-source evaluation is described in `spec.md`. Source: Beads epic `claude-deep-research-skill-2mu`; `spec.md` Post-Implementation Notes.
- Merged locally into `main` after the owner's integration decision. Source: `run.md` branch/base fields and the `main` history.

## Gotchas & surprises

- Workflow was unavailable in this harness. The user authorized ordinary subagents as the substitute; this reduced the workflow metrics available for this run. The fallback need was passed to the Superpowers Herdr agent. Source: `friction.md`; `run.md` idea.
- Review exposed five validator gaps and one overly narrow fix. Each was addressed with a regression case before the final sweep. Source: `roast-code.md`.

## Entrypoints

1. `SKILL.md` and `reference/methodology.md` for the research behavior. Source: branch diff.
2. `scripts/citation_manager.py`, `schemas/coverage.schema.json`, and `schemas/query.schema.json` for the saved artifacts. Source: branch diff.
3. `scripts/verify_coverage.py` and `tests/test_verify_coverage.py` for the structural stop checks. Source: branch diff.

## Smells

- The validator checks consistency of saved records; it cannot judge relevance, independence, or whether the recorded history is true. Source: `spec.md` Post-Implementation Notes; `roast-code.md`.

## Verification

- `python3 -m unittest discover -s tests -p 'test_*.py' -q`: 68 passed, 0 failed, 0 errors, 0 skipped. `git diff --check` was clean. Source: `run.md` codeBuckets.sweep.
