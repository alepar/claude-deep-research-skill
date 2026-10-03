# Design review, round 1

Verdict: should-fix findings resolved.

- The first design lacked a per-claim support boundary. The spec now separates structural ID/support checks from semantic evidence review and qualifies claim section IDs by artifact.
- The first workflow placed delegation after retrieval. It now assigns bounded facet retrieval first, joins candidate evidence through the lead's canonical registry, then drafts dossiers.
- The continuation helper had no owner. Bead `claude-deep-research-skill-ts9.3` now owns it and its tests.

The tracked audit JSON exists; an initial absence report resulted from `rg --files` respecting a broad `*.json` ignore rule.
