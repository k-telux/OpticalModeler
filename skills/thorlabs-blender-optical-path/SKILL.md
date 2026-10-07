---
name: thorlabs-blender-optical-path
description: Design, reconstruct from photographs or schematics, correct, audit, and present Blender optical systems using provenance-bound CAD and measured optical and mechanical interfaces. Use for optics-only laboratory models, constrained revisions, stateful instruments, and publication renders with explicit evidence and privacy boundaries.
metadata:
  version: "2.0.0"
---

# OpticalModeler 2.0 — Thorlabs Blender Optical Path

Turn a measurement requirement, schematic, or photographed apparatus into an editable, explainable Blender scene. Deliver the requested model and views with evidence that matches the claim. Manufacturer geometry, installed identity, visual readiness, and physical qualification are separate facts.

## Load the relevant references

- Read [physical-gates.md](references/physical-gates.md) before geometry, CAD placement, or mechanical review.
- Read [evidence-contract.md](references/evidence-contract.md) before declaring any PASS or preparing a release.
- Read [history-derived-rules.md](references/history-derived-rules.md) when revising an existing scene or when old fixes may have regressed.
- Read [project-case-study.md](references/project-case-study.md) for the complete G1/G2 2D-to-3D example.
- Read [fresh-design-and-rendering.md](references/fresh-design-and-rendering.md) when the user requests a new measurement path, uses an old example as a quality reference, excludes electronics, or reports inadequate detail/beam visibility.
- Read [photo-reconstruction-and-revisions.md](references/photo-reconstruction-and-revisions.md) for photographed setups, constrained layout changes, repeated user corrections, or selectable ports/shutters.
- Read [presentation-and-delivery.md](references/presentation-and-delivery.md) for material/light changes, image reuse, interactive opening state, and final delivery.
- Read [publication-privacy.md](references/publication-privacy.md) before publishing laboratory-derived guidance or examples. Keep the private identity map outside the public tree.
- Read [end-to-end-workflow.md](references/end-to-end-workflow.md) before a whole-system build or large forward test. Use its single-run ledger instead of splitting one system into independently authored modules.
- Read [multi-run-qualification.md](references/multi-run-qualification.md) before a Skill release or scale/stress campaign that must compare multiple fresh whole-system runs.

