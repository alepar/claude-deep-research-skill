super-roast verdict: Should-fix (5 confirmed) [converged]
mode: PR · iteration: 3 of 3
profile (assumed): Local research skill and report validators. A false delivery pass or wrong evidence link can mislead readers of a research report.
inputs: super-auto/layered-research-prompts@c27d3a7 vs main@64cc893
delta vs prior: 5 new confirmed (0 Blocking) · 0 carried · 4 resolved · 0 regressed Blocking · 0 punch-listed (open)
coverage: package, rendering, regression · 5 candidates → 5 three-seat panels · 100% seats returned
independence: same-family panel — reproduce, refute and ground seats · rung: manual fan-out
seat-agreement: panels 5 · unanimous 5/5 · reproduce 5/0/0 · refute 5/0/0 · ground 5/0/0

## Confirmed findings

- [Should-fix] scripts/validate_report_package.py:217 — `--delivery` accepts matching `critical-error` stops, despite continuation rules blocking completion.
  verdict: confirmed (reproduce ✓ / refute ✓ / ground ✓)
  evidence: A complete two-dossier package with manifest and coverage stops both set to `critical-error` returned `status: ok` at delivery.
  fix-shape hint: Reject critical-error before a package can be delivered; retain a fresh-stop recovery path.
- [Should-fix] scripts/verify_html.py:210 — An HTML bibliography link whose destination merely extends the registered URL passes fidelity validation.
  verdict: confirmed (reproduce ✓ / refute ✓ / ground ✓)
  evidence: Markdown expected `https://example.org/a`, while an HTML entry linked to `https://example.org/attacker`; verification returned true. A wrong href with the expected URL displayed as text also passes.
  fix-shape hint: Compare parsed link targets and visible URLs exactly.
- [Should-fix] scripts/validate_report_package.py:255 — Valid freeform `remaining_gaps` text is rejected for a partial dossier unless it starts with an undocumented `facet_id:` prefix. [fix-regression]
  verdict: confirmed (reproduce ✓ / refute ✓ / ground ✓)
  evidence: Budget stop, active unresolved facet, nonempty `gap_note`, and `remaining_gaps: ["No outcome data for facet alpha"]` failed delivery; the schema allows freeform strings.
  fix-shape hint: Use the facet's structured `gap_note` to establish linkage and accept nonempty remaining gaps, or document and enforce a new format end to end.
- [Should-fix] scripts/validate_report_package.py:165 — Exact bare source URLs ending in `)` fail bibliography validation. [fix-regression]
  verdict: confirmed (reproduce ✓ / refute ✓ / ground ✓)
  evidence: Registered `https://example.org/topic_(alpha)` appears exactly as a bare bibliography URL, but unconditional punctuation stripping removes its last character.
  fix-shape hint: Check the raw token exactly before stripping trailing prose punctuation.
- [Should-fix] scripts/verify_html.py:60 — A report finding and citation inside an HTML element with `hidden` can satisfy visible-content fidelity checks.
  verdict: confirmed (reproduce ✓ / refute ✓ / ground ✓)
  evidence: HTML with the only matching finding in `<p hidden>` passed against Markdown; `style="display:none"` also passed. `aria-hidden` alone is outside this finding.
  fix-shape hint: Exclude subtrees hidden by standard HTML attributes and simple inline display/visibility rules.

## Cleared from prior

All four round-two findings were checked and found cleared in the current branch.

## Rejected (with reason)

None.

## Escalations (need human)

None.
