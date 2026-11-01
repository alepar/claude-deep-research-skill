### Retrieval health

**Status: DEGRADED.** 1 provider failure type(s) reduced search coverage.

- Search preflight: ok (search) - search 0.12.2 (signal/integration build); first query partial_success, jina timeout
- Search attempts: 2 (1 partial, 1 success)
- Document fetches: 2 attempts, 2 distinct documents read, 0 failed attempts, 0 recovered, 0 still inaccessible
- High-priority quotes: 0 (0 verbatim from search -m extract, 0 non-verbatim fallback, 0 provenance unknown)

Provider failures (search still returned results from other providers):

| Provider | Category | Queries affected |
|---|---|---|
| jina | timeout | 1 |

Recommended actions:

- **timeout** (provider jina): Transient timeout: rerun the affected queries or fetches.
