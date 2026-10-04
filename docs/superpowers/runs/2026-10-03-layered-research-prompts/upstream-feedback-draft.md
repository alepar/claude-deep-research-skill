# 2026-10-03-layered-research-prompts: Consider bounded parallel task work in the ordinary-subagent fallback

Plugin: 6.4.2-alepar4.15. Run: 13 task beads, three PR roast rounds, 2026-10-03.

## Defects

none

## Run metrics

### Judge panel

- Design iteration 1: no seat-agreement line recorded.
- PR iteration 1: same-family, manual fan-out; no seat-agreement line recorded.
- PR iteration 2: same-family, manual fan-out; no seat-agreement line recorded.
- PR iteration 3: same-family, manual fan-out; 5 unanimous panels; reproduce 5/0/0, refute 5/0/0, ground 5/0/0.
- Post-cap audit: partial subagent coverage, manual fan-out; no panels.

### Fix loop

- 13 task beads closed, none escalated, pending retry, or parked. Reviews for .1–.5, .9, and .13 needed a fix pass. All 13 merges passed their build check.

### Merge-back

- Ledger: 13 `Merge:` success lines, 0 merge failures, 0 rebase conflicts, 0 check failures; ledger-check ok. First-parent branch history: 13 merge commits. No ledger shortfall.

### Coverage

- Initial implementation: 5 tasks; code roast rounds: 10, 4, and 5 confirmed findings; all confirmed findings were addressed by task beads or cleared in the scoped audit. Scope filter: 10 then 4 in-scope, 0 punch-listed in rounds 1 and 2.

### Bead graph

| id | type | title | what |
| --- | --- | --- | --- |
| ts9 | epic | Layered research and prompting audit | Own approved design and 73 findings. |
| ts9.1 | task | Reporting manifest | Define schema and package validator. |
| ts9.2 | task | Research instructions | Rewrite research and delegation guidance. |
| ts9.3 | task | Layered reporting | Add dossiers and continuation. |
| ts9.4 | task | Quality gates | Align validation and rendering. |
| ts9.5 | task | Audit disposition | Map findings and integrated fixture. |
| ts9.6 | task | Delivery gates | Repair package delivery checks. |
| ts9.7 | task | Continuation completion | Require joins and validation. |
| ts9.8 | task | Rendered evidence | Repair HTML citation and bibliography checks. |
| ts9.9 | task | Partial dossiers | Require justified gaps and exact URLs. |
| ts9.10 | task | Critical stop | Block completion after retrieval error. |
| ts9.11 | task | Hidden HTML | Ignore nonrendered elements. |
| ts9.12 | task | Package follow-up | Close delivery and valid-input gaps. |
| ts9.13 | task | HTML follow-up | Close bibliography and hidden-content gaps. |

| dependent | blocker | reason |
| --- | --- | --- |
| ts9.3 | ts9.1 | Consumes the manifest schema. |
| ts9.4 | ts9.3 | Consumes the dossier/report structure. |
| ts9.5 | ts9.2 | Integrates research instructions. |
| ts9.5 | ts9.4 | Integrates quality gates. |

## Design questions

### Should ordinary-subagent mode dispatch independent ready tasks concurrently?

- **Evidence:** The fallback ran 13 tasks with peak in-flight work of 1; the initial detector reported a ready queue peak of 2. The graph shows .1 and .2 were independent, while merge-back remained safe at one in flight. The run had no merge or build-check failures. Two friction events record manual coordination without Workflow.
- **Premise to verify:** Ordinary subagents and worktrees can isolate independent writes while preserving task review and serialized integration. This single run does not quantify speedup or prove an ideal concurrency limit.
- **Suggested fix shape:** Detect dependency-ready tasks with disjoint write ownership and dispatch a bounded set; keep merge-back serial and record why other ready tasks remain queued. A serial default is simpler and may be preferable for low-slot harnesses; bounded parallelism may reduce critical-path time when ready tasks are independent. If upstream decides otherwise, please state the position explicitly so downstream can reconcile against words rather than silence.

## Doc gaps

none — the installed version already documents ordinary-subagent fallback in `super-code/coordinator-subagents.md` and `super-roast/SKILL.md`.

## Already fixed — do not re-litigate

- The lack of a Workflow-independent path is already addressed in plugin 6.4.2-alepar4.15: this run completed with the supported ordinary-subagent fallback. The proposed question concerns bounded parallel work within that fallback.

## Not established

- No measured speedup, contention rate, or safe concurrency cap from this one run.
- Ledger append is not transactional; its metrics are a lower bound, though the ledger check and 13-to-13 merge cross-check passed here.

## Verification bar

- Replay a bead graph with at least two independent ready tasks and one dependent task under a harness with no Workflow tool. Verify bounded concurrent implementation, one merge at a time, task review, dependency rechecks, clean ledger, and final suite result. Compare elapsed time and conflicts against serial fallback.

---
If a premise above is wrong, stop and say so rather than improvising a larger change.
