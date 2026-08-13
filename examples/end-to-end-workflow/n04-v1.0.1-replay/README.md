# N04 unified-ledger replay

This fixture exercises the `v1.0.1` single-run workflow against the frozen public N04 light-sheet package. It is one read-only replay of one 32-node optical system, not a merger of the four historical forward-test tracks.

The ledger advances only through claims that the distributed package can independently support:

| Gate | Replay verdict | Reason |
|---|---|---|
| run lock | `PASS_TO_NEXT_GATE` | One run, writer, revision, stage order, and baseline are frozen. |
| source lock | `PASS_TO_NEXT_GATE` | The public package includes the open Dibaji et al. article/supplement lock, attribution, hashes, and topology source. |
| topology lock | `PASS_TO_NEXT_GATE` | The frozen map contains 32 nodes, 44 directed traversals, and two true branch points. |
| CAD provenance lock | `PASS_TO_NEXT_GATE` | Official URLs, native-unit/hash records, substitutions, and blocked redistribution are explicit. This does not certify literal paper performance. |
| deterministic replay | `PASS_TO_NEXT_GATE` | Normalized semantic parameters match with zero difference paths and zero unlogged transforms. |
| representative smoke | `UNVERIFIED` | The public package contains the frozen inputs, generator/audit scripts, and raster evidence, but deliberately excludes vendor CAD and the saved representative Blend. The public fixture therefore cannot independently reopen the scene. |
| downstream whole-scene gates | `PENDING` | They cannot be promoted past the first unverified physical gate. |

Accordingly, ledger integrity passes while aggregate status remains `UNVERIFIED` and `final_or_release=false`. This is the intended fail-closed result: a historical scoped propagation PASS is not silently converted into a fresh whole-system PASS.

Validate the fixture from the repository root:

```text
python skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py validate --spec examples/end-to-end-workflow/n04-v1.0.1-replay/RUN_SPEC.json --state examples/end-to-end-workflow/n04-v1.0.1-replay/WORKFLOW_STATE.json --events examples/end-to-end-workflow/n04-v1.0.1-replay/WORKFLOW_EVENTS.jsonl
```

For a new build, copy only the run-spec shape, point `RUN_OUTPUT` entries at the new revision, initialize an empty ledger, and generate every required artifact with the same writer and generator lineage. Do not copy this fixture's PASS events into another run.

The [whole-system runbook](RUNBOOK.md) is the executable path used by a fresh private revision. It fetches all 54 manifest-locked official STEP files into a private cache, runs the representative gate, builds and reopens the 32-node scene twice, renders nine audit views, sanitizes the public raster, and records all 12 gates in one ledger. Vendor CAD, derived meshes, and Blend files remain excluded from this repository.
