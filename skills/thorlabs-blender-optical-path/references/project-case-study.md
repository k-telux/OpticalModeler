# G1/G2 2D-to-3D case study

## Contents

1. Goal
2. Input topology
3. Reconstruction decisions
4. Evidence outcome
5. Limits

## Goal

Reconstruct a pump-probe, spectrometer, single-mode-fiber, g(1), and g(2) schematic as one physically continuous Blender optical table, then produce an editorial Nature-style render without changing verified geometry.

Public example files:

- 2D input: `examples/g1g2/input/fig_s17_componentlibrary_g1g2.png`
- 3D hero: `examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg`
- annotated top view: `examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg`
- sanitized acceptance: `examples/g1g2/evidence/v18_nature_final_acceptance.json`

## Input topology

- Probe: `Galvo -> L1 -> L2 -> BS_MAIN -> L3 -> BS_PICK -> DMLP -> OBJ100 -> Sample`
- Pump: `LA-ND -> SH -> CM2 -> CM1 -> AP -> CM3 -> M1 -> M2 -> DMLP -> OBJ100 -> Sample`
- Spectrometer: `collection plane -> PH -> BS_SPEC -> FELH -> slit -> internal redirect -> CCD2`
- Reflection/SMF: declared sample-return pickoff -> launch -> continuous SMF -> launch -> downstream optics
- g(1)/g(2): declared beamsplitter chain -> two SPAD optical endpoints -> two separate electrical/coaxial links to TCSPC

## Reconstruction decisions

1. Map every schematic node to a physical asset, port, optical anchor, and support chain.
2. Use real open apertures and measured face-port centers.
3. Build post-mounted hardware from verified table holes upward.
4. Model each MBT objective and FC/fiber chain as one continuous optical/mechanical family.
5. Distinguish optical rays, fiber jackets, and electrical cables in geometry and color.
6. Prove slit-to-internal-mirror-to-CCD2 continuity with a dedicated cutaway.
7. Freeze verified transforms and topology before editorial lighting, materials, camera, and annotation work.

## Evidence outcome

The sanitized final record reports:

- status `PASS_V18_NATURE_FINAL_VERIFIED`;
- Cycles, 96 samples;
- 4096×2304 16-bit master renders and 4096×3072 annotated output;
- unchanged render geometry signature;
- image QA PASS;
- saved-Blend reopen PASS;
- three of three independent publication reviewers PASS;
- zero P0 and P1 blockers.

## Limits

The repository does not ship the laboratory Blend or manufacturer CAD. The image pair demonstrates the workflow and evidence contract; it does not independently reproduce the scene, certify commercial hardware interfaces, or establish spectral performance.
