# Evidence contract

## Contents

1. Scope and lineage
2. Source-to-artifact replay
3. Representative-to-global loop
4. Required evidence
5. Derived claims and status
6. Public-package sanitization
7. Rule-compliance record
8. Fail-closed decisions

## Scope and lineage

- Freeze accepted revisions and build new corrections in a new directory.
- Any geometry, scene, export, report, or evidence write invalidates all dependent downstream checks.
- Record the user-command source, ruleset version/hash, generator hash, scene hash, and audit scope.
- Use `FULL_ACTIVE_RULE_REGRESSION` for whole-system PASS. Use `PARTIAL_SCOPED` for a delta-only audit.
- Keep one whole-system run, writer, generator/Blend lineage, and event-hashed ledger from source lock to package. Independently authored module packages cannot be stitched into a whole-system PASS.
- Keep stage execution authorization separate from claim status. A gate may execute successfully while its scientific/provenance claim remains `PARTIAL_SCOPED`; final authorization requires every applicable claim status to be `PASS`.

## Source-to-artifact replay

- Recompute every published lock and semantic build parameter from the distributed scripts and frozen inputs before scene generation.
- Canonicalize only declared volatile fields such as a generation timestamp. Require normalized semantic hashes to match and the field-difference list to be empty.
- Put every manual exception, port-center override, substitution, and no-snap policy in source with its reason. A hand-edited lock or unlogged transform blocks propagation even when its manifest hash is correct.
- Run replay in a clean location with bytecode/cache writes disabled or excluded, then prove the package file set is unchanged.
- Verify the complete source-lock byte set and every producer-to-consumer path/key before long-running conversion or Blender work. A stage-local PASS is invalid when the next declared consumer cannot resolve the artifact.
- Treat every authority bundle and cross-file evidence join as a typed exact-set contract. Count roles and compound identities before constructing lookup maps; reject missing, duplicate, extra, legacy, malformed, non-finite, out-of-range, or mismatched records with reason-coded structured `BLOCKED` evidence. Do not let `next(...)`, direct indexing, or dictionary collapse turn contract failures into exceptions or lost duplicates.
- Validate evidence at the trust boundary before arithmetic or geometry. Require explicit string, hash, positive-byte, finite-number, vector, and index constraints as applicable, and derive polygon count, surface area, normal, and contact witnesses from the reopened object rather than trusting copied lock fields.
- When an embedded runtime loads an adjacent audit helper, bind the executable and helper to exact path, bytes, SHA-256, and actual loaded-module identity. Exercise that boundary from a clean working directory/environment in the real target runtime; a host-Python import or compile check alone is scoped evidence.
- For multi-state topology, bind every edge and zero-radius ray template to exact active states or to a versioned, hashed expansion script; structural node/edge counts alone are scoped diagnostics, not topology PASS.

## Representative-to-global loop

1. Fix the shared placement/transform root cause.
2. Validate one representative repeated assembly with real mesh, section, ray, and BVH evidence.
3. Inspect a side/oblique load-path view plus a bright axial/cutaway view.
4. Propagate only the verified transform.
5. Reopen the saved scene and recheck every copy plus global neighbor collisions.

## Required evidence

- machine-readable topology and role inventory;
- official/modeled/surrogate provenance with hashes and unit scale;
- saved-Blend reopen and world-space transform/mesh readback;
- actual reopened filepath plus opened-file SHA-256; a hash of the expected path is insufficient when another Blend may be open;
- zero-radius optical-axis and first-opaque-hit checks;
- measured endpoint/surface witnesses, separate from target coordinates; expected object-family hits or literal zero error fields are not sufficient;
- narrow-phase BVH with allowed contact envelopes separated from illegal collision;
- close-up mechanical views and complete table views;
- role-specific OpenCV or equivalent visual checks;
- declared final output resolution and bit depth read from delivered images; per-branch visibility evidence rather than only whole-frame edge/color statistics;
- empty-scene GLB reimport when GLB is delivered;
- readable PDF/README, manifest, and independently checked hashes;
- status agreement across all artifacts.

Treat each Blender audit attempt as a transaction with a unique nonce, start time, and attempt-specific report/commit paths. Process exit code zero is necessary but not sufficient: the fresh parseable report must bind the run, attempt, runtime, auditor/helper identities, and actual opened Blend path/bytes/SHA. Write the audited-Blend commit last, bind it to both the report and actual audited Blend, and verify it in a second clean reopen when that gate is required. A missing, stale, malformed, mismatched, or `BLOCKED` report is `BLOCKED_AUDITOR_EXECUTION_FAILURE`; a prior generation-only Blend cannot receive retrospective audit credit.

If the auditor cannot complete, write a structured failure report before returning a nonzero runtime exit whenever the output path remains writable. The failure report records the attempted identities and reason codes but grants no geometry or audit credit.

Do not substitute generator-time self-report, AABB-only overlap, process success, or a beauty render for these gates.

## Derived claims and status

- Derive README, gate, table, and summary counts from the same machine-readable evidence used by the validator. Do not maintain independent numeric literals.
- Assert exact record lengths, state distributions, status values, and release authorization across evidence, prose, and manifest. Reject stale superseded counts explicitly.
- For `PARTIAL_SCOPED`, publish the audited subset, every remaining blocker, and `final_or_release=false`. A valid scoped package may contain known blockers; it may not hide or neutralize them.

## Public-package sanitization

- Scan every file as bytes for absolute paths and isolation tokens, including ASCII, UTF-16LE, and UTF-16BE forms. A decode error or skipped binary is a failure, not zero findings.
- Parse container metadata. For PNG, validate signature, chunk bounds, CRCs, and decompression, and remove public-copy `tEXt`, `iTXt`, `zTXt`, and `eXIf` chunks unless an explicit reviewed allowlist requires one.
- When stripping PNG metadata, preserve `IHDR`, concatenated `IDAT`, and decoded scanline hashes; keep the private source immutable and rebuild every dependent hash and manifest.
- Keep sanitization status separate from geometry, CAD-conversion, mechanical, optical, and performance status.

## Rule-compliance record

```json
{
  "ruleset_version": "project ruleset id",
  "ruleset_sha256": "sha256",
  "latest_user_command_at": "timestamp or source turn",
  "audit_scope": "FULL_ACTIVE_RULE_REGRESSION",
  "rule_compliance": [
    {
      "rule_id": "MECH-POST-FIRST",
      "applicable": true,
      "verdict": "PASS",
      "evidence": ["relative/path/to/audit.json#field"],
      "notes": "measured result"
    }
  ],
  "unresolved_conflicts": []
}
```

The manifest repeats the ruleset, scope, rule-gate status, conflicts, and artifact hashes.

## Fail-closed decisions

- `PASS`: every applicable active rule has fresh, independent evidence.
- `PARTIAL/SCOPED`: the declared subset passes, its blockers are enumerated, and no whole-system or release claim is allowed.
- `UNVERIFIED`: evidence cannot establish the claim.
- `BLOCKED`: a known rule fails.

Any stale hash, unresolved conflict, inconsistent status, missing P0 evidence, or unverified physical interface blocks a final release.

Here, final release means the physical model claim. A separately scoped Skill/documentation release may preserve incomplete or rejected examples as lessons, provided it states their limits and does not promote their verdicts. See [fresh-design-and-rendering.md](fresh-design-and-rendering.md) for fresh-design provenance and preview-specific traps.
