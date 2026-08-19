# Repeated-station qualification runbook

This profile scales one freshly generated and factory-reopened N04 station into a deterministic repeated-station scene. It validates topology namespace, saved-scene lineage, rigid transforms, station separation, serialization, visibility, and public sanitization. It does not by itself certify strict intra-station mechanics.

Use a fresh run root. Complete the base [N04 runbook](../n04-v1.0.1-replay/RUNBOOK.md) in the same run and with the same writer. Do not import another run's STL, Blend, audits, state, or events.

## Lock the array before geometry

After copying the three public Phase-1 JSON locks and representative input locks, materialize all external contracts:

```text
python ../n04-v1.0.1-replay/stage-scripts/fetch_source_lock_artifacts.py RUN_ROOT
python ../n04-v1.0.1-replay/stage-scripts/fetch_official_cad.py RUN_ROOT
python ../n04-v1.0.1-replay/stage-scripts/audit_live_cad_sources.py RUN_ROOT
python ../n04-v1.0.1-replay/stage-scripts/representative/verify_official_drawings.py RUN_ROOT
python ../n04-v1.0.1-replay/stage-scripts/preflight_artifact_contract.py RUN_ROOT
python scripts/build_array_lock.py RUN_ROOT --stations 2 --spacing-m 3.1 --clearance-margin-m 0.25 --run-id NEW_RUN_ID
python scripts/create_array_run_spec.py RUN_ROOT
python scripts/verify_array_lock_replay.py RUN_ROOT
```

The live CAD audit currently returns nonzero when any official payload differs from the pinned lock. Preserve that report and choose explicitly between a historical pinned-cache replay and a new current-live run-specific lock. Never overwrite a pinned hash silently.

Initialize the ledger. New specs use `require_claim_status=true`; every record command supplies both `--status` and `--claim-status`.

```text
python skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py init --spec RUN_ROOT/RUN_SPEC.json --state RUN_ROOT/WORKFLOW_STATE.json --events RUN_ROOT/WORKFLOW_EVENTS.jsonl
```

Record `run_lock`, `source_lock`, `topology_lock`, `cad_provenance_lock`, and `deterministic_replay` only after their exact artifacts pass. A current-live source drift may allow a declared scoped execution, but its claim status remains `PARTIAL_SCOPED` and `final_or_release=false`.

## Build one station, then scale

Run the representative and base 32-node build in the same run. The representative must pass its physical gates before propagation. Open the fresh base audited Blend and scale it:

```text
blender --background RUN_ROOT/work/full_32_node_propagation_v3/scene/FULL_32_NODE_PROPAGATION_GATE_v3.blend --python scripts/expand_array_scene.py -- RUN_ROOT
blender --background RUN_ROOT/work/array_scale/scene/N04_ARRAY_2x_GENERATED.blend --python scripts/audit_array_reopened.py -- RUN_ROOT
blender --background RUN_ROOT/work/array_scale/scene/N04_ARRAY_2x_AUDITED.blend --python scripts/verify_array_second_reopen.py -- RUN_ROOT
python scripts/opencv_audit_array.py RUN_ROOT
python scripts/finalize_array_run.py --run-root RUN_ROOT --repo REPOSITORY_ROOT
```

`expand_array_scene.py` refuses station spacing below the reopened aggregate X extent plus the locked margin. Both reopen scripts assert the actual opened Blend path and hash. The scale audit verifies namespaced nodes/edges, official instances, load links, shared mesh lineage, rigid translations, and cross-station separation.

## Strict whole-system gate

Before a physical whole-system claim, send every evaluated-world-mesh AABB candidate through narrow-phase BVH. There are no same-node, family, station, table, prefix, wildcard, or regex blanket exemptions. Each allowed overlap cites an exact object pair, interface/load-link proof ID, and numeric contact envelope.

If this strict audit is not present, record the whole-system claim as `PARTIAL_SCOPED` or `UNVERIFIED`. If any illegal pair remains after the finite run-spec retry budget, record `BLOCKED`, retain the exact pair list, and stop geometry mutation. The public 96-node fixture is intentionally blocked by this rule.

## Publication boundary

The finalizer publishes metadata plus a sanitized contact sheet only. Vendor geometry and Blend remain private. Visibility/OpenCV PASS cannot upgrade topology, physical, performance, provenance, licensing, or release status.
