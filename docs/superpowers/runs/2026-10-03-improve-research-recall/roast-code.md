# Code review — recall retrieval

Scope: branch diff from `main` through the three implementation children, reviewed against `spec.md`.

## Findings and resolution

- The first artifact review reproduced three defects: an empty initial-facet snapshot could pass saturation; query coverage changes could be hidden by empty round changes; malformed records could crash the CLI. Regression tests and validator fixes resolved each.
- The whole-branch review reproduced two further defects: a checked counterevidence state had no required query trail, and schema-required fields could be absent while validation returned `ok`. Regression tests and validator fixes resolved each.
- Re-review found an overly narrow counterevidence provenance rule: it rejected valid checks surfaced by literal or source-specific queries. The rule now accepts any query family when the query targets the facet and records the change in the same round. A regression test covers this case.

No remaining Blocking or should-fix finding was identified after these fixes. The review cannot assess empirical recall or whether a human selected relevant, independent sources correctly.
