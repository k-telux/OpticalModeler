# Unified end-to-end workflow

## Purpose

Build one complete optical system through one run, one writer, one deterministic generator lineage, one saved-Blend lineage, and one machine-readable ledger. Stages are sequential evidence gates inside the run. Do not assign them to independent writers or claim completeness by stitching module packages.

Select the operation before initializing the run: new measurement design, reconstruction, scene correction, or presentation-only rerender. For a new design or optics-only scope, read [fresh-design-and-rendering.md](fresh-design-and-rendering.md). A diagnostic preview can help choose framing or detect missing detail, but cannot advance pending physical gates or claim final render quality.

## Run contract

Before source collection, freeze a `RUN_SPEC.json` using the `opticalmodeler.whole-system-run-spec.v1` schema and initialize `WORKFLOW_STATE.json` plus the append-only `WORKFLOW_EVENTS.jsonl` with `scripts/workflow_ledger.py`.

The spec must declare:

- one stable `run_id`, `writer_id`, workspace, and revision root;
- `mode=WHOLE_SYSTEM_END_TO_END`, `single_writer=true`, and `allow_module_stitching=false`;
- `require_claim_status=true` for new runs, so execution authorization and scientific/evidence claim scope cannot be conflated;
- the complete stage order and required frozen inputs or run outputs;
- `FULL_ACTIVE_RULE_REGRESSION` for a whole-system claim, otherwise `PARTIAL_SCOPED`;
- every required free-space, guided-fiber, electrical/data, return, spectrometer, and detector family that is in the declared system.

Declare excluded families too. An optics-only request excludes circuit and electrical/data visualization; retain the required optical detector bodies and their supports. Do not import an earlier example's electronics counts or topology as requirements for a new modality.

Record a gate only after its required artifacts exist, their SHA-256 values are captured, and any declared JSON-pointer assertions match. Use those assertions to bind a gate to machine-readable verdicts instead of hashing a report whose contents contradict the recorded PASS. The script rejects another writer, an out-of-order gate, a changed recorded artifact, a failed assertion, an output outside the revision, a broken event hash chain, or a state file that differs from event replay.

Run schema, authority, import-boundary, and failure-path fixtures only in a disposable fixture root. They must not write canonical stage outputs. If a pre-gate fixture touches a canonical output, preserve or quarantine the bytes as `FIXTURE_ONLY_UNCREDITED`, record the activity truthfully, invalidate dependent credit, and require a fresh authorized stage run to recreate the canonical artifact.

## Stage order

1. `run_lock`: freeze the run contract, public/private boundary, baseline, writer, units, coordinate frame, and complete requested scope.
2. `source_lock`: freeze primary literature or the user-authoritative schematic, attribution/license, files, hashes, and any unresolved source identity. Materialize every declared file as one atomic input bundle; a sanitized derivative with a different byte hash does not replace the frozen source record.
3. `topology_lock`: map every node, directed port edge, branch, signal family, endpoint, optional/deferred node, and support requirement. For a multi-state system, require exact per-edge state membership and explicit ray templates for every state, or a hashed deterministic expansion replay.
4. `cad_provenance_lock`: freeze official product/CAD URLs, part numbers, native units, hashes, licenses, model status, semantic ports, and substitutions. Fetch only those locked URLs into the private run cache, verify byte count and SHA-256 before atomic placement, keep redistribution blocked unless an explicit grant is recorded, and run a producer-to-consumer preflight over exact cache aliases and drawing paths before geometry.
5. `deterministic_replay`: recompute normalized semantic build parameters from frozen inputs and published source with zero unexplained field differences.
6. `representative_smoke`: use the final generator to build and reopen one repeated assembly; prove mesh, port, ray, BVH, contact, fastener, actual link-mesh endpoints, and load-path gates. Give each audit attempt a unique nonce and fresh report/commit identity; runtime success without a matching fresh report, audited-Blend commit, and required second reopen is a failed attempt. For repeated stations, derive root spacing from the representative reopened aggregate bbox plus a declared margin before propagation.
7. `full_scene_build`: propagate only the verified transform with the same generator and inputs; create the complete declared topology in one scene.
8. `saved_scene_reopen`: reopen the saved Blend in a factory process and re-read world meshes, transforms, ports, zero-radius rays, BVH, contacts, load paths, mesh cleanliness, and every repeated instance.
9. `whole_system_optomechanical_audit`: check every branch and signal family end to end, global neighbor collisions, apertures, fibers/cables, instruments, table holes, and active-rule coverage.
10. `visual_audit`: render bright whole-table, side/oblique, axial, and cutaway evidence; run role-specific OpenCV or equivalent checks without treating visibility as physical proof.
11. `export_and_sanitization`: reimport delivered GLB when applicable, scan all bytes and containers, strip public-copy metadata safely, exclude unlicensed CAD, and rebuild hashes/manifests.
12. `final_consistency`: derive prose/counts/status from machine evidence and require agreement across ledger, audits, README/PDF, manifest, and user-facing summary.

`PASS_TO_NEXT_GATE` authorizes only the next stage; its `claim_status` may still be `PARTIAL_SCOPED`. The ledger emits whole-run `PASS` and `final_or_release=true` only after all twelve gates execute successfully under `FULL_ACTIVE_RULE_REGRESSION` and every claim status is `PASS`. A completely executed or scientifically scoped run remains aggregate `PARTIAL_SCOPED` with `final_or_release=false`. `BLOCKED`, `UNVERIFIED`, or any pending stage also keeps `final_or_release=false`.

## Representative smoke is not a module

The representative scene is an internal transaction in the same run. It must use the same frozen source/topology/CAD locks, generator code, semantic-port rules, units, and writer as full propagation. A separate helper-generated assembly, manually moved copy, or imported PASS report cannot authorize propagation.

## Invalidation

Any write to a frozen input, generator, auditor, runtime helper, scene, export, audit, or derived report invalidates that gate and every downstream gate. For a planned change, run `workflow_ledger.py invalidate` before writing, then rerun the affected source/static/runtime fixtures, regenerate the dependent artifacts, and record new events. If drift is discovered after a file changed, the invalidate command permits recovery only when every recorded artifact before the requested invalidation point still verifies; changed upstream evidence blocks the command. Never edit the state or event log by hand.

## Minimal commands

Run the canonical ledger with normal Python. It refuses `-O`, `-OO`, and `PYTHONOPTIMIZE` because those modes remove its assertion-based contract checks; disabling validation is not a supported speed optimization.

```text
python scripts/workflow_ledger.py init --spec RUN_SPEC.json --state WORKFLOW_STATE.json --events WORKFLOW_EVENTS.jsonl
python scripts/workflow_ledger.py record --spec RUN_SPEC.json --state WORKFLOW_STATE.json --events WORKFLOW_EVENTS.jsonl --writer-id <writer> --stage run_lock --status PASS_TO_NEXT_GATE --claim-status PASS --event-id E001 --recorded-at <RFC3339>
python scripts/workflow_ledger.py invalidate --spec RUN_SPEC.json --state WORKFLOW_STATE.json --events WORKFLOW_EVENTS.jsonl --writer-id <writer> --stage topology_lock --event-id E009 --recorded-at <RFC3339> --reason <reason>
python scripts/workflow_ledger.py validate --spec RUN_SPEC.json --state WORKFLOW_STATE.json --events WORKFLOW_EVENTS.jsonl
```

Use explicit event IDs and timestamps from the run log; the tool does not synthesize volatile time values.
