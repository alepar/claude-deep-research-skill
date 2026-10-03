## Goal

Improve the skill's chance of finding decision-relevant sources by making each research run track question coverage, choose follow-up searches from evidence gaps, and stop with an explicit coverage decision. Preserve the existing Claude-driven search workflow and citation/evidence artifacts.

## Context and scope

The current methodology asks for 5–10 search angles and permits retrieval to end at a source-count or time threshold. The engine is an instruction and state scaffold; it does not search. A source count is useful as a depth indicator, but it cannot show whether the user's essential subquestions were investigated. The earlier research report recommends a coverage ledger, distinct query families, an evidence-driven follow-up loop, and a coverage-aware stop decision.

This change applies to the instructions in `SKILL.md`, `reference/methodology.md`, `reference/quality-gates.md`, and the matching phase text in `scripts/research_engine.py`. It adds a small artifact/validator script if needed so a saved run can be inspected. It does not add a search backend, vector index, embedding model, or an automated agent that decides relevance. The report's proposed citation chasing is included as a conditional scholarly query lane. Rank fusion and genuine HyDE are deferred: the present search providers do not expose a common, stable ranked corpus or vector index. A guarded hypothetical-answer vocabulary probe is included, but its output is query vocabulary only.

## Design choices

1. **Prompt-only ledger vs. persisted ledger.** Choose a persisted `coverage.json` and append-only `queries.jsonl`, because continuation agents and reviewers need to inspect decisions after context is lost. The model updates coverage after each retrieval batch; a validator checks shape and stop consistency. Avoid a new runtime orchestrator.
2. **Broad query generation vs. targeted lanes.** Choose named query families with a facet/gap and expected evidence for every query. Keep the user's literal wording in the first batch. Use bounded expansion only when literal searches appear to miss vocabulary.
3. **Source-count stop vs. coverage stop.** Choose coverage plus observed marginal yield, with a hard time/tool budget escape. Keep existing source count and credibility as diagnostics, not automatic clearance. A budget stop must name unresolved gaps.

## Artifacts and schema

`citation_manager.py init-run` should create `coverage.json` and `queries.jsonl` alongside existing `sources.jsonl`, `evidence.jsonl`, `claims.jsonl`, and `run_manifest.json`, and name them in `artifact_paths`. Existing run directories without these files remain readable; the new validator should report `missing` instead of silently declaring coverage sufficient. `run_manifest.json` may gain a `retrieval_stop` object after the run; do not change existing version 3 source/evidence/claim identities.

`coverage.json` is the latest state, written atomically. Minimum shape:

```json
{
  "schema_version": 1,
  "question": "original research question",
  "initial_facets": [
    { "id": "F1", "question": "answerable subquestion", "priority": "high" }
  ],
  "facets": [
    {
      "id": "F1",
      "question": "answerable subquestion",
      "priority": "high",
      "source_types": ["primary documentation"],
      "status": "unsearched",
      "active": true,
      "query_ids": [],
      "evidence_ids": [],
      "contested_positions": [],
      "counterevidence": "unchecked",
      "gap_note": "why this matters",
      "scope_change": null
    }
  ],
  "completed_rounds": [],
  "stop": null
}
```

`initial_facets` is the immutable scope snapshot taken before retrieval. `priority` is `high` or `supporting`. `status` is `unsearched`, `searched`, `supported`, `contested`, or `unresolved`. `counterevidence` is `unchecked`, `searched-none-found`, `found`, or `not-applicable` (with reason in `gap_note`). `supported` requires at least one direct evidence ID; the existing 3-independent-source standard still applies to major claims. `contested_positions` is empty unless status is `contested`; then it contains at least two `{ "position": "...", "evidence_ids": ["..."] }` entries, with direct evidence IDs for each material side and the disagreement explained in `gap_note`. `unresolved` means search attempts failed to establish an answer. A facet can be added when evidence reveals an essential in-scope issue; the original question remains the anchor. Facet IDs and the initial facet rows are never deleted. A removed facet becomes an inactive tombstone; a demoted high-priority facet remains active with `priority: supporting`. Both require `scope_change` containing `previous_priority`, `new_priority`, `reason`, and supporting evidence IDs or an explicit user-scope reason. The validator compares every initial ID, question, and priority against the current row and checks this record before excluding a formerly high-priority facet from the stop gate. New facet IDs cannot collide with the initial snapshot.

