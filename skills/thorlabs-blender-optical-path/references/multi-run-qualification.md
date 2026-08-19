# Multi-run qualification

Use this mode when a Skill release, scaling change, or reusable workflow optimization must be supported by more than one optical-system run.

## Campaign boundary

- Keep one campaign coordinator and one scene writer per run.
- Give every iteration its own run ID, revision root, generator/Blend lineage, ledger, and verdict.
- Reuse only immutable public locks and source bytes that are reverified against the current run's manifest. Never reuse another run's derived meshes, Blend, audits, state, or PASS events.
- Increase a declared dimension such as topology/state coverage, station count, official instances, or strict physical gates. Repeating the same cached report is not another qualification run.
- Preserve each run's weakest status. Never average or stitch `PASS_SCOPED`, `PARTIAL_SCOPED`, `UNVERIFIED`, and `BLOCKED` into a whole-system PASS.

## Cross-run matrix

Derive a machine-readable matrix from the run authorities. At minimum record:

- source/topology/CAD lock hashes and live-versus-pinned identity;
- nodes, directed edges, signal states/families, official instances, load links, and scene size;
- mesh validity, saved-scene path/hash, reopen results, ports/rays/BVH/load paths, and visual/sanitization results;
- execution status, claim status, blockers, invalidations, retry count, ledger head, and final authorization;
- which defect or optimization repeated in at least two independent runs.

Only repeated general defects enter the durable Skill. Keep part numbers, numeric counts, collision pairs, timings, and view thresholds as fixtures unless the evidence establishes a general rule.

## Qualification priorities

1. Ledger truth: canonical stages, event replay, exact artifacts, and separate execution/claim status.
2. Input truth: atomic source bundle, exact producer-consumer keys, and independent live/cache/geometry/semantic/licensing axes.
3. Physical truth: representative coverage for every active support/load template, strict per-candidate BVH, exact allowed contacts, and bounded regeneration.
4. Reopen truth: actual opened filepath/hash plus normalized geometry/port/link signatures.
5. Topology truth: exact state membership and ray expansion when multi-state behavior applies.
6. Publication truth: role-specific visibility evidence, complete scoped context, byte/container sanitization, manifest-last build, and read-only postscan.

The retry budget is finite and declared in `RUN_SPEC`. Exhaustion produces a `BLOCKED` handoff with exact evidence; it never authorizes a blanket collision exemption or continued mutation.
