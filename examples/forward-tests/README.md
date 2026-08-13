# Public-only forward tests

These four isolated tests used only the published `v1.0.0` Skill at peeled commit `048766250538f169d924c31bbdd39bf0c255c63f`, public primary literature, official manufacturer sources, and clean projectless workspaces. Independent review checked whether each package supported its own scoped verdict; a review PASS does not promote the modeled system to final PASS.

| ID | System | Gate | Scope | Final/release | Public reference |
|---|---|---|---|---|---|
| `n04-lightsheet` | 32-node remote-focus light-sheet path | `PASS` propagation gate | `PARTIAL_SCOPED` | `BLOCKED` | [workflow, locks, scripts, and sanitized renders](n04-lightsheet/README.md) |
| `interferometer` | 40-node multi-state free-space interferometer | `PARTIAL_SCOPED` | `PARTIAL_SCOPED` | `BLOCKED` | [repaired count-locked evidence package](interferometer/README.md) |
| `oct-clean-r2` | 22-role OCT representative smoke | `UNVERIFIED` | `PARTIAL_SCOPED` | `BLOCKED` | [directed topology and fail-closed smoke package](oct-clean-r2/README.md) |
| `cad-conversion-clean-r2` | Four-family Thorlabs CAD conversion smoke | `BLOCKED` | `PARTIAL_SCOPED` | `BLOCKED` | [binary-sanitized conversion package](cad-conversion-clean-r2/README.md) |

The matrix preserves the weakest applicable verdict. For example, the CAD package is clean enough to publish, but PDA100A2 still has an unbounded native bbox, failed deterministic meshing, and empty faces, so conversion remains `BLOCKED`.

## Reusable workflow

1. Pin the public Skill tag and peeled commit, then freeze literature, topology, CAD provenance, units, and licenses before geometry.
2. Represent every optical, guided-fiber, and electrical route as explicit directed edges with exact port IDs; do not synthesize reverse edges.
3. Replay the distributed lock script in a clean location and require normalized semantic equality before Blender generation.
4. Generate one representative assembly, reopen the saved Blend in a factory process, and verify world mesh, ports, zero-radius rays, BVH contact/collision, load path, and mesh cleanliness.
5. Propagate only the verified transform, then repeat saved-reopen and visual checks over all copies and neighboring assemblies.
6. Derive README and gate counts from evidence, sanitize every public file as bytes and by container metadata, rebuild manifests, and keep scoped blockers visible.

The machine-readable [RESULTS.json](RESULTS.json) is the status source for this index. The repository validator cross-checks it against the package evidence and manifests so stale prose, hidden binary metadata, and status promotion fail closed.

## Unified end-to-end replay

The four rows above remain historical isolated tests. They must not be stitched into one whole-system claim. The [`v1.0.1` N04 unified-ledger replay](../end-to-end-workflow/n04-v1.0.1-replay/README.md) applies the new one-run/one-writer/one-lineage contract to a single 32-node package and intentionally stops at `representative_smoke=UNVERIFIED` because the static public fixture excludes vendor CAD and the saved representative scene. Its [fresh-run runbook](../end-to-end-workflow/n04-v1.0.1-replay/RUNBOOK.md) provides the complete executable path without redistributing those binaries.