Each entry in `completed_rounds` is `{ "round": 1, "query_ids": ["Q1"], "families": ["literal"], "target_high_priority_facet_ids": ["F1"], "new_relevant_source_ids": [], "material_changes": [], "coverage_ready_after": false }`. Record one only after all queries in that round have been screened and the ledger updated. A `material_changes` entry names `facet_id`, `kind`, `before`, and `after`; kinds are `status`, `counterevidence`, `contested_position`, `priority`, `facet_added`, and `scope_change`. Any such change makes the round non-low-yield, even if it found no new source. The query log supplies the per-query source trail; completed rounds persist the decision-relevant aggregate. A validator cross-checks query IDs/families, consecutive round numbers, canonical new-source IDs, and material changes against the current facet state before accepting a saturation decision.

Each `queries.jsonl` row contains `query_id`, `round`, `facet_ids`, `gap`, `family`, `query`, `provider`, `expected_evidence`, `result_source_ids`, `new_relevant_source_ids`, `coverage_changed`, and `notes`. Families are `literal`, `synonym`, `disciplinary`, `entity`, `source-specific`, `counterevidence`, `citation-neighborhood`, `vocabulary-probe`, and `delta`. A source counts as new only after canonical source registration and relevance screening. Duplicate URLs/DOIs do not increase yield. The query log is provenance, not evidence; source and evidence entries continue to live in their existing files. Existing `evidence.jsonl.retrieval_query` remains useful and should be filled when known.

`coverage.json.stop` and `run_manifest.json.retrieval_stop` record the same decision: `reason` (`coverage-saturated`, `budget-exhausted`, or `critical-error`), `at`, `round`, `unresolved_high_priority_facet_ids`, `remaining_gaps`, and `basis`. The validator must reject a `coverage-saturated` decision if any high-priority facet is unsearched, searched without direct evidence, or has unchecked counterevidence; a contested facet qualifies only if both sides have evidence and the conflict is described. This is structural validation, not automatic judgment that sources are relevant or independent.

## Research behavior

### Scope and initial searches

At scope, write 3–8 answerable facets, prioritizing those needed to answer the user's actual decision. Include expected source types and plausible counterarguments. Quick mode still writes a small ledger even though it skips the formal plan phase. The first batch includes the user's literal terms and distinct variants chosen for high-priority facets: synonyms/acronyms, field terminology, relevant named entities, source-specific searches, and a counterevidence search where meaningful. Each query must name a facet, expected evidence, and reason it differs from prior queries. Do not issue ten paraphrases solely to satisfy a count.

If initial results appear to have a vocabulary mismatch, the model may write a two- or three-sentence *hypothetical* answer to identify terms. It then extracts at most five candidate terms and issues at most two separate expanded queries, keeping the literal query in the batch. Every generated entity, number, and date is unverified until independently found in a real source. The hypothetical text is never a source, evidence entry, citation, or basis for a finding. This is lexical expansion inspired by Query2doc, not HyDE.

### After each batch

Register and deduplicate candidate sources, screen them as relevant/possibly relevant/irrelevant, persist useful evidence, and update the facets they address. Mark a query's new relevant source IDs and whether it changed a facet's status or revealed a new essential in-scope facet. Select the next query from the highest-priority concrete gap: unsearched facet, weakly evidenced claim, material contradiction, missing counterargument, or a new in-scope entity/limitation. Log its gap and expected novel evidence. For scholarly work, inspect references and citing papers of central publications once when the source interface exposes those links; do not require it for news or documentation. Keep source diversity and original scope checks from the current methodology.

### Stop decision

At the end of each batch, compute two boolean checks:

* `coverage_ready`: every high-priority facet has been searched and has direct evidence; each has a completed counterevidence check or a documented reason it does not apply; any contested facet has evidence for both material positions and a conflict note. Existing claim verification still applies before report delivery.
* `low_yield_round`: a completed round adds zero *new relevant, canonical* sources to high-priority facets and records no `material_changes`. Two consecutive low-yield rounds count toward saturation only if, together, they used at least two distinct query families and addressed the remaining high-priority gaps. Repeating one phrasing/provider does not count.

