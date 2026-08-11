
# Marked public workflow — full 32-node propagation gate

## 1. Immutable baseline and source lock — PASS

The annotated OpticalModeler tag is `v1.0.0`, peeled and checked out at `048766250538f169d924c31bbdd39bf0c255c63f`. The checked-out public skill entrypoint and its three linked public references are the sole domain rules. The frozen Phase 1 files were hash-checked before generation and again during packaging. N04 r3 was read-only and its accepted manifest hash is `76d3cafa4a60c7faee87b6e452bbf586fa7daf094ff778e6c950be97578fb862`.

## 2. Frozen literature topology — PASS with model scope PARTIAL_SCOPED

The reconstruction transcribes 32 optical nodes and 44 directed port traversals from Supplementary Figure 2: implementation of the pmRF into the detection path of the light-sheet microscopy, the supporting main schematic, and Methods. BR01 and BR02 are true branch points; N04-N06, N10-N14, N16-N22, N22-N24, and N25-N32 provide focusing/imaging relays; N32 is the camera endpoint. The exact 17 substitutions remain `PARTIAL_SCOPED`; literal paper performance remains `BLOCKED`.

## 2A. Deterministic lock-stage reconstruction — PASS

`make_full_locks.py` resolves N30 to `[0.7125, -0.55, 0.125]` m and N31 to `[0.9625, -0.55, 0.125]` m through explicit, reason-bearing optical-port-center overrides. These are not table-hole anchor centers and therefore do not pass through the integer-hole `snapped()` policy. `BUILD_PARAMS_RECOMPUTE_AUDIT.json` imports the published lock script without running its writer, recomputes all 32 node records from the frozen inputs, removes only `generated_utc`, and requires canonical semantic equality with the published `BUILD_PARAMS.json`. Both semantic hashes are `bfd80a07d0815f5079eff1a73ac591731bf357c1060d4649278de7d9bb52e3de`. `manual_unlogged_transforms` remains zero; the two overrides are separately counted and serialized.

## 3. Official CAD and native units — PASS

Fifty-four official STEP byte records were hash-joined to the frozen `CAD_MANIFEST.json`. Each was transferred at native unit scale with OpenCascade, measured in millimetres, triangulated, cleaned, and compared with its OpenCascade bbox. Blender imported millimetre coordinates and applied one explicit 0.001 scene transform. Every official instance was rechecked in world space. S4FC488 and S4FC637 stayed `PARTIAL_SCOPED` despite usable transferred geometry; their source diagnostics were never promoted to clean-source PASS.

## 4. CAD-native semantic ports — PASS

`CAD_NATIVE_PORT_LOCK_FULL.json` records the pre-placement native origin, axis, in/out ports, clear aperture, source STEP hash, and OpenCascade optimal bbox for every node. N04 alone uses the accepted r3 CAD-native optical interface. Other families inherit neither N04 placement nor N04 PASS.

## 5. Post-first mechanics and provenance — PASS at the propagation gate

Sixteen families were assembled independently. Official components retain exact current/cataloged identities. The N15 literature chamber and all joining fasteners/load witnesses are explicitly `MODELED_NON_THORLABS`; no all-official claim includes them. Four official drawings were byte/hash reverified and locked in `MECHANICAL_INTERFACE_LOCK.json`; drawing bytes are excluded.

## 6. Blender generation and N04 propagation — PASS

The generator creates the table/frame, 32 node assemblies, 44 presentation rays, labels, cameras, lights, and load witnesses without manual transforms or randomness. N04 preserves its accepted r3 local assembly and applies only one root yaw/translation to the frozen N04 topology port. Its official SM1RC/M-to-AC254-045-A-ML contact is recomputed in the full saved Blend, not inherited as a verdict.

## 7. Saved-Blend reopen regression — PASS

Blender 5.2.0 LTS reopened the generated Blend and recomputed 154 official instance bboxes/scales, all 387 used mesh objects backed by 287 serialized mesh datablocks, 32 native-port placements, 44 zero-radius edge rays, eight branch-ID groups, 156 load-link endpoint contacts, 16 family gates, and the N04 direct clamp contact. Every used mesh, including 156 load links, four frame links, 44 presentation beams, the N15 chamber, and audit markers, ended with zero non-triangular/duplicate/collinear faces. E042 traversed through the target plane and first hit N31 BB1-E02 at 4.920312 mm radial offset inside the 11 mm aperture. N24's stage had two independently recomputed load contacts while its paired controller remained excluded. The audited Blend was then reopened in a second factory session and the two critical gates were recomputed again.

## 8. Visual and OpenCV evidence — PASS for visibility only

Nine 1600×1000 evidence renders cover the overall perspective, axial top view, source launch, scanner relay, branch/remote relay, spectral detector, N04, N24 stage load path, and E042/N31 target. OpenCV checks dimensions, brightness, contrast, dynamic range, edges, overexposure, cyan component pixels, orange modeled-support pixels, and hash agreement with the second reopen. These checks prove evidence visibility, not paper performance.

## 9. Public-candidate sanitization — PASS

The package contains literature/2D references, frozen locks, manifests, distributable scripts, raster renders, audits, and hashes. It contains zero STEP/STL/Blend/vendor-drawing/runtime archives and no absolute private path. `MANIFEST.json` hashes every non-self-referential public artifact.

## Reproduction command order

Use a clean `<ROOT>` with the frozen Phase 1 and accepted N04 r3 public metadata staged at the paths named by the scripts. Fetch vendor files only from `CAD_MANIFEST.json`; verify every hash; do not redistribute them.

1. `python scripts/prepare_full_cad.py <ROOT>`
2. `python scripts/make_full_locks.py <ROOT>`
3. `python scripts/verify_build_params_recompute.py <ROOT>`
4. `python scripts/finalize_native_ports.py <ROOT>`
5. `blender --background --factory-startup --python scripts/generate_full_scene.py -- <ROOT>`
6. `blender --background --factory-startup <PRIVATE_GENERATED_BLEND> --python scripts/audit_reopened_full.py -- <ROOT>`
7. `blender --background --factory-startup <PRIVATE_AUDITED_BLEND> --python scripts/verify_and_render_gate.py -- <ROOT>`
8. `python scripts/opencv_audit_full.py <ROOT>`

Stop here. `FULL_32_NODE_PROPAGATION_GATE=PASS` is not final/release approval.
