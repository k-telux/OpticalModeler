# Evidence contract

## Contents

1. Scope and lineage
2. Representative-to-global loop
3. Required evidence
4. Rule-compliance record
5. Fail-closed decisions

## Scope and lineage

- Freeze accepted revisions and build new corrections in a new directory.
- Any geometry, scene, export, report, or evidence write invalidates all dependent downstream checks.
- Record the user-command source, ruleset version/hash, generator hash, scene hash, and audit scope.
- Use `FULL_ACTIVE_RULE_REGRESSION` for whole-system PASS. Use `PARTIAL_SCOPED` for a delta-only audit.

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
- `PARTIAL/SCOPED`: the declared subset passes; no whole-system claim is allowed.
- `UNVERIFIED`: evidence cannot establish the claim.
- `BLOCKED`: a known rule fails.

Any stale hash, unresolved conflict, inconsistent status, missing P0 evidence, or unverified physical interface blocks a final release.