Once `coverage_ready` first becomes true, begin the saturation sequence. Run up to two residual probes in distinct query families, aimed at the weakest-supported high-priority facet, a plausible counterexample, a missing source type, or adjacent terminology. The probes must target high-priority facets even if no explicit gap remains. Only rounds completed *after* readiness count toward the two-round low-yield test. Any new relevant canonical source or material facet status change resets the count; if it creates a new high-priority gap, restore `coverage_ready` first. A single round containing two families does not substitute for two completed rounds. Stop with `coverage-saturated` only when readiness remains true and the last two completed residual rounds are low yield, use distinct families across the rounds, and have their summaries persisted and validated. Otherwise continue targeted search while the mode's time/tool budget allows. At the budget limit, stop with `budget-exhausted`, record every unresolved high-priority facet and remaining gap, and carry those limitations into the report. A truly critical tool/data error records `critical-error` and follows existing error handling. Source totals and average credibility never override open high-priority gaps. The two-round saturation rule is an operational heuristic, not a measured recall guarantee or a claim that all relevant web sources were found. Do not run background searches after recording a stop unless the decision is reopened and the new results are incorporated.

Phase 4.5 and critique delta searches use the same ledger and query log rather than an untracked side path. When critique reveals a new critical facet, reopen retrieval, run the targeted queries within budget, and record a fresh stop decision. Report the final stop reason and unresolved gaps in the Methodology Appendix and Limitations.

## Failure handling

* No useful results from a query: log zero yield, try a different family or provider, and leave the facet unresolved if the budget expires.
* Fabricated or off-topic expansion terms: discard them before source registration; return to literal/source-specific searches.
* Duplicate URLs or syndicated articles: canonicalize and count once for query yield; existing independence checks govern claim corroboration.
* Provider lacks rank/citation links: preserve all unique candidates and skip rank fusion/citation-neighborhood without treating absence as a coverage failure.
* Old run without coverage artifacts: validation reports unavailable coverage; existing citation/report checks still run. Do not infer a clean stop retroactively.
* Narrow or sparse domain: package a partial answer with an explicit `budget-exhausted` decision and open gaps, following the existing graceful-degradation rule.

## Test and evaluation strategy

Unit tests for initialization and validator should cover schema creation; missing artifacts; duplicate query IDs; invalid facet/evidence references; a valid coverage-saturated stop; rejection of premature saturation for unsearched, unsupported, or unchecked high-priority facets; contested facets with one side missing; an initial high-priority facet deleted or demoted without a tombstone rationale; missing or contradictory completed-round summaries; residual rounds completed before readiness; two low-yield rounds from one family; a new relevant source or material counterevidence/position change that resets the saturation count; and budget-exhausted with recorded gaps. Existing source/evidence/claim and report tests must pass unchanged. A small fixture should show the complete loop from initial queries through a gap-driven follow-up and stop decision.

Do not claim empirical recall improvement from these structural tests. A later evaluation should pool relevant sources for 20–30 varied prior questions, adjudicate required facets, and compare the current skill with the changed skill under comparable query/time budgets. Measure pooled Recall@20/50, high-priority facet coverage, unique relevant sources per search, off-topic rate, and cost. Hold out some questions and state that pooled recall is only an estimate for the open web.

## Task split

| Task | Work | Acceptance |
|---|---|---|
| 1. Artifacts and validator | Add coverage/query artifact initialization and a lightweight structural validator, with unit fixtures. | New runs contain the files; false `coverage-saturated` stops fail validation; old runs fail gracefully. |
| 2. Research loop instructions | Update `SKILL.md` and methodology for facet planning, query families, guarded vocabulary probe, evidence-driven follow-ups, conditional citation chasing, and exact stop logic. | A reader can run every mode without source-count auto-clearance or treating generated text as evidence. |
| 3. Integration and quality guidance | Align `research_engine.py` instruction templates, quality gates, output/report guidance, and examples with the artifacts; run tests and review all stop wording for contradictions. | Engine is still clearly a scaffold, docs and CLI agree, and repository tests pass. |

Tasks 1 and 2 can proceed independently. Task 3 consumes both and performs the final integration review.

## Post-Implementation Notes

To be filled after implementation: changed files, validation results, any deviations, and observed limitations.
