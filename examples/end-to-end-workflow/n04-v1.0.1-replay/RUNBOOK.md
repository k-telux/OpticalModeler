# N04 whole-system runbook

This runbook is one ordered execution owned by one writer. It does not run independent track agents and does not merge separately generated scenes. Every output lives below one new `RUN_ROOT`, and every gate is recorded in the same hash-chain ledger.

## Prerequisites

- Blender 5.2 LTS or a compatible tested release.
- Python 3.12 with `cadquery-ocp==7.9.3.1.1` (the tested run reported OCP `7.9.3.1`); ordinary standard-library/OpenCV steps may use a separate active Python.
- Network access to the official URLs already frozen in `CAD_MANIFEST.json`.
- At least 2 GB of free working space. Official CAD, derived STL, and Blend files are private working artifacts and must not enter the public repository.

In PowerShell, define the three roots:

```powershell
$Repo = 'C:\path\to\OpticalModeler'
$RunRoot = 'C:\path\to\workflow_runs\n04_unified_new_revision'
$Blender = 'C:\Program Files\Blender Foundation\Blender 5.2\blender.exe'
$Workflow = Join-Path $Repo 'examples\end-to-end-workflow\n04-v1.0.1-replay'
$RepScripts = Join-Path $Workflow 'stage-scripts\representative'
$FullScripts = Join-Path $Repo 'examples\forward-tests\n04-lightsheet\scripts'
```

Create an isolated CAD runtime so its CPython 3.12 binaries cannot shadow the OpenCV runtime:

```powershell
$CadVenv = Join-Path $RunRoot 'work\runtime\cad-python'
py -3.12 -m venv $CadVenv
$CadPython = Join-Path $CadVenv 'Scripts\python.exe'
& $CadPython -m pip install 'cadquery-ocp==7.9.3.1.1'
& $CadPython -c "import OCP,sys; print(sys.version); print(OCP.__version__)"
python -c "import cv2,numpy; print(cv2.__version__, numpy.__version__)"
& $Blender --version
```

If any probe fails, stop before CAD conversion. Record the actual interpreter, package, and Blender versions in the run evidence; never combine a CPython 3.12 dependency directory with an incompatible Python process through a global `PYTHONPATH`.

Create the new revision and copy only public frozen inputs. Never copy a previous run's scene, derived meshes, evidence, events, or state:

```powershell
$Phase1 = Join-Path $RunRoot 'outputs\phase1_source_cad_topology_lock'
$RepMeasurements = Join-Path $RunRoot 'work\phase2_representative_smoke_r3\measurements'
New-Item -ItemType Directory -Force -Path $Phase1, $RepMeasurements | Out-Null
Copy-Item (Join-Path $Repo 'examples\forward-tests\n04-lightsheet\SOURCE_LOCK.json') $Phase1
Copy-Item (Join-Path $Repo 'examples\forward-tests\n04-lightsheet\TOPOLOGY_MAP.json') $Phase1
Copy-Item (Join-Path $Repo 'examples\forward-tests\n04-lightsheet\CAD_MANIFEST.json') $Phase1
Copy-Item (Join-Path $Workflow 'stage-inputs\REPRESENTATIVE_INPUT_LOCK.json') $RepMeasurements
Copy-Item (Join-Path $Workflow 'stage-inputs\CAD_NATIVE_PORT_LOCK.json') $RepMeasurements
```

The three JSON locks are not the complete source input. Materialize and verify every literature byte record declared by `SOURCE_LOCK.json` before recording `source_lock`:

```powershell
python (Join-Path $Workflow 'stage-scripts\fetch_source_lock_artifacts.py') $RunRoot
```

Create a new `RUN_SPEC.json` from this fixture's schema, set `workspace_root` and `revision_root` to the new run, keep `single_writer=true` and `allow_module_stitching=false`, then initialize an empty ledger:

```powershell
$Ledger = Join-Path $Repo 'skills\thorlabs-blender-optical-path\scripts\workflow_ledger.py'
python $Ledger init --spec (Join-Path $RunRoot 'RUN_SPEC.json') --state (Join-Path $RunRoot 'WORKFLOW_STATE.json') --events (Join-Path $RunRoot 'WORKFLOW_EVENTS.jsonl')
```

## Ordered execution

Run the following commands in order. Stop on the first nonzero exit code; do not start a downstream stage and do not edit a report to force PASS.

### 1. Public locks and private official CAD cache

```powershell
python (Join-Path $Workflow 'stage-scripts\fetch_official_cad.py') $RunRoot
python (Join-Path $Workflow 'stage-scripts\audit_live_cad_sources.py') $RunRoot
python (Join-Path $RepScripts 'verify_official_drawings.py') $RunRoot
python (Join-Path $Workflow 'stage-scripts\preflight_artifact_contract.py') $RunRoot
```

The fetcher tries only manifest-locked official URLs, verifies byte count and SHA-256 before atomic placement, and writes both the canonical filename and every `part_number__filename` consumer alias from the same verified bytes. The live-source audit independently streams the current official payloads without replacing the pinned cache; any drift blocks a current-catalog provenance PASS until a new run-specific lock and geometry audit are frozen. The drawing verifier writes to the filenames declared by `REPRESENTATIVE_INPUT_LOCK.json`. The preflight then checks all source files, 108 CAD consumer keys, and six drawing consumer keys before long CAD or Blender work. The cache is explicitly non-redistributable.

