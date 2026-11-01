### Retrieval health

**Status: DEGRADED.** 1 provider failure type(s) reduced search coverage.

- Search preflight: ok (search) - search 0.12.2; first query partial_success (jina timeout), other providers returned results
- Search attempts: 2 (2 partial)
- Document fetches: 2 attempts, 2 distinct documents read, 0 failed attempts, 0 recovered, 0 still inaccessible
- High-priority quotes: 2 (2 verbatim from search -m extract, 0 non-verbatim fallback, 0 provenance unknown)
- Claim support check: model; 3 claim(s) judged by model (claude-sonnet-5-5), 0 unverified by model

Provider failures (search still returned results from other providers):

| Provider | Category | Queries affected |
|---|---|---|
| jina | timeout | 2 |

Recommended actions:

- **timeout** (provider jina): Transient timeout: rerun the affected queries or fetches.
