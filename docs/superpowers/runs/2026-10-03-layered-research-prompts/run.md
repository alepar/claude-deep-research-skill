# super-auto run — 2026-10-03-layered-research-prompts

flags: planOneShot=false skipPlanRoast=false skipCodeRoast=false autonomous=true
phase: report
codeMechanism: ordinary-subagents

idea: Implement everything found in the prompting-guide audit and scoped in the approved layered research dossier design for the Claude deep-research skill.
branch: super-auto/layered-research-prompts
base: main
spec: ../../specs/2026-10-03-layered-research-dossiers-design.md
epic: claude-deep-research-skill-ts9
roast-design: 2026-10-03-layered-research-prompts-roast-design-1.md
roastDesignRound: 1
roastCodeRound: 3
roastCodeExit: converged · no Blocking findings; completing five confirmed quality-gate issues before reporting
roast-code: 2026-10-03-layered-research-prompts-roast-pr-1.md, 2026-10-03-layered-research-prompts-roast-pr-2.md, 2026-10-03-layered-research-prompts-roast-pr-3.md, 2026-10-03-layered-research-prompts-roast-pr-post-cap-audit.md
stepBackCode-round-2: targeted repair — no design change; align independent delivery gates
scope-filter: 4 in-scope · 0 punch-listed
stepBackCode-round-1: targeted repair — no design change; restore delivery and rendering gates
scope-filter: 10 in-scope · 0 punch-listed
graph-pass: no safe edge cuts; schema precedes reporting prompts, and integration follows validation

approvals:
- top-split · auto · claude-deep-research-skill-ts9.1 LEAF, claude-deep-research-skill-ts9.2 LEAF, claude-deep-research-skill-ts9.3 LEAF, claude-deep-research-skill-ts9.4 LEAF, claude-deep-research-skill-ts9.5 LEAF

post-cap-audit: scoped review of round-three fixes clean; all five findings cleared @ 4272d51
friction: 2 events
codeBuckets:
  completed: claude-deep-research-skill-ts9.1, claude-deep-research-skill-ts9.2, claude-deep-research-skill-ts9.3, claude-deep-research-skill-ts9.4, claude-deep-research-skill-ts9.5, claude-deep-research-skill-ts9.6, claude-deep-research-skill-ts9.7, claude-deep-research-skill-ts9.8, claude-deep-research-skill-ts9.9, claude-deep-research-skill-ts9.10, claude-deep-research-skill-ts9.11, claude-deep-research-skill-ts9.12, claude-deep-research-skill-ts9.13
  escalated: none
  pendingRetry: none
  parked: none
  stalled: false
  review: ready
  sweep: 4272d51 — 181 passed, 0 failed, 0 errors, 0 skipped; failing: none; command: python3 -m unittest discover -s tests -p 'test_*.py' -q @ 4272d51
  worktreesKept: none
  processSweep: stopped 0 · survived 0
