# RocksDB default block cache size

**Finding:** RocksDB uses an LRU-based block cache with 32MB capacity out of the box, and 8MB before version 8.2, per its wiki. A secondary article's 8MB figure matches the older default. Configure it by passing a `Cache` object with the desired capacity.

This run exists to test provider-signal marks end to end. It is not a thorough answer.

## Method

Tool: search CLI; two queries, 20 result entries considered, two documents read (one `search -m extract`, one WebFetch). jina timed out on the first query.

## Retrieval health

See health.md.
