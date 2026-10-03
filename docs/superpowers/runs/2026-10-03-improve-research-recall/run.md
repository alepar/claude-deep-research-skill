# super-auto run — 2026-10-03-improve-research-recall

flags: planOneShot=false skipPlanRoast=false skipCodeRoast=false autonomous=true
phase: design

idea: Implement the proposed recall improvements to the Claude deep-research skill: coverage-led query planning, evidence-driven follow-up search, and coverage-aware stopping. Use ordinary subagents as the user-authorized substitute for the absent Workflow tool.
branch: super-auto/recall-retrieval
base: main
epic: claude-deep-research-skill-2mu
