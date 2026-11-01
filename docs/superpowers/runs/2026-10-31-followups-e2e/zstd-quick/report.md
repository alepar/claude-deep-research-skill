# Research Report: zstd CLI compression levels and --ultra

## Answer

<!-- facet: F1 -->

The zstd CLI selects compression levels 1 to 19 with -#, and the default level is 3 [1]. <!-- claim: 63d5e68c05cd7117; evidence: 7f2669dfa7db19df; source: e27c2ce8a31091d2 -->
The --ultra flag unlocks levels 20 and above, up to a maximum of 22, at the cost of much more memory for both compression and decompression [1]. <!-- claim: 36f7acac017cc3aa; evidence: 0fc8d36535904fc5; source: e27c2ce8a31091d2 -->

Counterevidence to a simple "1 to 22" answer: the range also extends downward.
The --fast[=#] option switches to ultra-fast compression levels, where a higher value compresses faster at the cost of some compression ratio; without a value it defaults to 1 [1]. <!-- claim: 188686dbad9a4653; evidence: 6041f85f473de6c8; source: e27c2ce8a31091d2 -->
The Arch manual page [2] describes --fast the same way, but gives no numeric range for it.

## Limitations

Quick mode ran one retrieval round, so the stop is budget-exhausted, with no residual saturation probes. The high-priority facet F1 met readiness. The manual does not state a lower bound for `--fast=#`. Library-level (libzstd) limits were out of scope.

## Methodology

Tools: `search` CLI 0.12.2 for search (preflight ok) and `search -m extract` for the upstream manual. WebFetch read the Arch manual page for the supporting facet only. Two search attempts; both were partial (jina timed out, other providers answered), with 20 result entries considered. Two distinct original documents were read and no fetches failed. High-priority quotes are verbatim extract text.

### Retrieval health (retrieval_health.py output)

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

## Bibliography

[1] [zstd(1) manual, programs/zstd.1.md (facebook/zstd, dev branch)](https://github.com/facebook/zstd/blob/dev/programs/zstd.1.md)
[2] [zstd(1) - Arch manual pages](https://man.archlinux.org/man/zstd.1.en)