Published detailed prompts, correction loops, and final handoffs: [six walkthroughs](https://github.com/k-telux/OpticalModeler/blob/v2.0.0/examples/v2.0/README.md), [English dialogues](https://github.com/k-telux/OpticalModeler/blob/v2.0.0/examples/v2.0/WALKTHROUGHS.md), and [中文交互案例](https://github.com/k-telux/OpticalModeler/blob/v2.0.0/examples/v2.0/WALKTHROUGHS.zh-CN.md). They are edited teaching examples, not raw conversations or a new qualification campaign.

## Authority and revision rules

1. Apply system constraints first, then the newest explicit user wording or annotated screenshot, then active project rules, then this general skill, and only then older artifacts or PASS labels.
2. Freeze submitted or accepted packages. Make corrections in an active revision without overwriting frozen evidence; group related fixes before submission instead of publishing a version for every preview.
3. Keep one writer, run ID, revision root, deterministic generator lineage, saved-Blend lineage, and workflow ledger for the whole system. Use helpers only as read-only reviewers unless an isolated non-shared asset scope is explicit; never stitch independently authored modules into a whole-system claim.
4. Translate every correction into object families, fixed and editable degrees of freedom, world-space geometry, a measurable gate, and required evidence before editing. "Make it compact" does not authorize changing the optical order, internal spacing, or an accepted upper endpoint.
5. Use `BLOCKED` or `UNVERIFIED` when real geometry or evidence is missing. File existence, imported CAD, process success, labels, AABB contact, and self-reported text are not proof.
6. Use existing evidence and photographs before asking a material question. If the user requests a complete review candidate before further measurements, finish that authorized candidate with explicit unknowns; do not invent hardware identity or call it physically qualified.
7. When helpers are authorized, assign isolated scopes and keep ordinary findings in a consolidated queue read at checkpoints. A moving build/render is not stalled. External messages, uploads, and publication require the user's authorization for those actions.

## Core workflow

First choose new measurement design, photograph/schematic reconstruction, constrained correction, presentation-only rerender, or audit-only work. Record which inputs are design authority, reusable assets, or visual references. A new measurement at an old example's quality starts from an empty scene. An explicitly retained reconstruction baseline can be reused read-only in a new revision. For optics-only requests, exclude electrical/data/circuit visualization while retaining optical detectors and their mechanical supports.

1. For a new whole-system build, initialize the run spec, state ledger, and append-only event hash chain with `scripts/workflow_ledger.py`. For a scoped correction, continue the existing lineage with a frozen input lock, declared change set, current evidence and delivery manifest; do not fabricate completion of pending whole-system stages.
2. Build a machine-readable map: `schematic node -> experimental role -> real asset -> optical/fiber/electrical ports -> support path`.
3. Inventory every directed edge, branch, optional/deferred node, component, beam segment, beam height, aperture, connector, and required detector endpoint. Never invent reciprocal edges.
4. Acquire official CAD only from manifest-locked manufacturer URLs into a private cache. Verify byte count and SHA-256 before atomic placement; record part number, source URL, unit scale, bbox, local optical axis, surface normal, aperture, provenance, and redistribution boundary. Mark modeled or surrogate parts explicitly and never publish vendor geometry without an explicit grant.
5. Treat each source lock and its hashed files as one atomic input bundle. Before geometry, run a producer-to-consumer artifact preflight: every locked source byte, canonical and part-qualified CAD cache key, official drawing, and required runtime must exist at the exact path/key used by the next script. Validate structured authority inputs as typed exact sets before lookup; missing, duplicate, extra, legacy, malformed, or identity-mismatched records must produce a durable structured `BLOCKED` result rather than an exception or silently collapsed entry.
6. Freeze deterministic source locks and replay them before geometry. Public-package scripts must reproduce their distributed normalized semantic parameters with zero unexplained field differences; encode every override in source with a reason. Private source/identity locks remain private unless separately authorized and curated. For multi-state systems, every edge has exact `active_states` or a hashed deterministic expansion, and every declared state has explicit ray templates.
7. Solve optical constraints first: centers, surface normals, reflection, splitting planes, branch endpoints, and zero-radius clearance. Keep design coordinates separate from measured reopened mesh/port witnesses; constant zero errors and endpoint-family matches cannot prove aperture or first-hit acceptance.
8. Solve mechanics post-first from verified table holes through real fasteners, clamps, holders, posts, mount faces, and device interfaces.
9. Fix the shared placement or transform root cause. Prove one representative repeated assembly inside the same run before propagation, then reopen and recheck every copy.
10. Render bright audit views before beauty views. Use cutaways or transparency only to expose hidden, already-measured interfaces.
11. For a whole-system claim, complete the applicable saved-scene, optomechanical, visual, export, derived-claim, sanitization, hash and rule-compliance gates in the same ledger. For a scoped correction/presentation, record current checks and exact preservation evidence while keeping missing whole-system gates pending.

Before final rendering, audit intent as well as geometry: retained relative vectors, exact mirror count and ordering, fixed endpoints, allowed support moves, and the actual requested footprint. Device centers inside a platform projection do not prove complete device/support coverage. Audit all changed-to-fixed and changed-to-changed neighbors, including fasteners owned by other nodes.

## Required semantic separation

- Treat free-space optical rays, guided fiber, and electrical/coaxial cables as different object families, materials, ports, and audit records.
- Terminate free-space light at the physical coupling surface; continue only the guided fiber from the ferrule/FC interface.
- Use open geometry for apertures and slits. A centered ray through an opaque disk is a collision, not a PASS.
- Remove duplicate surrogates and unexplained placeholders after the real or declared modeled assembly exists.
- Record installed/user-confirmed identity, candidate manufacturer identity, proposed installation, modeled geometry, and dimensional uncertainty separately. Redaction for publication never changes the private evidence or turns an alias into an official part.
- Treat unverified instrument internals as functional black boxes. Model real external openings and selected output states; two physical exits do not establish simultaneous splitting. Update evaluated transforms and visibility before each state audit.

## Publication rendering

Use low-cost diagnostic previews to review device detail, beam readability, and framing. Label physical gaps explicitly. A physical-qualified render follows its physical gates; an authorized manual-review or presentation package may be completed with those gaps disclosed and physical approval false. Use restrained metals, readable black-anodized edges, modest glass, thin beam cores, and uncluttered labels.

Preserve geometry, evaluated states, optical surfaces, beam centerlines/radii, material slots and polygon indices through presentation changes. Inspect actual shader ownership before darkening shared materials. Bind every image to its actual producer; reusing an unchanged image requires a preservation bridge and never a false fresh-render receipt. Inspect component close-ups and each branch. Verify decoded dimensions and bit depth; a 2K preview does not satisfy 4K delivery.

Once the requested checks pass, freeze one delivery. Publish only the separately authorized public scope. Recheck affected dependencies after a change, identity drift, or failed test; do not restart unchanged successful gates or open additional variants for optional polish. Skill documentation releases may record limitations without granting model-release credit; see [multi-run-qualification.md](references/multi-run-qualification.md).

## Completion language

- `PASS`: every applicable active gate has fresh evidence.
- `PARTIAL/SCOPED`: only a declared subset was audited; enumerate blockers and keep final/release approval false.
- `UNVERIFIED`: required evidence is missing or cannot distinguish the claim.
- `BLOCKED`: a known requirement fails.

`READY_FOR_USER_REVIEW` is a delivery milestone, not a replacement physical verdict. State which result is delivered, which checks ran, and which facts remain unknown. Show openable local artifacts as clickable links and the actual requested image when appropriate. If the rendered final reply cannot be captured, report `reply_visual_confirmation=incomplete`; source Markdown alone does not prove rendered links.

Never promote `PARTIAL/SCOPED` to whole-system PASS.
