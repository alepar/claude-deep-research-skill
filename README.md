# Deep Research Skill for Claude Code

A Claude Code skill for citation-backed research reports. It guides source discovery, records evidence and question coverage on disk, and validates report and retrieval artifacts. Claude runs the research; `scripts/research_engine.py` prints phase instructions and saves scaffold state.

## Installation

```bash
# Clone into Claude Code skills directory
git clone https://github.com/alepar/claude-deep-research-skill.git ~/.claude/skills/deep-research
```

No additional dependencies required for basic usage.

### Optional: search-cli (multi-provider search)

For aggregated search across Brave, Serper, Exa, Jina, and Firecrawl:

```bash
brew tap 199-biotechnologies/tap && brew install search-cli
search config set keys.brave YOUR_KEY  # configure at least one provider
```

## Usage

```
deep research on the current state of quantum computing
```

```
deep research in ultradeep mode: compare PostgreSQL vs Supabase for our stack
```

## Research Modes

| Mode | Phases | Duration | Best For |
|------|--------|----------|----------|
| Quick | 3 | 2-5 min | Initial exploration |
| Standard | 6 | 5-10 min | Most research questions |
| Deep | 8 | 10-20 min | Complex topics, critical decisions |
| UltraDeep | 8+ | 20-45 min | Comprehensive reports, maximum rigor |

## Workflow

Scope the question into answerable facets, retrieve and register direct evidence, check coverage, draft facet dossiers when useful, and synthesize a final report. Reopen retrieval when a material gap appears.

Key features:
- **Coverage-led retrieval**: answerable facets, with high-priority gaps and expected source types recorded before searching, including Quick mode
- **Distinct query families**: Literal wording first, then targeted synonyms, field terms, entities, source-specific searches, and counterevidence; optional guarded vocabulary expansion and scholarly citation chasing
- **Evidence-driven follow-ups**: Log each query, screened yield, and material facet change; choose the next query from the largest decision-relevant gap
- **Explicit stop**: Coverage readiness followed by two distinct, low-yield residual rounds, or a budget/critical-error stop with unresolved gaps
- **Gap recovery**: New essential in-scope gaps reopen retrieval through the same ledger and query log
- **Disk-persisted artifacts**: `sources.jsonl`, `evidence.jsonl`, `claims.jsonl`, `coverage.json`, `queries.jsonl`, and `run_manifest.json` survive context compaction

## Output

The user-requested destination takes precedence; otherwise reports go to
`~/Documents/[Topic]_Research_[YYYYMMDD]/`. The default deliverable is a
Markdown final report, with linked Markdown facet dossiers for deeper runs.
Generate HTML or PDF only when requested. Do not open deliverables automatically.
For long writing tasks, save state at section and dossier boundaries, then
continue from the checkpoint when capacity requires it. With no capacity signal,
18,000 words is a conservative per-agent fallback ceiling, not a report target.

## Quality Standards

- Source counts are diagnostics, never automatic retrieval stops; seek independent corroboration for consequential claims where available
- Each high-priority facet needs direct evidence and a counterevidence check or documented exception; contested facets need evidenced material sides
- Final stop reason and unresolved gaps appear in the report's methodology and limitations
- Final synthesis sized to the decision and supported by linked evidence dossiers
- Full bibliography with URLs, no placeholders
- Structural retrieval check: `python scripts/verify_coverage.py --dir [run_folder]`; this does not judge source relevance or measure recall
- Package checks: `validate_report.py`, `validate_report_package.py`, and applicable citation and claim-support checks
- Repair the failing artifact and rerun the affected check; ask for input only if a trustworthy answer cannot be produced

## Search Tools

| Tool | Priority | Setup |
|------|----------|-------|
| search-cli | Available multi-provider option | `brew install search-cli` + API keys |
| Host web search | Available host option | Host dependent |
| Exa MCP | Optional semantic search | MCP config |

## Architecture

```
deep-research/
├── SKILL.md                          # Skill entry point (lean, ~100 lines)
├── reference/
│   ├── methodology.md                # 8-phase pipeline details
│   ├── report-assembly.md            # Progressive generation strategy
│   ├── quality-gates.md              # Validation standards
│   ├── html-generation.md            # McKinsey HTML conversion
│   ├── continuation.md               # Auto-continuation protocol
│   └── weasyprint_guidelines.md      # PDF generation
├── templates/
│   ├── report_template.md            # Report structure template
│   └── mckinsey_report_template.html # HTML report template
├── scripts/
│   ├── validate_report.py            # 6-check Markdown surface validator
│   ├── verify_citations.py           # DOI/URL/hallucination checker
│   ├── source_evaluator.py           # Source credibility scoring
│   ├── citation_manager.py           # Citation tracking
│   ├── verify_coverage.py            # Structural retrieval/stop validation
│   ├── md_to_html.py                 # Markdown to HTML converter
│   ├── verify_html.py                # HTML verification
│   └── research_engine.py            # Phase instruction/state scaffold
├── schemas/                          # Artifact schemas
└── tests/
    └── fixtures/                     # Test report fixtures
```

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.3.1 | 2026-03-19 | Template/validator harmonization, structured evidence, critique loop-back, multi-persona red teaming |
| 2.3 | 2026-03-19 | Contract harmonization, search-cli integration, dynamic year detection, disk-persisted citations, validation loops |
| 2.2 | 2025-11-05 | Auto-continuation system for unlimited length |
| 2.1 | 2025-11-05 | Progressive file assembly |
| 1.0 | 2025-11-04 | Initial release |

## License

MIT - modify as needed for your workflow.
