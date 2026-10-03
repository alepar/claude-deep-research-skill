# Deep Research Methodology: 8-Phase Pipeline

## Overview

This document contains the detailed methodology for conducting deep research. The 8 phases represent a comprehensive approach to gathering, verifying, and synthesizing information from multiple sources.

---

## Phase 1: SCOPE - Research Framing

**Objective:** Define research boundaries and success criteria

**Activities:**
1. Preserve the user's original question and decompose it into 3–8 answerable facets. Mark each `high` if it is necessary for the user's decision, otherwise `supporting`.
2. Identify stakeholder perspectives
3. Define scope boundaries (what's in/out)
4. For each facet, name expected source types, a plausible counterargument, and the gap that would matter if evidence is absent. Initialize `coverage.json` with the immutable `initial_facets` snapshot and current `facets` rows before searching. Quick mode does this despite skipping Phase 2.
5. Establish success criteria and list key assumptions to validate

Keep the original question as the scope anchor. Evidence may reveal a new essential in-scope facet. Never erase an initial facet: preserve its ID and initial snapshot. If evidence or an explicit user-scope reason justifies removing or demoting one, retain an inactive or supporting current row with a `scope_change` record (`previous_priority`, `new_priority`, `reason`, and supporting evidence IDs or the explicit user-scope reason). A new facet gets a unique ID.

Write `coverage.json` as the latest state after each round; retain `question`, `initial_facets`, `facets`, `completed_rounds`, and `stop` (initially `null`). An old run without coverage artifacts has unavailable coverage; do not infer a clean stop from its source totals.

**Ultrathink Application:** Use extended reasoning to explore multiple framings of the question before committing to scope.

**Output:** Structured scope document with research boundaries

---

## Phase 2: PLAN - Strategy Formulation

**Objective:** Create an intelligent research roadmap

**Activities:**
1. Identify primary and secondary sources
2. Map knowledge dependencies (what must be understood first)
3. Plan distinct query families for high-priority facets, starting with the user's literal terms and choosing variants for specific evidence gaps
4. Plan triangulation approach
5. Estimate time/effort per phase
6. Define quality gates

**Graph-of-Thoughts:** Branch into multiple potential research paths, then converge on optimal strategy.

**Output:** Research plan with prioritized investigation paths, expected evidence, and a retrieval budget. Quick mode makes these decisions directly from its scope ledger without a separate plan document.

---

## Phase 3: RETRIEVE - Coverage-Led Information Gathering

**Objective:** Find decision-relevant evidence for the scoped facets, preserve its provenance, and make an explicit retrieval stop decision. This procedure applies to Quick, Standard, Deep, and UltraDeep modes. Parallelize independent searches when useful, but finish screening and ledger updates before declaring a round complete.

### Query planning and execution

**Step 0: Get the current date.** Before date-sensitive searches, retrieve today's date with `date +%Y-%m-%d`; use that date for filters and recency checks.

**Step 1: Select distinct queries from the ledger.** The first batch must retain the user's literal wording and address high-priority facets. Choose variants because they seek different evidence, not to reach a query count:

| Family | Use when |
|---|---|
| `literal` | Preserve the user's terms as the baseline query. |
| `synonym` | Search acronyms or alternate wording. |
| `disciplinary` | Search the terminology used by a relevant field. |
| `entity` | Look for an evidenced organization, product, person, or event. |
| `source-specific` | Search likely primary repositories, agencies, or documentation. |
| `counterevidence` | Test a plausible contrary claim or failure mode. |
| `citation-neighborhood` | Inspect references and citing papers of central scholarly publications once when the source interface exposes them. |
| `vocabulary-probe` | Expand vocabulary under the guard below. |
| `delta` | Fill a specific gap revealed by outline refinement or critique. |

For every query, name its facet IDs, concrete gap, expected evidence, and why it differs from prior queries. Include a meaningful counterevidence query in the opening batch where possible. Do not manufacture variants for a count. Citation-neighborhood is conditional on a central scholarly source and available links; news and documentation research do not require it. A provider without citation links is not a coverage failure.

If literal results suggest a vocabulary mismatch, write a two- or three-sentence *hypothetical* answer solely to extract at most five candidate terms. Use at most two separate expanded queries and keep the literal query in the batch. Treat every generated entity, number, and date as unverified until a real source confirms it. Discard fabricated or off-topic terms. The hypothetical text is never a source, evidence entry, citation, or basis for a finding. This is a guarded vocabulary probe, not HyDE.

**Step 2: Execute the batch.** Use `search-cli` first (`search "query" --json -c 10`, with an appropriate mode such as `academic` or `news`); use WebSearch if it fails, is rate-limited, or a domain restriction is needed. Exa MCP is optional when configured. Use the correct parameters for each provider. Run independent queries concurrently where tools permit. Use extraction/fetch tools to read promising sources. Delegate focused deep dives only when the environment and task permit it; require source URLs, exact passages, and locators from any delegate.

**Step 3: Screen, persist, and update.** For each query, screen candidates as relevant, possibly relevant, or irrelevant. Register relevant sources canonically before counting them; duplicate URLs, DOIs, and syndicated copies do not increase yield. Persist useful passages in `evidence.jsonl` with source IDs and locators before synthesis. Fill `evidence.jsonl.retrieval_query` when known. Source diversity, recency, independence, geography, and credibility remain important checks, but a total or average score never closes a facet.

Append one `queries.jsonl` row per query with `query_id`, `round`, `facet_ids`, `gap`, `family`, `query`, `provider`, `expected_evidence`, `result_source_ids`, `new_relevant_source_ids`, `coverage_changed`, and `notes`. The query log records provenance, not evidence. Update each facet's `query_ids`, direct `evidence_ids`, `status` (`unsearched`, `searched`, `supported`, `contested`, or `unresolved`), `counterevidence` (`unchecked`, `searched-none-found`, `found`, or `not-applicable` with a reason), and `gap_note`. `supported` needs direct evidence. For `contested`, record at least two material positions with direct evidence IDs for each side and explain the conflict. Mark `unresolved` when attempts fail to establish an answer. Keep the three-independent-source standard for major claims separate from this facet status.

After all queries in a batch are screened and coverage is updated, append a `completed_rounds` summary with `round`, `query_ids`, `families`, `target_high_priority_facet_ids`, `new_relevant_source_ids`, `material_changes`, and `coverage_ready_after`. Material changes include facet status, counterevidence state, contested position, priority, a new essential facet, or scope change; record `facet_id`, `kind`, `before`, and `after`. A round with a material change is not low yield even if it found no new source.

**Step 4: Choose the next gap.** Follow the highest-priority concrete gap: an unsearched facet, weakly evidenced claim, material contradiction, missing counterargument or source type, or new in-scope entity or limitation. Log what novel evidence the next query could find. If a query yields nothing, log zero yield and try a different family or provider within budget. Do not treat search-result snippets or generated text as evidence. Recheck that follow-ups still serve the original question.

### Retrieval stop decision

Check at the end of each completed round:

- `coverage_ready` is true only when every active high-priority facet has been searched and has direct evidence; each has a completed counterevidence search or a documented reason it does not apply; and every contested facet has direct evidence for both material positions plus an explained conflict. A demoted or inactive initial high-priority facet needs its recorded scope-change justification before exclusion. Claim verification still applies before report delivery.
- `low_yield_round` is true only when a completed round adds zero new relevant canonical sources to high-priority facets and records no material changes. Duplicate results do not increase yield.

When readiness first becomes true, begin the saturation sequence. Seek two *subsequent* low-yield residual probe rounds in distinct query families, aimed at the weakest-supported high-priority facet, a plausible counterexample, a missing source type, or adjacent terminology. Target high-priority facets even if no explicit gap remains. A single round with two families is still one round. Only rounds completed after readiness count; they must together address remaining high-priority gaps. Any new relevant canonical source or material facet change resets the low-yield count. If the change opens a high-priority gap, restore readiness before restarting residual probes. Stop as `coverage-saturated` only when readiness still holds and the last two post-readiness rounds are both low yield, use distinct families across the rounds, and are persisted and validated. This is an operational heuristic, not a guarantee of web recall.

Continue targeted search while the mode's time or tool budget permits. At the budget limit, stop as `budget-exhausted` and list every high-priority facet that fails coverage readiness (including one with evidence but unchecked counterevidence), plus each remaining gap, even if there are many credible sources. A truly critical tool or data error uses `critical-error` and the existing error path. Record the same decision in `coverage.json.stop` and `run_manifest.json.retrieval_stop`: `reason`, `at`, `round`, `unresolved_high_priority_facet_ids`, `remaining_gaps`, and `basis`. Do not run background searches after a stop unless retrieval is reopened and their results are incorporated. Source totals and credibility are depth diagnostics, never automatic stop gates. For sparse domains, deliver a qualified partial answer with the budget stop and open gaps.

**Source quality:** Seek primary material, multiple independent source clusters for major claims, relevant source types, recent and foundational sources, opposing perspectives, and geographic diversity where the topic warrants them. Score credibility with `source_evaluator.py`; verify low-scoring sources before relying on them. These checks guide follow-ups and claim verification, not the stop decision by themselves.

**Output:** Canonical source and evidence stores, `queries.jsonl` provenance, current `coverage.json`, and a documented retrieval stop decision.

---

## Phase 4: TRIANGULATE - Cross-Reference Verification

**Objective:** Validate information across multiple independent sources

**Activities:**
1. Identify claims requiring verification
2. Cross-reference facts across 3+ sources
3. Flag contradictions or uncertainties
4. Assess source credibility
5. Note consensus vs. debate areas
6. Document verification status per claim

**Quality Standards:**
- Core claims must have 3+ independent sources
- Flag any single-source information
- Note recency of information
- Identify potential biases

**Output:** Verified fact base with confidence levels

---

## Phase 4.5: OUTLINE REFINEMENT - Dynamic Evolution (WebWeaver 2025)

**Objective:** Adapt research direction based on evidence discovered

**Problem Solved:** Prevents "locked-in" research when evidence points to different conclusions or uncovers more important angles than initially planned.

**When to Execute:**
- **Standard/Deep/UltraDeep modes only** (Quick mode skips this)
- After Phase 4 (TRIANGULATE) completes
- Before Phase 5 (SYNTHESIZE)

**Activities:**

1. **Review Initial Scope vs. Actual Findings**
   - Compare Phase 1 scope with Phase 3-4 discoveries
   - Identify unexpected patterns or contradictions
   - Note underexplored angles that emerged as critical
   - Flag overexplored areas that proved less important

2. **Evaluate Outline Adaptation Need**

   **Signals for adaptation (ANY triggers refinement):**
   - Major findings contradict initial assumptions
   - Evidence reveals more important angle than originally scoped
   - Critical subtopic emerged that wasn't in original plan
   - Original research question was too broad/narrow based on evidence
   - Sources consistently discuss aspects not in initial outline

   **Signals to keep current outline:**
   - Evidence aligns with initial scope
   - All key angles adequately covered
   - No major gaps or surprises

3. **Refine Outline (if needed)**

   **Update structure to reflect evidence:**
   - Add sections for unexpected but important findings
   - Demote/remove sections with insufficient evidence
   - Reorder sections based on evidence strength and importance
   - Adjust scope boundaries based on what's actually discoverable

   **Example adaptation:**
   ```
   Original outline:
   1. Introduction
   2. Technical Architecture
   3. Performance Benchmarks
   4. Conclusion

   Refined after Phase 4 (evidence revealed security as critical):
   1. Introduction
   2. Technical Architecture
   3. **Security Vulnerabilities (NEW - major finding)**
   4. Performance Benchmarks (demoted - less critical than expected)
   5. **Real-World Failure Modes (NEW - pattern emerged)**
   6. Synthesis & Recommendations
   ```

4. **Targeted Gap Filling (if major gaps found)**

   If outline refinement reveals critical knowledge gaps, update `coverage.json` and reopen retrieval. Log targeted `delta` queries in `queries.jsonl`, screen and persist results, update triangulation, and complete the same readiness and stop checks within the remaining mode budget. Record a fresh stop decision. Do not run an untracked side search or retain an earlier saturation decision after reopening.

5. **Document Adaptation Rationale**

   Record in methodology appendix:
   - What changed in outline
   - Why it changed (evidence-driven reasons)
   - What additional research was conducted (if any)

**Quality Standards:**
- Adaptation must be evidence-driven (cite specific sources that prompted change)
- No more than 50% outline restructuring (if more needed, scope was severely mis scoped)
- Retain original research question core (don't drift into different topic entirely)
- New sections must have supporting evidence already gathered

**Output:** Refined outline that accurately reflects evidence landscape, ready for synthesis

**Anti-Pattern Warning:**
- ❌ DON'T adapt outline based on speculation or "what would be interesting"
- ❌ DON'T add sections without supporting evidence already in hand
- ❌ DON'T completely abandon original research question
- ✅ DO adapt when evidence clearly indicates better structure
- ✅ DO document rationale for changes
- ✅ DO stay within original topic scope

---

## Phase 5: SYNTHESIZE - Deep Analysis

**Objective:** Connect insights and generate novel understanding

**Activities:**
1. Identify patterns across sources
2. Map relationships between concepts
3. Generate insights beyond source material
4. Create conceptual frameworks
5. Build argument structures
6. Develop evidence hierarchies

**Ultrathink Integration:** Use extended reasoning to explore non-obvious connections and second-order implications.

**Output:** Synthesized understanding with insight generation

---

## Phase 6: CRITIQUE - Quality Assurance

**Objective:** Rigorously evaluate research quality

**Activities:**
1. Review for logical consistency
2. Check citation completeness
3. Identify gaps or weaknesses
4. Assess balance and objectivity
5. Verify claims against sources
6. Test alternative interpretations

**Red Team Questions:**
- What's missing?
- What could be wrong?
- What alternative explanations exist?
- What biases might be present?
- What counterfactuals should be considered?

**Persona-Based Critique (Deep/UltraDeep only):**
Simulate 2-3 specific critic personas relevant to the topic:
- "Skeptical Practitioner" — Would someone doing this daily trust these findings?
- "Adversarial Reviewer" — What would a peer reviewer reject?
- "Implementation Engineer" — Can these recommendations actually be executed?

**Critical Gap Loop-Back:**
If critique identifies a critical knowledge gap or a new essential in-scope facet (rather than only a writing issue), reopen Phase 3. Update `coverage.json`, run targeted `delta` queries within the remaining budget, append them to `queries.jsonl`, and record a new stop decision after screening and ledger updates. If the budget runs out, preserve the unresolved gap in the report. A prior `coverage-saturated` decision does not survive newly discovered contrary evidence or a new high-priority facet.

**Output:** Critique report with improvement recommendations

---

## Phase 7: REFINE - Iterative Improvement

**Objective:** Address gaps and strengthen weak areas

**Activities:**
1. Conduct additional research for gaps
2. Strengthen weak arguments
3. Add missing perspectives
4. Resolve contradictions
5. Enhance clarity
6. Verify revised content

Any additional research here follows the Phase 3 ledger, query provenance, and stop rules. Report the final stop reason and unresolved high-priority gaps in both the Methodology Appendix and Limitations.

**Output:** Strengthened research with addressed deficiencies

---

## Phase 8: PACKAGE - Report Generation

**Objective:** Deliver professional, actionable research

**Activities:**
1. Structure report with clear hierarchy
2. Write executive summary
3. Develop detailed sections
4. Create visualizations (tables, diagrams)
5. Compile full bibliography
6. Add methodology appendix

**Output:** Complete research report ready for use

---

## Advanced Features

### Graph-of-Thoughts Reasoning

Rather than linear thinking, branch into multiple reasoning paths:
- Explore alternative framings in parallel
- Pursue tangential leads that might be relevant
- Merge insights from different branches
- Backtrack and revise as new information emerges

### Parallel Agent Deployment

Use Task tool to spawn sub-agents for:
- Parallel source retrieval
- Independent verification paths
- Competing hypothesis evaluation
- Specialized domain analysis

### Adaptive Depth Control

Automatically adjust research depth based on:
- Information complexity
- Source availability
- Time constraints
- Confidence levels

### Citation Intelligence

Smart citation management:
- Track provenance of every claim
- Link to original sources
- Assess source credibility
- Handle conflicting sources
- Generate proper bibliographies
