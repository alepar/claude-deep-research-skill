# Report Assembly

## Choose the delivered shape

Deliver a final Markdown report by default. Put it in the user's requested
destination; otherwise use `~/Documents/[Topic]_Research_[YYYYMMDD]/`. Keep the
package self-contained. Render the final report as HTML or PDF only when asked;
keep the linked Markdown dossiers in the delivered folder unless rendered
dossiers were also requested. Do not open files automatically.

Deep and UltraDeep runs plan linked dossiers from the start. Standard runs use
them when several facets have substantial independent evidence or a single
report would bury useful detail. Quick runs normally produce one compact
report. The lead may choose another shape when the request or evidence warrants
it and records why. Size each dossier by its evidence and importance. Size the
final synthesis for the reader's decision. Do not enforce finding counts,
section word targets, citation-density targets, or prose percentages.

## Initialize and preserve the research record

Start the run before retrieval:

```bash
python scripts/citation_manager.py init-run --out-dir [run_folder] --query "[question]" --mode [mode]
```

This creates `run_manifest.json`, `coverage.json`, `queries.jsonl`,
`sources.jsonl`, `evidence.jsonl`, and `claims.jsonl`. The original question and
`coverage.initial_facets` anchor scope. Record screened queries and completed
rounds; register source and evidence IDs in the canonical files. A source may
appear in several dossiers under the same stable source ID. Source similarity
does not determine facet scope.

Before drafting, save one retrieval stop decision in both `coverage.json.stop`
and `run_manifest.json.retrieval_stop`. Use `coverage-saturated`,
`budget-exhausted`, or `critical-error`, including basis, unresolved high
priority facets, and remaining gaps. If drafting exposes a material gap, reopen
retrieval with `delta` queries and a new round, then save a fresh stop. Run:

```bash
python scripts/verify_coverage.py --dir [run_folder]
```

Its result checks structural consistency; the lead still judges whether the
evidence answers each facet and whether contrary positions were fairly sought.

## Build facet dossiers

Group by answerable facet first. A dossier may cover closely related facets,
but list their IDs in `run_manifest.reporting.dossiers[].facet_ids`. Inside it,
group related sources and competing positions. Each Markdown dossier has a
short summary, facet question and answer, supported claims, counterevidence,
methods and limits, and open gaps. Detailed passages belong here when useful.

The lead owns `run_manifest.json` and all canonical ledgers. It adds the
optional `reporting` object with `output_mode`, relative `final_report_path`,
and dossier rows: stable `id`, relative Markdown `path`, `facet_ids`,
`source_ids`, `evidence_ids`, `claim_ids`, and `status` (`draft`, `complete`, or
`partial`). A worker writes only its exclusive dossier path. Give each worker
the assigned facets and canonical IDs, permitted inputs, a bounded task, and a
stop condition. Its return names output path, covered facets, source/evidence/
claim IDs, candidate evidence, unresolved gaps, and status. The lead waits for
all required returns, registers any new evidence itself, updates coverage, and
verifies each returned dossier. When subagents are unavailable, perform the
same tasks sequentially.

Use artifact-qualified claim section IDs such as `dossier-a:findings` and
`final:synthesis`. A factual statement needs an original source citation and
a registered claim/evidence trail. Write its visible citation and validator
anchor together:

```markdown
The intervention reduced events in the trial [1]. <!-- claim: 0123456789abcdef; evidence: abcdef0123456789; source: fedcba9876543210 -->
```

The IDs are the real 16-character IDs from `claims.jsonl`, `evidence.jsonl`,
and `sources.jsonl`; the display number comes from the canonical source
registry. Declare all dossier IDs used in its manifest row. A dossier is a
derived reading artifact, never an original source for the final report.

## Synthesize the final report

Read dossier summaries first, then inspect underlying evidence for every
material conclusion used in the final. Reconcile overlapping or conflicting
dossiers explicitly. The final report gives the direct answer, cross-facet
synthesis, useful recommendations, limits and open gaps, final retrieval stop
reason, methodology, and bibliography. Link every delivered dossier with a
relative Markdown link. Mark each covered facet where discussed, for example
`<!-- facet: facet-a -->`. For factual final claims, cite original registered
sources with visible `[N]` and the same claim/evidence/source anchor; create
`final:*` claim records. Do not cite a dossier as the source of a fact.

Assign display numbers from the source registry when rendering:

```bash
python scripts/citation_manager.py assign-display-numbers --dir [run_folder]
```

Display numbers are presentation only. Do not persist them as source identity
or rely on a working-memory citation list. Derive each bibliography entry from
the registry, with its correct `[N]`, title, and original URL. Include an
entry for every number cited in the final body; do not use ranges or truncated
placeholders.

## Validate and deliver

```bash
python scripts/verify_coverage.py --dir [run_folder]
python scripts/verify_claim_support.py verify --dir [run_folder] --strict
python scripts/validate_report_package.py --dir [run_folder]
python scripts/verify_citations.py --report [final_report_path]
```

Run the relevant HTML/PDF check only when that format was requested. The
package validator checks facet markers, dossier links, declared IDs, visible
citations, and bibliography against the canonical record; it cannot establish
that prose is semantically entailed by evidence. Review that question directly
for material claims and contradictions. Repair a failing artifact and rerun
the affected check; widen validation only when the repair can affect another
check. If evidence remains insufficient, remove or qualify the claim or reopen
retrieval. A budget-limited package can be delivered with explicit open gaps
and supported remaining claims.

Save a continuation checkpoint after each completed section or dossier using
`scripts/continuation_state.py`; see [continuation.md](continuation.md).
