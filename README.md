# OpticalModeler

[English](README.md) · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) &nbsp; / &nbsp; [v2.0.0](https://github.com/k-telux/OpticalModeler/releases/tag/v2.0.0)

[Use Skill](skills/thorlabs-blender-optical-path/SKILL.md) &nbsp; [Cases](examples/v2.0/README.md) &nbsp; [Evidence](skills/thorlabs-blender-optical-path/references/evidence-contract.md)

<p>
<img src="assets/readme/wordmark.svg" width="100%" align="top" alt="OpticalModeler — Light. Structure. Evidence.">
<img src="assets/readme/formal-optics-detail.jpg" width="100%" align="top" alt="A fresh camera-rendered detail of mounted relay optics and existing optical paths from the formal saved model.">
</p>

<sub>A new view of the formal model. Apparatus layout and beam geometry retained; private instrument identities and scene files excluded.</sub>

**Design the path. Keep the evidence.**

OpticalModeler is an Agent Skill for turning measurement ideas, diagrams and photographed setups into editable Blender optical systems. It connects the optical route to real apertures, mounts and support paths, then keeps the saved scene, checks and final views tied to the same result.

---

## 01 / Start with your intent

Install with a compatible Agent Skills installer:

`npx skills add k-telux/OpticalModeler`

Then give your agent the input, what may change, and what you need back:

```text
Use
$thorlabs-blender-optical-path
to reconstruct these photos
on the accepted baseline.
Keep the original files.
Keep fixed upper endpoints.
Deliver an optics-only model,
final views and a checklist.
Mark installed, candidate
and proposed parts.
```

Prefer a manual install? Copy [the skill folder](skills/thorlabs-blender-optical-path) into your agent's skills directory.

## 02 / Choose the work, preserve its boundaries

| Your goal | Where the work begins |
|---|---|
| **Design** a new measurement | An empty scene, a source-backed topology and permitted component assets. |
| **Reconstruct** a diagram or photographs | Authoritative inputs and an explicitly retained baseline. |
| **Correct** an accepted model | Frozen originals, protected families and declared movable degrees of freedom. |
| **Audit** an existing scene | Read-only evidence, actual saved geometry and precise findings. |
| **Present** the accepted result | A separate camera/light copy with geometry and image provenance preserved. |

Keep a fixed upper endpoint fixed. Move an optic with its mount and supports. Treat a proposed camera as proposed. A clearer render supports presentation; it does not close an unknown physical interface.

## 03 / From request to final handoff

Six conversations show the decisions that matter, including rejection, correction and the final output:

- **A — Diagram to scene.** [Follow the complete reconstruction](examples/v2.0/WALKTHROUGHS.md#a-from-a-public-2d-schematic-to-the-delivered-3d-presentation), with real public input, final previews and historical evidence.
- **B — Photos with missing specifications.** [Deliver a usable review model](examples/v2.0/WALKTHROUGHS.md#b-photograph-reconstruction-with-unknown-hardware-details) while keeping installed identity and estimates separate.
- **C — A compact layout, without redesign.** [Follow a rejected layout through correction](examples/v2.0/WALKTHROUGHS.md#c-a-compact-layout-request-that-must-survive-user-rejection), retaining internal vectors and fixed endpoints.
- **D — Better light, same instrument.** [Create a verified presentation copy](examples/v2.0/WALKTHROUGHS.md#d-darker-enclosures-and-readable-beams-without-geometry-drift), with fresh images and unchanged scientific geometry.
- **E — One entrance, selected exits.** [Model a proposed detector and shutter states](examples/v2.0/WALKTHROUGHS.md#e-a-proposed-detector-two-selected-exits-and-an-entrance-shutter) without inventing internal transfer.
- **F — A process exits; evidence is missing.** [Produce an honest recovery handoff](examples/v2.0/WALKTHROUGHS.md#f-audit-failure-and-ledger-rejection-still-produce-an-honest-result), with a valid record or reproducible blocker.

The laboratory-derived dialogues are edited, anonymized teaching reconstructions. Private photos, exact setup coordinates, important instrument SKUs and the full scene are not distributed. [Read the Chinese dialogues →](examples/v2.0/WALKTHROUGHS.zh-CN.md)

## 04 / Three things that stay connected

**The optical path.** Directed branches, actual working faces, apertures and detector endpoints. Free-space light and guided fiber keep distinct roles.

**The physical structure.** Real mounting interfaces, table holes, fasteners and continuous supports. Representative checks precede repeated placement; saved-scene checks cover the affected neighbors.

**The evidence.** One scene lineage, fresh reopen measurements, actual image producers and a consistent manifest. An execution success, source CAD and a well-framed picture each support their own claim.

[End-to-end workflow](skills/thorlabs-blender-optical-path/references/end-to-end-workflow.md) · [Photographed reconstruction](skills/thorlabs-blender-optical-path/references/photo-reconstruction-and-revisions.md) · [Presentation and delivery](skills/thorlabs-blender-optical-path/references/presentation-and-delivery.md)

## 05 / Know what the result establishes

| Status | What you can conclude |
|---|---|
| **PASS** | The declared applicable gates have current evidence. |
| **PARTIAL / SCOPED** | A stated subset is checked; remaining blockers and limits stay visible. |
| **UNVERIFIED** | Necessary evidence is missing or inconclusive. |
| **BLOCKED** | A known requirement fails. |

`READY_FOR_USER_REVIEW` means the requested handoff is ready for inspection. It does not certify installed hardware, thread preload, alignment, optical performance or laser safety. The cover is a presentation detail from an existing model, with its inherited physical limits preserved. [Image provenance](assets/readme/MANIFEST.json) · [Publication privacy](skills/thorlabs-blender-optical-path/references/publication-privacy.md)

<details>
<summary><strong>Explore the historical models and qualification results</strong></summary>

- [G1/G2: public schematic, final renders and sanitized historical acceptance](examples/g1g2/README.md). Compressed previews are available; private Blend and vendor CAD are excluded.
- [Single-run N04 workflow and replay](examples/end-to-end-workflow/n04-v1.0.1-replay/README.md). Static replay stops at `UNVERIFIED` where private assets are required.
- [Multi-run qualification](examples/end-to-end-workflow/qualification-v1.1.0/README.md). Scoped, blocked and unverified results remain distinct; there is no whole-system physical PASS.
- [MZI preview limitations](examples/fresh-design/mzi-preview/README.md). Constant zero errors, expected-family hits and small previews do not establish full acceptance.
- [Four public-only forward tests](examples/forward-tests/README.md). Historical discovery evidence, not modules to stitch into a new system.

</details>

<details>
<summary><strong>Validation, contribution and source boundaries</strong></summary>

`python scripts/validate_repository.py`

The validator checks skill editions, resources, manifests, historical verdicts, PNG metadata and runnable software checks. Keep a private identifier policy outside the repository when publishing laboratory-derived material; inspect pixels and container contents separately. See [privacy guidance](skills/thorlabs-blender-optical-path/references/publication-privacy.md).

[Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Security](SECURITY.md) · [Project-memory template](rules/OPTICAL_PATH_PROJECT_MEMORY_TEMPLATE.md)

</details>

---

Independent community workflow. Not affiliated with or endorsed by Thorlabs. English is the technical source; [Chinese](i18n/zh-CN/SKILL.md) and [Japanese](i18n/ja/SKILL.md) entries preserve its evidence rules.

Maintained by [telux](https://github.com/k-telux) · [MIT License](LICENSE)
