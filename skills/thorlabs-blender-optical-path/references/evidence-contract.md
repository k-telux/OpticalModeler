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

## Source-to-artifact replay

- Recompute every published lock and semantic build parameter from the distributed scripts and frozen inputs before scene generation.
- Canonicalize only declared volatile fields such as a generation timestamp. Require normalized semantic hashes to match and the field-difference list to be empty.
- Put every manual exception, port-center override, substitution, and no-snap policy in source with its reason. A hand-edited lock or unlogged transform blocks propagation even when its manifest hash is correct.
- Run replay in a clean location with bytecode/cache writes disabled or excluded, then prove the package file set is unchanged.

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
- zero-radius optical-axis and first-opaque-hit checks;
- narrow-phase BVH with allowed contact envelopes separated from illegal collision;
- close-up mechanical views and complete table views;
- role-specific OpenCV or equivalent visual checks;
- empty-scene GLB reimport when GLB is delivered;
- readable PDF/README, manifest, and independently checked hashes;
- status agreement across all artifacts.

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
