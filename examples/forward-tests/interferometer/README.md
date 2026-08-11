# Full 40-node interferometer propagation

Status: `PARTIAL_SCOPED_FULL_40_NODE_PROPAGATION` — not final, not release, not publish.

This public metadata package propagates the frozen 40-role / 66-edge topology through a saved Blender factory-reopen audit. It contains no STEP, STL, Blend, render, or third-party CAD payload.

Key results:

- 40/40 canonical nodes and 66/66 topology edges are present.
- 30 official Thorlabs CAD families were SHA-locked and imported with per-file mm/inch unit binding; 158 placed official instances were read back.
- 497 CAD-derived port datums and all evaluated world bboxes were compared. SPDMH2 remains invalid BRep, so its agreement is numeric-bound-only.
- 32 per-state zero-radius ray objects (7 measurement-only, 6 lock-only, 14 combined lock+measurement, 5 calibration) and 166 modeled-proxy first hits passed saved-reopen readback. Vendor optical face identity remains unverified.
- 63/63 selected table holes passed scoped through-void classification; M6 thread identity and mechanical fits remain unverified.
- The complete BVH inventory contains 499 mesh objects, 309 included physical objects, 47586 candidate pairs, and 110 blocking collision pairs. Therefore mechanical propagation is not a PASS.
- Four private views passed OpenCV, but the images and Blend are excluded, so public visual re-verification is blocked.
- 633→810 phase mapping and paper performance equivalence remain `UNVERIFIED/BLOCKED`.

Files:

- [Topology contract](topology/FULL_TOPOLOGY_CONTRACT.json)
- [Root lock](evidence/ROOT_LOCK.json)
- [OCCT CAD audit](evidence/OCCT_CAD_AUDIT.json)
- [Build evidence](evidence/BUILD_EVIDENCE.json)
- [Factory reopen audit](evidence/FACTORY_REOPEN_AUDIT.json)
- [Table-hole audit](evidence/TABLE_HOLE_AUDIT.json)
- [OpenCV private attestation](evidence/OPENCV_PRIVATE_ATTESTATION.json)
- [Scope/status matrix](SCOPE_STATUS_MATRIX.json)
- [Stage gate](FULL_40_NODE_PROPAGATION_GATE.md)
