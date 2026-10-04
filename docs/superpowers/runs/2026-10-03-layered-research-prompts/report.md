status: clean
metrics: pending (upstream-feedback not yet run)

## Implemented

- .1: Added optional reporting manifest and structural package validation. Source: bead `claude-deep-research-skill-ts9.1`; `.superpowers/sdd/claude-deep-research-skill-ts9-plan/progress.md`.
- .2: Rewrote research and delegation around facet coverage, source provenance, bounded workers, and sequential fallback. Source: bead `.2`; `progress.md`.
- .3: Added linked facet dossiers, final synthesis, and durable continuation state. Source: bead `.3`; `progress.md`.
- .4: Aligned quality gates and optional HTML/PDF instructions. Source: bead `.4`; `progress.md`.
- .5: Disposed all 73 prompting findings and added a two-dossier integrated fixture. Source: bead `.5`; `ts9.5-report.md`.
- .6: Tightened package delivery, stop, dossier, synthesis, and link gates. Source: bead `.6`; `progress.md`.
- .7: Required joined workers and passed validation before reporting completion. Source: bead `.7`; `progress.md`.
- .8: Repaired HTML citation placement and bibliography fidelity. Source: bead `.8`; `progress.md`.
- .9: Required justified partial dossiers and exact bibliography URLs. Source: bead `.9`; `progress.md`.
- .10: Blocked completion after critical retrieval error. Source: bead `.10`; `progress.md`.
- .11: Excluded script, style, and template content from visible HTML checks. Source: bead `.11`; `progress.md`.
- .12: Blocked critical-error package delivery and accepted valid freeform gaps and parenthesized URLs. Source: bead `.12`; `progress.md`.
- .13: Required exact rendered bibliography links and excluded hidden HTML content. Source: bead `.13`; `run.md`.

## Remaining

- No open beads or confirmed material defects. Empirical recall gains are unmeasured on real research tasks, and the synthetic fixture does not exercise generated PDF output. Structural checks cannot establish whether prose follows from cited evidence. Source: `run.md`; `.superpowers/sdd/claude-deep-research-skill-ts9-plan/ts9.5-report.md`; `final-review.md`.

## Gotchas & surprises

- Design review sharpened per-claim support, retrieval before drafting, and continuation ownership. Source: `2026-10-03-layered-research-prompts-roast-design-1.md`.
- Workflow was unavailable, so task orchestration and three roast rounds used manual ordinary subagents. Source: `friction.md`.
- Three code roast rounds found delivery and rendering defects; a scoped post-cap audit cleared the final five. Source: `run.md`; `2026-10-03-layered-research-prompts-roast-pr-post-cap-audit.md`.

## Entrypoints

- Read `schemas/run_manifest.schema.json` for the reporting contract. Source: bead `.1`; diff against `main`.
- Read `scripts/validate_report_package.py` for the package delivery gate. Source: beads `.1`, `.6`, `.9`, `.12`; diff against `main`.
- Read `SKILL.md`, then `reference/methodology.md` and `reference/report-assembly.md` for the research flow. Source: beads `.2`, `.3`; diff against `main`.

## Smells

- Task reviews for .1–.5, .9, and .13 needed a fix pass, which merged without another task review. The whole-branch roast and scoped audit later checked the integrated branch. Source: `.superpowers/sdd/claude-deep-research-skill-ts9-plan/progress.md`; `run.md`.
- Task .12's review noted ambiguity when punctuation follows a bare source URL. Source: `.superpowers/sdd/claude-deep-research-skill-ts9-plan/ts9.12-review.md`.
- Evidence and citation validators check structure and links; the lead must still judge factual support. Source: `.superpowers/sdd/claude-deep-research-skill-ts9-plan/ts9.1-report.md`; `2026-10-03-layered-research-prompts-roast-pr-1.md`.
