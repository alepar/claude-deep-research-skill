super-roast verdict: Should-fix (4 confirmed)
mode: PR · iteration: 2 of 3
inputs: super-auto/layered-research-prompts@c3f288b vs main@64cc893
delta vs prior: 4 new confirmed · 10 prior findings cleared · 0 carried
coverage: package, rendering, integration · 4 candidates → 4 three-seat panels
independence: same-family panel — reproduce, refute and ground seats · rung: manual fan-out

## Confirmed findings

- [Should-fix] scripts/validate_report_package.py:225 — Delivery accepts a `partial` dossier with a coverage-saturated stop and no facet-linked gap. Require a budget-exhausted stop and a declared gap for its facet.
- [Should-fix] scripts/continuation_state.py:163 — A critical-error retrieval stop can yield `complete` when other flags pass. Block completion and report the critical failure.
- [Should-fix] scripts/verify_html.py:82 — Text and citations inside `<script>` or `<style>` count as visible content. Ignore non-rendered elements in fidelity checks.
- [Should-fix] scripts/validate_report_package.py:153 — Bibliography URL substring matching accepts a different, attacker-controlled link. Compare the parsed target exactly to the registered URL.

## Cleared from prior

All ten round-one findings were checked and found cleared in the current branch.
