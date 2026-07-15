---
name: thorlabs-blender-optical-path
description: Build, audit, and revise physically plausible Blender optical-table figures from 2D schematics and manufacturer CAD. Use for Thorlabs-compatible mirrors, lens mounts, beamsplitters, posts, fiber launches, apertures, detectors, optical topology, fail-closed evidence, or Nature-style photonics renders.
---

# Thorlabs Blender Optical Path

Convert a 2D optical schematic into a physically explainable, independently auditable Blender scene.

## Load the relevant references

- Read [physical-gates.md](references/physical-gates.md) before geometry, CAD placement, or mechanical review.
- Read [evidence-contract.md](references/evidence-contract.md) before declaring any PASS or preparing a release.
- Read [history-derived-rules.md](references/history-derived-rules.md) when revising an existing scene or when old fixes may have regressed.
- Read [project-case-study.md](references/project-case-study.md) for the complete G1/G2 2D-to-3D example.

## Authority and revision rules

1. Apply system constraints first, then the newest explicit user wording or annotated screenshot, then active project rules, then this general skill, and only then older artifacts or PASS labels.
2. Freeze an accepted package. Start a new revision for every correction; never overwrite the prior evidence package.
3. Keep one writer for the shared Blender generator. Use helpers as read-only optical, mechanical, CAD, evidence, and visual reviewers unless an isolated write scope is explicit.
4. Translate every correction into object families, world-space geometry, a measurable gate, and required evidence before editing.
5. Use `BLOCKED` or `UNVERIFIED` when real geometry or evidence is missing. File existence, imported CAD, process success, labels, AABB contact, and self-reported text are not proof.

## Core workflow

1. Build a machine-readable map: `schematic node -> experimental role -> real asset -> optical/fiber/electrical ports -> support path`.
2. Inventory every branch, component, beam segment, beam height, aperture, connector, and required detector endpoint.
3. Acquire official CAD when licensing permits. Record part number, source URL, SHA-256, unit scale, bbox, local optical axis, surface normal, aperture, and provenance. Mark modeled or surrogate parts explicitly.
4. Solve optical constraints first: centers, surface normals, reflection, splitting planes, branch endpoints, and zero-radius clearance.
5. Solve mechanics post-first from verified table holes through real fasteners, clamps, holders, posts, mount faces, and device interfaces.
6. Fix the shared placement or transform root cause. Prove one representative repeated assembly before propagation, then reopen and recheck every copy.
7. Render bright audit views before beauty views. Use cutaways or transparency only to expose hidden, already-measured interfaces.
8. Complete the saved-scene, visual, export, document, hash, and rule-compliance gates in the evidence contract.

## Required semantic separation

- Treat free-space optical rays, guided fiber, and electrical/coaxial cables as different object families, materials, ports, and audit records.
- Terminate free-space light at the physical coupling surface; continue only the guided fiber from the ferrule/FC interface.
- Use open geometry for apertures and slits. A centered ray through an opaque disk is a collision, not a PASS.
- Remove duplicate surrogates and unexplained placeholders after the real or declared modeled assembly exists.

## Publication rendering

After physical gates pass, produce a clean editorial scene with restrained metals, readable black-anodized edges, physically modest glass, thin emissive beam cores, soft halos, and uncluttered labels. Preserve topology and geometry while changing camera, lighting, materials, or presentation. Nature-style appearance never replaces mechanical evidence.

## Completion language

- `PASS`: every applicable active gate has fresh evidence.
- `PARTIAL/SCOPED`: only a declared subset was audited.
- `UNVERIFIED`: required evidence is missing or cannot distinguish the claim.
- `BLOCKED`: a known requirement fails.

Never promote `PARTIAL/SCOPED` to whole-system PASS.
