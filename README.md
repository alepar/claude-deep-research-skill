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

## Pipeline

Scope &rarr; Plan &rarr; **Retrieve** (parallel search + agents) &rarr; Triangulate &rarr; Outline Refinement &rarr; Synthesize &rarr; Critique (with loop-back) &rarr; Refine &rarr; Package

Key features:
- **Step 0**: Retrieves current date before searches (prevents stale training-data year assumptions)
- **Coverage-led retrieval**: 3-8 answerable facets, with high-priority gaps and expected source types recorded before searching, including Quick mode
- **Distinct query families**: Literal wording first, then targeted synonyms, field terms, entities, source-specific searches, and counterevidence; optional guarded vocabulary expansion and scholarly citation chasing
- **Evidence-driven follow-ups**: Log each query, screened yield, and material facet change; choose the next query from the largest decision-relevant gap
- **Explicit stop**: Coverage readiness followed by two distinct, low-yield residual rounds, or a budget/critical-error stop with unresolved gaps
- **Critique loop-back**: New essential in-scope gaps reopen Phase 3 through the same ledger and query log
- **Multi-persona red teaming**: Skeptical Practitioner, Adversarial Reviewer, Implementation Engineer (Deep/UltraDeep)
- **Disk-persisted artifacts**: `sources.jsonl`, `evidence.jsonl`, `claims.jsonl`, `coverage.json`, `queries.jsonl`, and `run_manifest.json` survive context compaction

## Output

Reports saved to `~/Documents/[Topic]_Research_[Date]/`:
- Markdown (primary source of truth)
- HTML (McKinsey-style, auto-opened in browser)
- PDF (professional print via WeasyPrint)

Reports >18K words auto-continue via recursive agent spawning with context preservation.

## Quality Standards

- 10+ sources is a depth diagnostic, never an automatic retrieval stop; major claims need 3+ independent sources
- Each high-priority facet needs direct evidence and a counterevidence check or documented exception; contested facets need evidenced material sides
- Final stop reason and unresolved gaps appear in Methodology Appendix and Limitations
- Executive summary 200-400 words
- Findings 600-2,000 words each, prose-first (>=80%)
- Full bibliography with URLs, no placeholders
- Structural retrieval check: `python scripts/verify_coverage.py --dir [run_folder]`; this does not judge source relevance or measure recall
- Report checks: `validate_report.py` and `verify_citations.py` (citation and metadata checks)
- Validation loop: validate &rarr; fix &rarr; retry (max 3 cycles)

## Search Tools

| Tool | Priority | Setup |
|------|----------|-------|
| search-cli | **Primary** — all searches go here first | `brew install search-cli` + API keys |
| WebSearch | Fallback — if search-cli fails or rate-limited | None (built-in) |
| Exa MCP | Optional — semantic/neural search alongside search-cli | MCP config |

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
│   ├── validate_report.py            # 9-check structure validator
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
