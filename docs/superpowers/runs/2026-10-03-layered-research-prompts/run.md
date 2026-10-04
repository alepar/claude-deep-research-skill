# super-auto run — 2026-10-03-layered-research-prompts

flags: planOneShot=false skipPlanRoast=false skipCodeRoast=false autonomous=true
phase: fix-loop
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
roast-code: 2026-10-03-layered-research-prompts-roast-pr-1.md, 2026-10-03-layered-research-prompts-roast-pr-2.md, 2026-10-03-layered-research-prompts-roast-pr-3.md
stepBackCode-round-2: targeted repair — no design change; align independent delivery gates
scope-filter: 4 in-scope · 0 punch-listed
stepBackCode-round-1: targeted repair — no design change; restore delivery and rendering gates
scope-filter: 10 in-scope · 0 punch-listed
graph-pass: no safe edge cuts; schema precedes reporting prompts, and integration follows validation

approvals:
- top-split · auto · claude-deep-research-skill-ts9.1 LEAF, claude-deep-research-skill-ts9.2 LEAF, claude-deep-research-skill-ts9.3 LEAF, claude-deep-research-skill-ts9.4 LEAF, claude-deep-research-skill-ts9.5 LEAF
