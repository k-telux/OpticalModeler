# OpticalModeler 2.0: requests, correction loops, and final results

[English walkthroughs](WALKTHROUGHS.md) · [中文完整交互案例](WALKTHROUGHS.zh-CN.md) · [Canonical skill](../../skills/thorlabs-blender-optical-path/SKILL.md)

These six walkthroughs explain how to use the skill through a concrete final handoff, including a rejected layout and a blocked audit. The dialogues are edited teaching reconstructions grounded in project work and already public examples. They are not verbatim chat exports, new geometry runs, or blind forward-test results.

The recent laboratory-derived cases use functional aliases. Important instrument identities, exact installed geometry/operating parameters, private photographs, models, correspondence and identity maps are excluded. Output-image specifications describe the handoff, not a newly published laboratory image. The only apparatus images embedded here are the previously published G1/G2 previews.

## Choose a case

| Case | User goal | What the agent must settle | Final result and evidence boundary |
|---|---|---|---|
| A | Reconstruct a 2D schematic and deliver clear 3D views | Directed topology, real interfaces, support paths, editorial copy | Existing public G1/G2 input/output/evidence; historical verdict only. |
| B | Reconstruct a photographed apparatus on an accepted baseline | Installed versus candidate identity, complete beam branches, missing upright supports | Editable private review model, views, guide and measurement list; `PARTIAL_SCOPED`. |
| C | Move a lower branch under an upper platform without redesigning it | Fixed upper endpoint, rigid group vectors, permitted mirror/support changes, full footprint | Corrected private engineering/presentation package after intent rejection; no hardware qualification. |
| D | Reduce enclosure glare and improve beam readability | Actual shader ownership, protected optical surfaces, saved-state preservation | Separate presentation copy and fresh final images; inherited physical unknowns. |
| E | Add a proposed side detector and missing entrance shutter | Actual apertures, selector states, installed/proposed labels, unknown internals | Private selectable-port/shutter review package; modeled interfaces and physical limits explicit. |
| F | Finish a workflow whose audit or ledger evidence fails | Fresh report identity, valid event chain, affected-stage invalidation | Durable blocker/checkpoint or repaired software record; no fabricated model PASS. |

## An actual public input/output pair

The [2D input](../g1g2/input/fig_s17_componentlibrary_g1g2.png), [hero preview](../g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg), [annotated top preview](../g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg) and [sanitized historical acceptance](../g1g2/evidence/v18_nature_final_acceptance.json) are real published artifacts. The repository contains compressed previews rather than the original 16-bit masters or private editable scene.

![Previously published 2D G1/G2 input](../g1g2/input/fig_s17_componentlibrary_g1g2.png)

The schematic supplies roles and branch relationships; it does not itself prove mounting, optical alignment or unseen internal interfaces.

![Previously published G1/G2 final hero preview](../g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg)

The image shows the historical final presentation result. Its acceptance record stays bound to that historical scene; skill version 2.0 does not transfer that verdict to a different apparatus.

## Start your own task

State the operation, authoritative input/baseline, movable and protected scope, requested views/dimensions, and whether the result is private review or public release. Missing hardware facts can remain explicitly unknown in an authorized review candidate.

```text
Use $thorlabs-blender-optical-path to reconstruct my annotated photographs
on the accepted baseline. Preserve the original. Deliver one editable
optics-only review model, a readable overview/top view and interface close-ups,
plus assumptions and a laboratory measurement checklist. Distinguish installed,
candidate and proposed parts. Keep photographs, instrument identities and the
full scene private; do not claim physical qualification from render checks.
```

For a fresh design, replace the baseline instruction with "start from an empty scene and derive a new source-backed topology." For presentation only, state exactly which shaders, lights and cameras may change. A screenshot correction is translated into object families and measurable constraints before geometry.

## Evidence you should receive

An editable model and clear image are useful delivery artifacts. The accompanying record should name the actual saved-scene identity, changed/protected families, checked states, optical/neighbor/interface scope, image producers and final decoded dimensions, open questions and release authorization. A complete review package can be delivered without falsely closing unmeasured thread, preload, load, focal-plane or performance claims.

[CASE_INDEX.json](CASE_INDEX.json) records the cases' publication and claim boundaries. [MANIFEST.json](MANIFEST.json) binds the public teaching files, excluding itself. See [privacy workflow](../../skills/thorlabs-blender-optical-path/references/publication-privacy.md) for publication checks; the private redaction list and mapping are not distributed.
