# super-auto run — 2026-10-03-improve-research-recall

flags: planOneShot=false skipPlanRoast=false skipCodeRoast=false autonomous=true
phase: report

idea: Implement the proposed recall improvements to the Claude deep-research skill: coverage-led query planning, evidence-driven follow-up search, and coverage-aware stopping. Use ordinary subagents as the user-authorized substitute for the absent Workflow tool.
branch: super-auto/recall-retrieval
base: main
epic: claude-deep-research-skill-2mu
spec: spec.md
roast-design: roast-design.md
roast-code: roast-code.md
roastDesignRound: 3
roastCodeRound: 2
roastCodeExit: converged
codeBuckets:
  completed: claude-deep-research-skill-2mu.1, claude-deep-research-skill-2mu.2, claude-deep-research-skill-2mu.3
  escalated: none
  pendingRetry: none
  parked: none
  stalled: false
  review: ready
  sweep: SWEEP DEFERRED (caller-owned)
  worktreesKept: none
  processSweep: stopped 0 · survived 0
friction: 1 events
approvals:
- top-split · auto · claude-deep-research-skill-2mu.1 LEAF, claude-deep-research-skill-2mu.2 LEAF, claude-deep-research-skill-2mu.3 LEAF
- coverage-round-1 · auto · requirements: 3 · mapped: 3 · unmapped: 0 (coverage ledger, query loop, stop rule)
