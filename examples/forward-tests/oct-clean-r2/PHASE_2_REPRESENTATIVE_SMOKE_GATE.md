# PHASE_2_REPRESENTATIVE_SMOKE_GATE

`PHASE_2_REPRESENTATIVE_SMOKE_GATE=UNVERIFIED`

- `audit_scope=PARTIAL_SCOPED`
- `whole_system_status=UNVERIFIED`
- `PRIVATE_CONTEXT_READS=0`
- `propagation_authorized=false`
- `public_vendor_cad_count=0`
- `public_derived_mesh_count=0`
- `public_blend_count=0`

## Representative closure

The frozen, unrewired subgraph contains 22 role nodes, 20 physical instances, 36 directed typed edges, and 7 paths. It includes all four main coupler connector frames, the sample round trip, both internal reference free-space branches and their returns, the custom spectrometer/camera endpoint, and the direct CMOS-to-computer `e52` baseline.

## Passed gates

- Frozen Phase 1: 10/10 payload hashes reverified; manifest SHA-256 `7513c352768915cb96c0161b842f04505af75b98cedab1f41d1259fd07ae8ce6`.
- Public checkout: annotated `v1.0.0`, detached/peeled commit `048766250538f169d924c31bbdd39bf0c255c63f`, clean.
- Runtime: Blender 4.5.12 LTS and OCCT/XCAF 8.0.1 archives/binaries hash-locked; real STEPCAF read passed.
- XCAF/Blender: 17 official CAD families, 52 evaluated instances, and 50 named ports passed the stated bbox/axis thresholds.
- Guided fiber: 6 physical runs representing 10 semantic edges passed endpoint, tangent, ≥30 mm bend-radius, and penetration checks.
- Electrical/data geometry: the sole `e52` route passed endpoints, tangents, bend radius, and penetration checks.
- Collision: 0 undeclared cross-assembly triangle-BVH overlaps.
- Saved Blend reopen: fresh factory-startup fingerprint matched.
- Visual: four bright views passed frozen OpenCV masks, projected-neighborhood checks, branch continuity, and PNG sanitization.

## Fail-closed limits

- Free-space first-hit audit: 9 PASS / 16 UNVERIFIED. Engineering-derived CAD ports do not prove vendor optical surfaces, and some mount bodies are hit first.
- Load paths: 8 PASS / 11 UNVERIFIED. Twenty of 141 narrow-phase interfaces remain above the 0.1 mm evidence threshold.
- Mesh cleanup is `PARTIAL_SCOPED`: preservation and safe cleanup were recorded, but several CAD-derived meshes remain non-manifold/open; watertightness is not claimed.
- Coupler connector geometry does not prove 50:50 behavior; NPBS central rays do not prove throughput; custom spectrometer connectivity does not prove spectral resolution.
- Connector standard/data performance and vendor-CAD redistribution permission remain `UNVERIFIED`.

No full-graph propagation is authorized. This gate stops here for coordination review.
