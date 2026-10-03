# Report Assembly: Progressive File Generation

## Length Requirements by Mode

| Mode | Target Words | Description |
|------|--------------|-------------|
| Quick | 2,000-4,000 | Baseline quality threshold |
| Standard | 4,000-8,000 | Comprehensive analysis |
| Deep | 8,000-15,000 | Thorough investigation |
| UltraDeep | 15,000-20,000+ | Maximum rigor (at output limit) |

---

## Output Token Safeguard

**Claude Code default limit:** 32,000 output tokens (~24,000 words total per execution)

**Practical limits:**
- Target <=20,000 words total output
- Leave safety margin for tool call overhead
- Reports >20,000 words require auto-continuation (see continuation.md)

---

## Progressive Section Generation

**Core Strategy:** Generate and write each section individually using Write/Edit tools. This allows unlimited report length while keeping each generation manageable.

### Phase 8.1: Setup

```bash
# Create folder: ~/Documents/[TopicName]_Research_[YYYYMMDD]/
mkdir -p ~/Documents/[folder_name]

# Initialize markdown file with frontmatter
# Path: [folder]/research_report_[YYYYMMDD]_[slug].md
```

### Phase 8.2: Section Generation Loop

**Pattern:** Generate section -> Write/Edit to file -> Move to next section
Each Write/Edit call contains ONE section (<=2,000 words per call)

**Initialize the run before retrieval (persist to disk):**
```bash
# Create run manifest and artifact files using citation_manager CLI
python scripts/citation_manager.py init-run --out-dir [folder] --query "[question]" --mode [mode]
# Creates: run_manifest.json, sources.jsonl, evidence.jsonl, claims.jsonl,
#          coverage.json, queries.jsonl
```

At scope, fill `coverage.json` with the original question, immutable
`initial_facets`, current `facets`, empty `completed_rounds`, and `stop: null`.
Quick mode does this without a formal plan. During retrieval, append one
`queries.jsonl` row for each screened query and update coverage after each
completed round. Set a query's `coverage_changed` flag when it caused a material
facet change, and record that change in the round's `material_changes`. Keep the
query log as provenance; findings still require real sources and passages in
`sources.jsonl` and `evidence.jsonl`.

After the final retrieval round, write the same stop decision to
`coverage.json.stop` and `run_manifest.json.retrieval_stop`. Its reason is
`coverage-saturated`, `budget-exhausted`, or `critical-error`; include the time,
round, basis, unresolved high-priority facet IDs, and remaining gaps. A budget
stop permits a qualified partial report with open gaps. Verify the saved
decision before packaging:

```bash
python scripts/verify_coverage.py --dir [folder]
```

The validator checks structure and references, not evidence relevance or a
measured recall level. If outline refinement or critique reopens retrieval,
append the new `delta` queries and completed rounds, replace the earlier stop,
and validate again.

**Register each source as you encounter it:**
```bash
python scripts/citation_manager.py register-source \
  --json '{"raw_url": "...", "title": "...", "source_type": "academic", "year": "2024"}' \
  --dir [folder]
# Returns stable source_id (sha256-based, survives renumbering and continuation)
```

**Assign display numbers after all sources registered:**
```bash
python scripts/citation_manager.py assign-display-numbers --dir [folder]
# Maps stable source_ids to [1], [2], [3]... for rendering
```

Source identity is stable across edits and continuation. Display numbers are derived at render time, never stored in state. This survives context compaction and enables continuation agents to pick up citation state via stable IDs.

**Section sequence:**

1. **Executive Summary** (200-400 words)
   - Tool: Write(file, frontmatter + Executive Summary)
   - Track citations
   - Progress: "Executive Summary complete"

2. **Introduction** (400-800 words)
   - Tool: Edit(file, append Introduction)
   - Track citations
   - Progress: "Introduction complete"

3. **Finding 1-N** (600-2,000 words each)
   - Tool: Edit(file, append Finding N)
   - Track citations
   - Progress: "Finding N complete"

4. **Synthesis & Insights**
   - Novel insights beyond source statements
   - Tool: Edit(append)

5. **Limitations & Caveats**
   - Counterevidence, gaps, uncertainties, and unresolved high-priority facets
   - State the final retrieval stop reason and any budget-limited search gaps
   - Tool: Edit(append)

6. **Recommendations**
   - Immediate actions, next steps, research needs
   - Tool: Edit(append)

7. **Bibliography** (CRITICAL)
   - EVERY citation from citations_used list
   - NO ranges, NO placeholders, NO truncation
   - Tool: Edit(append)

8. **Methodology Appendix**
   - Research process, query families, coverage and verification approach
   - State the final stop reason, basis, completed rounds, and remaining gaps
   - Tool: Edit(append)

---

## File Organization

**1. Create dedicated folder:**
- Location: `~/Documents/[TopicName]_Research_[YYYYMMDD]/`
- Clean topic name (remove special chars, use underscores)

**2. File naming convention:**
All files use same base name:
- `research_report_20251104_topic_slug.md`
- `research_report_20251104_topic_slug.html`
- `research_report_20251104_topic_slug.pdf`

**3. Also save copy to:** `~/.claude/research_output/` (internal tracking)

---

## Word Count Per Section

**CRITICAL:** No single Edit call should exceed 2,000 words.

Example: 10 findings x 1,500 words = 15,000 words total
- Each Edit call: 1,500 words (under limit)
- File grows to 15,000 words
- No single tool call exceeds limits
