super-roast verdict: Should-fix (10 confirmed)
mode: PR · iteration: 1 of 3
inputs: super-auto/layered-research-prompts@96ee5af vs main@64cc893
coverage: schema, prompts, rendering · 11 candidates → 10 grouped findings · three judge seats
independence: same-family panel — reproduce, refute and ground seats · rung: manual fan-out

## Confirmed findings

- [Should-fix] scripts/validate_report_package.py:166 — An absent or empty `reporting` object bypasses all package checks for a new deep run. Distinguish legacy compatibility from delivery validation; require a complete reporting object for delivery.
- [Should-fix] scripts/validate_report_package.py:229 — A compact Quick or Standard report with a reporting object is required to have a dossier for every high facet. Validate its final facet coverage without inventing dossiers.
- [Should-fix] scripts/verify_coverage.py:306 — Both stop fields may be null and coverage verification passes even at delivery. Require a persisted stop for delivery and reconcile it with the package gate.
- [Should-fix] scripts/continuation_state.py:90 — `next_task: null` returns `complete` before required worker returns or final validation. Make completion depend on join and validation state.
- [Should-fix] scripts/validate_report_package.py:211 — A dossier marked `draft` passes the delivery validator and covers a high facet. Reject unfinished dossiers at delivery.
- [Should-fix] scripts/validate_report_package.py:251 — Registered final synthesis claims are excluded from required evidence anchors. Require anchors for material supported synthesis claims; semantic entailment still needs review.
- [Should-fix] scripts/validate_report_package.py:30 — Valid angle-bracket Markdown dossier links and `../` links from a nested final report fail despite resolving within the package. Normalize and bound links to the package root.
- [Should-fix] scripts/verify_html.py:111 — A correctly rendered HTML report omits Markdown comment markers from visible text and fails fidelity validation; swapping two citation numbers between claims passes. Compare visible content and citation placement correctly.
- [Should-fix] scripts/verify_html.py:138 — A multiline Markdown bibliography URL may be omitted from rendered HTML while verification passes. Compare complete entries or canonical links.
- [Should-fix] scripts/verify_citations.py:92 — The new Markdown-link bibliography form bypasses title metadata checks; a multiline URL can be missed. Parse the supported bibliography forms before calling them verified.

## Rejected or qualified

- Structural validators cannot detect a factual sentence that was never registered as a claim. The skill requires claim extraction and human semantic review; do not claim automatic entailment.
- Zero dossiers is valid for compact Quick and some Standard reports. The delivery check must validate their final report and facets.
