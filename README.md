# Thorlabs Blender Optical Path Skill

[简体中文](README.zh-CN.md) · [日本語](README.ja.md)

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-111827)](https://agentskills.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Validation](https://github.com/k-telux/thorlabs-blender-optical-path/actions/workflows/validate.yml/badge.svg)](https://github.com/k-telux/thorlabs-blender-optical-path/actions/workflows/validate.yml)

An agent skill for turning 2D photonics schematics into physically auditable Blender optical tables. It treats optical topology, real apertures, manufacturer CAD, fasteners, load paths, fiber routing, and evidence lineage as hard gates—not decorative details.

> Unofficial community project. Not affiliated with or endorsed by Thorlabs, Inc. Product names are used only to identify compatible hardware. A rendered CAD assembly is not a mechanical, spectral, laser-safety, or experimental certification.

## 2D input → verified 3D example

| Original schematic input | Nature-style 3D output |
|---|---|
| ![2D G1/G2 schematic](examples/g1g2/input/fig_s17_componentlibrary_g1g2.png) | ![3D optical table](examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg) |

The public case study also includes an annotated top view and sanitized acceptance record. Vendor STEP/CAD files and the large laboratory Blend are intentionally excluded from Git.

## Install

With a compatible Agent Skills installer:

```bash
npx skills add k-telux/thorlabs-blender-optical-path
```

Or copy `skills/thorlabs-blender-optical-path` into your agent's skills directory.

## Use

Example prompts:

```text
Use $thorlabs-blender-optical-path to reconstruct this pump-probe schematic in Blender and produce a fail-closed physical audit.
```

```text
Audit this optical table for real post/load paths, centered apertures, beam clearance, fiber bend radius, and stale evidence.
```

The skill enforces a compact workflow:

1. map schematic nodes to experimental roles, real assets, ports, and support paths;
2. solve optical centers, surfaces, splitter planes, and branch continuity;
3. assemble hardware post-first from verified table holes;
4. prove one representative instance before propagation;
5. reopen the saved scene and run mesh/ray/BVH checks;
6. package visual, GLB, report, manifest, hash, and rule-compliance evidence consistently.

## Repository layout

```text
skills/thorlabs-blender-optical-path/   canonical English skill
i18n/zh-CN/                            Simplified Chinese skill edition
i18n/ja/                               Japanese skill edition
rules/                                 reusable project-memory template
examples/g1g2/                         sanitized 2D-to-3D case study
scripts/validate_repository.py         dependency-free release gate
```

The design uses the progressive-disclosure pattern seen in [Vercel's agent-skills](https://github.com/vercel-labs/agent-skills) and the composable, verification-first workflow style of [Superpowers](https://github.com/obra/superpowers). Detailed geometry and evidence rules live in references so the main `SKILL.md` stays small.

## Scope and limits

- Supports Blender-oriented planning, modeling, revision, audit, and publication rendering.
- Uses manufacturer CAD as an asset source, never as proof of correct assembly.
- Keeps optical rays, guided fiber, and electrical cables semantically distinct.
- Uses `PASS`, `BLOCKED`, `UNVERIFIED`, and `PARTIAL/SCOPED` as explicit evidence states.
- Does not redistribute third-party CAD or guarantee real-world hardware compatibility.

See [CONTRIBUTING.md](CONTRIBUTING.md) for rule proposals and case-study submissions.
