# Changelog

All notable public workflow and evidence-contract changes are recorded here. Physical-system verdicts remain in their machine-readable example gates; a software/Skill version does not promote them.

## 1.1.0 — 2026-08-18

### Added

- Multi-run qualification across a 64-node N04 current-worktree run, isolated 96-node and 128-node N04 scale tests, and an isolated 40-node interferometer topology test.
- Source-lock artifact fetch with a commit marker written last, exact producer-to-consumer preflight, canonical plus part-qualified CAD cache keys, and official drawing output under the declared consumer filenames.
- Current-live CAD identity audit that does not overwrite historical pinned bytes. The dated qualification snapshot reports 53/54 pinned matches and one S4FC488 drift.
- Deterministic repeated-station lock/replay and scale scripts, reopened-mesh spacing preflight, two exact saved-scene reopen reports, OpenCV evidence, and sanitized qualification renders.
- Separate per-stage claim status support for new ledgers, including `PARTIAL_SCOPED` and `NOT_APPLICABLE` without release promotion.

### Hardened

- Whole-system ledgers now require the canonical twelve-stage order, current-stage equality during replay, exact recorded/spec artifact reconciliation, unique event IDs, timezone-aware nondecreasing RFC3339 timestamps, and fail-closed claim aggregation.
- Multi-state topology now requires exact edge `active_states` or a hashed deterministic expansion and explicit ray templates for every applicable state.
- Representative gates now require actual reopened link endpoints and load-path evidence; repeated-station spacing derives from reopened aggregate bounds plus a declared margin.
- Collision policy forbids same-node, family, station, table, prefix, wildcard, or regex blanket exemptions. Every broad-phase candidate requires narrow-phase classification; allowed contacts need exact interface/load-link evidence.
- Numeric physical gates use the strictest applicable user, primary-source, or manufacturer tolerance.

### Qualification verdicts

- 64-node N04: `PARTIAL_SCOPED`.
- 96-node N04: saved-scene/ports/rays/load-links/rigidity/separation/visual/sanitization passed, but whole-system physical status is `BLOCKED` by 15 measured illegal overlaps.
- 128-node N04: `PASS_SCOPED_SCALE_ONLY`, aggregate `PARTIAL_SCOPED`, `final_or_release=false`.
- 40-node interferometer: graph structure scoped PASS, topology `UNVERIFIED` because state membership and ray expansion are not source locked.
- Overall: no whole-system physical or release PASS.

## 1.0.1 — 2026-08-11

- Hardened evidence gates, sanitized four public forward-test packages, manifest/hash validation, and public-release transport checks.

## 1.0.0 — 2026-08-09

- Initial public Agent Skill and evidence-oriented optical-path examples.
