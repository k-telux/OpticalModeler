# Optical Path Project Memory

## Metadata

- Ruleset: `PROJECT-YYYY.MM.DD-r1`
- Updated: `YYYY-MM-DD timezone`
- Current revision: `revision-id`
- Frozen baseline: `revision-id or none`
- Current state: `BLOCKED | UNVERIFIED | PARTIAL_SCOPED | PASS`
- Governing skill: `thorlabs-blender-optical-path`

This file is the project-local source of truth. Register new user corrections here before or together with the next revision.

## Authority

1. System/developer constraints.
2. Newest explicit user wording or annotated screenshot.
3. Active project rules in this file.
4. General optical-path skill.
5. Older artifacts, audits, or PASS labels.

Preserve replaced rules as `superseded`; never silently delete history.

## Active rules

| Rule ID | Severity | Scope | Rule | Required evidence | Status |
|---|---|---|---|---|---|
| EXAMPLE-001 | P0 | all | Replace this row with one atomic rule. | JSON field and view path | active |

## Latest overrides

### YYYY-MM-DD / revision

- Add the newest user correction here.
- State which older rule or acceptance claim it supersedes.
- Keep one writer for shared geometry and freeze the old package.

## Required rule-compliance matrix

Every final audit records `ruleset_version`, `ruleset_sha256`, `latest_user_command_at`, `audit_scope`, `rule_compliance[]`, and `unresolved_conflicts[]`.

Whole-system PASS requires `FULL_ACTIVE_RULE_REGRESSION`. A delta-only audit is `PARTIAL_SCOPED`.

## Changelog

- `YYYY-MM-DD r1`: initialized project memory.
