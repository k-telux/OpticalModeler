<div align="center">

# OpticalModeler

**From 2D photonics schematics to physically auditable Blender optical tables.**

[![Validation](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml/badge.svg)](https://github.com/k-telux/OpticalModeler/actions/workflows/validate.yml)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/)
[![Blender](https://img.shields.io/badge/Blender-4.x-E87D0D?logo=blender&logoColor=white)](https://www.blender.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-2563EB.svg)](LICENSE)

<img src="examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg" width="100%" alt="Nature-style render of a physically audited G1/G2 optical table">

</div>

OpticalModeler is an evidence-first Agent Skill for reconstructing laboratory optical paths in Blender. It treats optical topology, real apertures, manufacturer CAD, fasteners, load paths, fiber routing, and artifact lineage as hard acceptance gates—not decorative details.

> **Independent community project.** Not affiliated with or endorsed by Thorlabs, Inc. Product names identify compatible hardware only. A rendered CAD assembly is not a mechanical, spectral, laser-safety, or experimental certification.

## Why OpticalModeler

| Physical assembly | Optical truth | Fail-closed evidence |
|---|---|---|
| Post-first placement, real table holes, fasteners, load paths, and supported hardware. | Centered apertures, splitter planes, branch continuity, internal fine beams, and fiber bend constraints. | Reopened-scene audits, ray/BVH checks, hashes, manifests, annotated renders, and explicit `PASS` / `BLOCKED` / `UNVERIFIED` states. |

## 2D input → verified 3D output

| Original schematic | Annotated 3D reconstruction |
|---|---|
| <img src="examples/g1g2/input/fig_s17_componentlibrary_g1g2.png" width="100%" alt="Original G1/G2 schematic"> | <img src="examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg" width="100%" alt="Annotated top view of the reconstructed optical table"> |

The sanitized [G1/G2 case study](examples/g1g2/README.md) includes the original 2D input, editorial 3D renders, and a machine-readable acceptance record. Vendor STEP/CAD files and the large laboratory `.blend` are intentionally excluded.

## Public-only forward tests

Four isolated tests started from the published `v1.0.0` tag and used no private Optical Path guidance. They cover a 32-node light-sheet path, a 40-node multi-state interferometer, an OCT representative smoke, and a Thorlabs CAD conversion benchmark.

| Track | Accepted verdict | Reproduced failure |
|---|---|---|
| Light-sheet / N04 | Propagation `PASS`, model `PARTIAL_SCOPED`, release `BLOCKED` | Public lock replay drifted from the saved scene until semantic replay and explicit overrides were added. |
| Interferometer | `PARTIAL_SCOPED`, release `BLOCKED` | README/GATE duplicated stale ray and port counts instead of deriving them from reopen evidence. |
| OCT | `UNVERIFIED`, propagation blocked | Package integrity passed while first-hit and load-path evidence remained incomplete. |
| CAD conversion | `BLOCKED` | PNG metadata leaked local paths; after sanitization, a separate CAD meshing blocker correctly remained. |

The [forward-test matrix](examples/forward-tests/README.md) publishes the sanitized packages, marked workflow, generation log, reproducible scripts, exact status boundaries, and the cross-package validation contract. The table is a test record, not a claim that every system passed.

## Install

With a compatible Agent Skills installer:

```bash
npx skills add k-telux/OpticalModeler
```

Or copy `skills/thorlabs-blender-optical-path` into your agent's skills directory.

## Quick start
Send message below to your agent:

```text
Use $thorlabs-blender-optical-path to reconstruct this 2D schematic in Blender.
```

```text
Audit this optical table for real post/load paths, centered apertures, beam clearance, fiber bend radius, and stale evidence.
```

The skill guides the agent to:

1. map schematic nodes to experimental roles, real assets, ports, and support paths;
2. freeze exact directed topology and official-CAD provenance;
3. replay public lock scripts to the same normalized semantic parameters;
4. solve optical centers, surfaces, splitter planes, and branch continuity;
5. assemble hardware post-first from verified table holes;
6. prove one representative instance before propagation;
7. reopen the saved scene and run mesh, ray, BVH, and load-path checks;
8. derive public claims from evidence and scan binary/container metadata before packaging.

## Validation and limits

- Manufacturer CAD is an asset source, never proof of correct assembly.
- Free-space rays, guided fiber, and electrical cables remain semantically distinct.
- Whole-project success requires an active-rule compliance matrix; scoped evidence stays `PARTIAL/SCOPED`.
- The repository excludes third-party CAD, private paths, oversized Blend files, and unsupported real-world performance claims.
- Public scripts must replay the published semantic locks; prose counts must match saved-reopen evidence.
- Every release is checked for skill metadata, links, file size, ASCII/UTF-16 privacy leaks, forbidden CAD binaries, PNG metadata/CRC/decompression, manifest hashes, and acceptance-state consistency.

See [CONTRIBUTING.md](CONTRIBUTING.md) for rule proposals and case-study submissions, [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for retained literature licensing, and [SECURITY.md](SECURITY.md) for responsible disclosure.

Maintained by [telux](https://github.com/k-telux). Released under the [MIT License](LICENSE).