### 2. Representative N04 mechanical interface

```powershell
& $CadPython (Join-Path $RepScripts 'measure_representative_cad.py') $RunRoot
& $CadPython (Join-Path $RepScripts 'prepare_cad_meshes.py') $RunRoot
python (Join-Path $RepScripts 'clean_and_audit_stl.py') $RunRoot
python (Join-Path $RepScripts 'measure_sm1rc_clamp_lock.py') $RunRoot
& $Blender --background --python (Join-Path $RepScripts 'generate_representative_smoke.py') -- $RunRoot
$RepBlend = Join-Path $RunRoot 'work\phase2_representative_smoke_r3\scene\N04_representative_smoke_r3.blend'
& $Blender --background $RepBlend --python (Join-Path $RepScripts 'audit_reopened_smoke.py') -- $RunRoot
python (Join-Path $RepScripts 'opencv_audit.py') $RunRoot
python (Join-Path $RepScripts 'build_representative_params.py') $RunRoot
python (Join-Path $RepScripts 'finalize_public_package.py') $RunRoot
```

This gate must read the saved Blend. Its geometric split-gap readback comes from the reopened mesh; the elastic residual-gap calculation remains `UNVERIFIED_ANALYTIC_ESTIMATE` and is not a geometry PASS.

### 3. Deterministic 32-node whole scene

```powershell
python (Join-Path $FullScripts 'make_full_locks.py') $RunRoot
python (Join-Path $FullScripts 'verify_build_params_recompute.py') $RunRoot
& $CadPython (Join-Path $FullScripts 'prepare_full_cad.py') $RunRoot
python (Join-Path $FullScripts 'finalize_native_ports.py') $RunRoot
& $Blender --background --python (Join-Path $FullScripts 'generate_full_scene.py') -- $RunRoot
$GeneratedBlend = Join-Path $RunRoot 'work\full_32_node_propagation_v3\scene\FULL_32_NODE_PROPAGATION_v3.blend'
& $Blender --background $GeneratedBlend --python (Join-Path $FullScripts 'audit_reopened_full.py') -- $RunRoot
$AuditedBlend = Join-Path $RunRoot 'work\full_32_node_propagation_v3\scene\FULL_32_NODE_PROPAGATION_GATE_v3.blend'
& $Blender --background $AuditedBlend --python (Join-Path $FullScripts 'verify_and_render_gate.py') -- $RunRoot
python (Join-Path $FullScripts 'opencv_audit_full.py') $RunRoot
python (Join-Path $Workflow 'stage-scripts\finalize_whole_system_run.py') $RunRoot
```

The first reopen checks 32 nodes, 44 directed edges, ports, rays, BVH contacts, and support/load paths. The second reopen verifies serialized mesh cleanliness and renders nine views. The finalizer copies only a sanitized raster plus metadata to `public_candidate`; it excludes STEP/STL/Blend/archive files and scans for absolute private paths.

## Twelve ledger gates

Record a gate immediately after its required artifacts pass, using the same writer ID throughout:

| Order | Gate | Primary evidence |
|---:|---|---|
| 1 | `run_lock` | `RUN_SPEC.json` ownership and revision boundary |
| 2 | `source_lock` | `SOURCE_LOCK.json` |
| 3 | `topology_lock` | `TOPOLOGY_MAP.json` |
| 4 | `cad_provenance_lock` | `CAD_MANIFEST.json`, `CAD_FETCH_AUDIT.json`, drawing URL audit |
| 5 | `deterministic_replay` | build-parameter recompute readback |
| 6 | `representative_smoke` | saved representative Blend reopen audit |
| 7 | `full_scene_build` | generated whole-scene Blend and 54-file mesh audit |
| 8 | `saved_scene_reopen` | first full-scene reopen regression |
| 9 | `whole_system_optomechanical_audit` | second reopen, ports/rays/BVH/support/load paths |
| 10 | `visual_audit` | nine-render OpenCV audit and contact sheet |
| 11 | `export_and_sanitization` | public-candidate and PNG sanitization audits |
| 12 | `final_consistency` | cross-artifact hash/status report |

Example record call, repeated only for the current gate with a unique event ID and real timestamp:

```powershell
python $Ledger record --spec (Join-Path $RunRoot 'RUN_SPEC.json') --state (Join-Path $RunRoot 'WORKFLOW_STATE.json') --events (Join-Path $RunRoot 'WORKFLOW_EVENTS.jsonl') --writer-id 'n04-unified-single-writer' --stage 'source_lock' --status PASS_TO_NEXT_GATE --event-id 'n04-source-lock-001' --recorded-at '2026-08-13T00:00:00+08:00'
```

Finish by replay-validating the ledger:

```powershell
python $Ledger validate --spec (Join-Path $RunRoot 'RUN_SPEC.json') --state (Join-Path $RunRoot 'WORKFLOW_STATE.json') --events (Join-Path $RunRoot 'WORKFLOW_EVENTS.jsonl')
```

All stage gates may pass while `aggregate_status=PARTIAL_SCOPED` and `final_or_release=false`. That is expected for this N04 substitution build: literal paper performance, vendor-CAD redistribution, force/torque, and dynamic calibration remain blocked.
