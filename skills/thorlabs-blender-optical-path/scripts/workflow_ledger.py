#!/usr/bin/env python3
"""Maintain one fail-closed ledger for a whole optical-system build."""

from __future__ import annotations

# ponytail: preserve the existing assertion-based contract; refuse modes that erase it.
if not __debug__:
    raise RuntimeError("Optimized Python is unsupported: validation assertions must remain enabled.")

import argparse
import hashlib
import json
import re
from copy import deepcopy
from datetime import datetime
from pathlib import Path


SPEC_SCHEMA = "opticalmodeler.whole-system-run-spec.v1"
STATE_SCHEMA = "opticalmodeler.whole-system-workflow-state.v1"
EVENT_SCHEMA = "opticalmodeler.whole-system-workflow-event.v1"
PASS = "PASS_TO_NEXT_GATE"
STAGE_STATUSES = {"PENDING", PASS, "BLOCKED", "UNVERIFIED"}
CLAIM_STATUSES = {"PASS", "PARTIAL_SCOPED", "BLOCKED", "UNVERIFIED", "NOT_APPLICABLE"}
ZERO_HASH = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$")
CANONICAL_STAGES = (
    "run_lock",
    "source_lock",
    "topology_lock",
    "cad_provenance_lock",
    "deterministic_replay",
    "representative_smoke",
    "full_scene_build",
    "saved_scene_reopen",
    "whole_system_optomechanical_audit",
    "visual_audit",
    "export_and_sanitization",
    "final_consistency",
)


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"expected JSON object: {path}"
    return value


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    temporary.replace(path)


def inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def roots(spec_path: Path, spec: dict[str, object]) -> tuple[Path, Path]:
    workspace = (spec_path.parent / str(spec["workspace_root"])).resolve()
    revision = (workspace / str(spec["revision_root"])).resolve()
    assert inside(revision, workspace), "revision_root escapes workspace_root"
    return workspace, revision


def validate_spec(spec_path: Path, spec: dict[str, object]) -> list[dict[str, object]]:
    assert spec.get("schema") == SPEC_SCHEMA
    assert spec.get("mode") == "WHOLE_SYSTEM_END_TO_END"
    assert isinstance(spec.get("run_id"), str) and spec["run_id"]
    assert isinstance(spec.get("writer_id"), str) and spec["writer_id"]
    assert spec.get("single_writer") is True
    assert spec.get("allow_module_stitching") is False
    assert spec.get("audit_scope") in {"FULL_ACTIVE_RULE_REGRESSION", "PARTIAL_SCOPED"}
    assert isinstance(spec.get("require_claim_status", False), bool)
    workspace, revision = roots(spec_path, spec)
    assert workspace.is_dir(), f"workspace_root missing: {workspace}"
    assert revision.is_dir(), f"revision_root missing: {revision}"

    stages = spec.get("stages")
    assert isinstance(stages, list) and stages, "stages must be a non-empty list"
    ids: list[str] = []
    roles: set[str] = set()
    for stage in stages:
        assert isinstance(stage, dict)
        stage_id = stage.get("id")
        assert isinstance(stage_id, str) and stage_id
        assert stage_id not in ids, f"duplicate stage id: {stage_id}"
        ids.append(stage_id)
        artifacts = stage.get("required_artifacts", [])
        assert isinstance(artifacts, list)
        applicable = stage.get("applicable", True)
        assert isinstance(applicable, bool)
        if not applicable:
            assert isinstance(stage.get("na_reason"), str) and stage["na_reason"].strip()
            assert not artifacts, f"non-applicable stage cannot require artifacts: {stage_id}"
        for artifact in artifacts:
            assert isinstance(artifact, dict)
            role = artifact.get("role")
            relative = artifact.get("path")
            kind = artifact.get("kind")
            expected = artifact.get("sha256")
            assert isinstance(role, str) and role and role not in roles, f"duplicate artifact role: {role}"
            assert isinstance(relative, str) and relative
            assert kind in {"FROZEN_INPUT", "RUN_OUTPUT"}
            assert expected is None or (isinstance(expected, str) and SHA256_RE.fullmatch(expected))
            assertions = artifact.get("json_assertions", [])
            assert isinstance(assertions, list)
            for assertion in assertions:
                assert isinstance(assertion, dict)
                assert isinstance(assertion.get("pointer"), str) and str(assertion["pointer"]).startswith("/")
                assert "equals" in assertion
            target = (workspace / relative).resolve()
            assert inside(target, workspace), f"artifact escapes workspace: {relative}"
            if kind == "RUN_OUTPUT":
                assert inside(target, revision), f"run output escapes revision: {relative}"
            roles.add(role)
    assert tuple(ids) == CANONICAL_STAGES, f"whole-system stages must equal canonical order: {CANONICAL_STAGES}"
    return stages


def blank_state(spec_path: Path, spec: dict[str, object], stages: list[dict[str, object]]) -> dict[str, object]:
    state = {
        "schema": STATE_SCHEMA,
        "run_id": spec["run_id"],
        "writer_id": spec["writer_id"],
        "spec_sha256": sha256(spec_path),
        "audit_scope": spec["audit_scope"],
        "current_stage": stages[0]["id"],
        "aggregate_status": "UNVERIFIED",
        "final_or_release": False,
        "event_count": 0,
        "event_head_sha256": ZERO_HASH,
        "stages": {
            str(stage["id"]): {
                "status": "PENDING",
                "event_id": None,
                "recorded_at": None,
                "artifacts": [],
                "blockers": [],
                "notes": [],
            }
            for stage in stages
        },
    }
    if spec.get("require_claim_status", False):
        state["require_claim_status"] = True
    return state


def refresh_summary(state: dict[str, object], stage_order: list[str]) -> None:
    records = state["stages"]
    assert isinstance(records, dict)
    current = next((stage_id for stage_id in stage_order if records[stage_id]["status"] != PASS), None)
    state["current_stage"] = current
    if current is None:
        claims_full = all(records[stage_id].get("claim_status", "PASS") in {"PASS", "NOT_APPLICABLE"} for stage_id in stage_order)
        full_scope = state["audit_scope"] == "FULL_ACTIVE_RULE_REGRESSION" and claims_full
        state["aggregate_status"] = "PASS" if full_scope else "PARTIAL_SCOPED"
        state["final_or_release"] = full_scope
        return
    status = records[current]["status"]
    state["aggregate_status"] = status if status in {"BLOCKED", "UNVERIFIED"} else "UNVERIFIED"
    state["final_or_release"] = False


def read_events(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    events: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        assert isinstance(value, dict), f"event line {line_number} is not an object"
        events.append(value)
    return events


def event_hash(event: dict[str, object]) -> str:
    payload = {key: value for key, value in event.items() if key != "event_sha256"}
    return hashlib.sha256(canonical(payload)).hexdigest()


def apply_event(state: dict[str, object], event: dict[str, object], stage_order: list[str]) -> None:
    assert event.get("schema") == EVENT_SCHEMA
    assert event.get("run_id") == state["run_id"]
    assert event.get("writer_id") == state["writer_id"]
    assert event.get("index") == state["event_count"] + 1
    assert event.get("previous_event_sha256") == state["event_head_sha256"]
    assert event.get("event_sha256") == event_hash(event)
    event_type = event.get("type")
    stage_id = str(event.get("stage_id"))
    assert stage_id in stage_order
    if event_type == "STAGE_RECORD":
        assert stage_id == state["current_stage"], f"event stage is not current stage: {stage_id} != {state['current_stage']}"
        status = event.get("status")
        assert status in STAGE_STATUSES - {"PENDING"}
        claim_status = event.get("claim_status")
        if state.get("require_claim_status") is True:
            assert claim_status in CLAIM_STATUSES, "claim_status is required by this run spec"
        if claim_status is not None:
            assert claim_status in CLAIM_STATUSES
            if status == PASS:
                assert claim_status in {"PASS", "PARTIAL_SCOPED", "NOT_APPLICABLE"}
            else:
                assert claim_status == status
        artifacts, blockers, notes = event.get("artifacts"), event.get("blockers"), event.get("notes")
        assert isinstance(artifacts, list) and isinstance(blockers, list) and isinstance(notes, list)
        assert (status == PASS and not blockers) or (status != PASS and blockers), (
            "PASS cannot carry blockers; BLOCKED/UNVERIFIED requires at least one blocker"
        )
        record = state["stages"][stage_id]
        record.update(
            status=status,
            event_id=event["event_id"],
            recorded_at=event["recorded_at"],
            artifacts=deepcopy(artifacts),
            blockers=deepcopy(blockers),
            notes=deepcopy(notes),
        )
        if claim_status is not None:
            record["claim_status"] = claim_status
    elif event_type == "INVALIDATE_FROM_STAGE":
        start = stage_order.index(stage_id)
        for invalidated in stage_order[start:]:
            state["stages"][invalidated] = {
                "status": "PENDING",
                "event_id": None,
                "recorded_at": None,
                "artifacts": [],
                "blockers": [],
                "notes": [],
            }
    else:
        raise AssertionError(f"unknown event type: {event_type}")
    state["event_count"] = event["index"]
    state["event_head_sha256"] = event["event_sha256"]
    refresh_summary(state, stage_order)


def replay(spec_path: Path, spec: dict[str, object], events: list[dict[str, object]]) -> dict[str, object]:
    stages = validate_spec(spec_path, spec)
    state = blank_state(spec_path, spec, stages)
    stage_order = [str(stage["id"]) for stage in stages]
    seen_event_ids: set[str] = set()
    previous_recorded_at: datetime | None = None
    for event in events:
        event_id = event.get("event_id")
        assert isinstance(event_id, str) and event_id and event_id not in seen_event_ids, f"duplicate or empty event id: {event_id}"
        seen_event_ids.add(event_id)
        recorded_at = event.get("recorded_at")
        assert isinstance(recorded_at, str) and RFC3339_RE.fullmatch(recorded_at), f"invalid RFC3339 recorded_at: {recorded_at}"
        parsed = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, f"recorded_at must include an RFC3339 timezone: {recorded_at}"
        assert previous_recorded_at is None or parsed >= previous_recorded_at, "recorded_at values must be nondecreasing"
        previous_recorded_at = parsed
        apply_event(state, event, stage_order)
    return state


def reconcile_recorded_artifacts(spec: dict[str, object], state: dict[str, object]) -> None:
    stage_specs = {str(stage["id"]): stage for stage in spec["stages"]}
    for stage_id, record in state["stages"].items():
        stage_spec = stage_specs[stage_id]
        requirements = {item["role"]: item for item in stage_spec.get("required_artifacts", [])}
        if stage_spec.get("applicable", True) is False and record["status"] != "PENDING":
            assert record.get("claim_status") == "NOT_APPLICABLE", f"non-applicable stage claim drift: {stage_id}"
        if stage_spec.get("applicable", True) is True:
            assert record.get("claim_status") != "NOT_APPLICABLE", f"applicable stage claim drift: {stage_id}"
        artifacts = record["artifacts"]
        assert isinstance(artifacts, list)
        recorded = {item["role"]: item for item in artifacts}
        assert len(recorded) == len(artifacts), f"duplicate recorded artifact roles: {stage_id}"
        assert set(recorded) <= set(requirements), f"unknown recorded artifact role: {stage_id}"
        if record["status"] == PASS:
            assert set(recorded) == set(requirements), f"PASS artifact set does not match spec: {stage_id}"
        for role, item in recorded.items():
            requirement = requirements[role]
            assert item["path"] == requirement["path"], f"recorded artifact path drift: {stage_id}/{role}"
            assert item["kind"] == requirement["kind"], f"recorded artifact kind drift: {stage_id}/{role}"
            assert item.get("json_assertions", []) == requirement.get("json_assertions", []), (
                f"recorded artifact assertions drift: {stage_id}/{role}"
            )
            expected = requirement.get("sha256")
            assert expected is None or item["sha256"] == expected, f"recorded frozen hash drift: {stage_id}/{role}"


def verify_artifacts(
    spec_path: Path,
    spec: dict[str, object],
    state: dict[str, object],
    stage_ids: set[str] | None = None,
) -> None:
    workspace, _ = roots(spec_path, spec)
    records = state["stages"]
    assert isinstance(records, dict)
    for stage_id, record in records.items():
        if stage_ids is not None and stage_id not in stage_ids:
            continue
        assert record["status"] in STAGE_STATUSES, f"bad stage status: {stage_id}"
        seen: set[str] = set()
        for artifact in record["artifacts"]:
            role = artifact["role"]
            assert role not in seen, f"duplicate recorded artifact role: {role}"
            target = (workspace / artifact["path"]).resolve()
            assert target.is_file(), f"recorded artifact missing: {target}"
            assert sha256(target) == artifact["sha256"], f"recorded artifact changed: {target}"
            check_json_assertions(target, artifact.get("json_assertions", []))
            seen.add(role)


def json_pointer(value: object, pointer: str) -> object:
    current = value
    for raw in pointer.removeprefix("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            assert token in current, f"JSON pointer missing key: {pointer}"
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise AssertionError(f"JSON pointer crosses scalar: {pointer}")
    return current


def check_json_assertions(path: Path, assertions: list[dict[str, object]]) -> None:
    if not assertions:
        return
    document = load_json(path)
    for assertion in assertions:
        actual = json_pointer(document, str(assertion["pointer"]))
        assert actual == assertion["equals"], (
            f"JSON assertion failed: {path} {assertion['pointer']}: {actual!r} != {assertion['equals']!r}"
        )


def validate_run(spec_path: Path, state_path: Path, events_path: Path) -> dict[str, object]:
    spec = load_json(spec_path)
    actual_state = load_json(state_path)
    expected_state = replay(spec_path, spec, read_events(events_path))
    assert actual_state == expected_state, "state does not equal event replay"
    reconcile_recorded_artifacts(spec, actual_state)
    verify_artifacts(spec_path, spec, actual_state)
    return actual_state


def capture_artifacts(
    spec_path: Path, spec: dict[str, object], stage: dict[str, object], require_all: bool
) -> list[dict[str, object]]:
    workspace, _ = roots(spec_path, spec)
    captured: list[dict[str, object]] = []
    for requirement in stage.get("required_artifacts", []):
        target = (workspace / str(requirement["path"])).resolve()
        if not target.is_file():
            assert not require_all, f"required artifact missing: {target}"
            continue
        actual = sha256(target)
        expected = requirement.get("sha256")
        assert expected is None or actual == expected, f"frozen artifact hash mismatch: {target}"
        assertions = deepcopy(requirement.get("json_assertions", []))
        check_json_assertions(target, assertions)
        captured.append(
            {
                "role": requirement["role"],
                "path": requirement["path"],
                "kind": requirement["kind"],
                "bytes": target.stat().st_size,
                "sha256": actual,
                "json_assertions": assertions,
            }
        )
    return captured


def append_event(events_path: Path, event: dict[str, object]) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def new_event(state: dict[str, object], args: argparse.Namespace, event_type: str) -> dict[str, object]:
    event = {
        "schema": EVENT_SCHEMA,
        "index": state["event_count"] + 1,
        "previous_event_sha256": state["event_head_sha256"],
        "event_id": args.event_id,
        "recorded_at": args.recorded_at,
        "run_id": state["run_id"],
        "writer_id": args.writer_id,
        "type": event_type,
        "stage_id": args.stage,
    }
    return event


def command_init(args: argparse.Namespace) -> None:
    spec_path, state_path, events_path = map(Path.resolve, (args.spec, args.state, args.events))
    assert not state_path.exists(), f"state already exists: {state_path}"
    assert not events_path.exists(), f"events already exist: {events_path}"
    spec = load_json(spec_path)
    stages = validate_spec(spec_path, spec)
    write_json(state_path, blank_state(spec_path, spec, stages))
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.touch(exist_ok=False)


def command_record(args: argparse.Namespace) -> None:
    spec_path, state_path, events_path = map(Path.resolve, (args.spec, args.state, args.events))
    spec = load_json(spec_path)
    state = validate_run(spec_path, state_path, events_path)
    assert args.writer_id == spec["writer_id"], "writer_id does not own this run"
    stages = validate_spec(spec_path, spec)
    stage_order = [str(stage["id"]) for stage in stages]
    assert args.stage == state["current_stage"], f"only current stage may be recorded: {state['current_stage']}"
    assert args.status in STAGE_STATUSES - {"PENDING"}
    blockers = args.blocker or []
    assert (args.status == PASS and not blockers) or (args.status != PASS and blockers), (
        "PASS cannot carry blockers; BLOCKED/UNVERIFIED requires at least one blocker"
    )
    stage = next(value for value in stages if value["id"] == args.stage)
    event = new_event(state, args, "STAGE_RECORD")
    claim_status = args.claim_status or ("PASS" if args.status == PASS else args.status)
    if stage.get("applicable", True) is False:
        assert args.status == PASS and claim_status == "NOT_APPLICABLE", "non-applicable stage must record PASS_TO_NEXT_GATE / NOT_APPLICABLE"
    else:
        assert claim_status != "NOT_APPLICABLE", "applicable stage cannot claim NOT_APPLICABLE"
    event.update(
        status=args.status,
        claim_status=claim_status,
        artifacts=capture_artifacts(spec_path, spec, stage, require_all=args.status == PASS),
        blockers=blockers,
        notes=args.note or [],
    )
    event["event_sha256"] = event_hash(event)
    append_event(events_path, event)
    apply_event(state, event, stage_order)
    write_json(state_path, state)


def command_invalidate(args: argparse.Namespace) -> None:
    spec_path, state_path, events_path = map(Path.resolve, (args.spec, args.state, args.events))
    spec = load_json(spec_path)
    stages = validate_spec(spec_path, spec)
    stage_order = [str(stage["id"]) for stage in stages]
    assert args.stage in stage_order
    state = load_json(state_path)
    expected_state = replay(spec_path, spec, read_events(events_path))
    assert state == expected_state, "state does not equal event replay"
    reconcile_recorded_artifacts(spec, state)
    upstream = set(stage_order[: stage_order.index(args.stage)])
    verify_artifacts(spec_path, spec, state, upstream)
    assert args.writer_id == spec["writer_id"], "writer_id does not own this run"
    event = new_event(state, args, "INVALIDATE_FROM_STAGE")
    event["reason"] = args.reason
    event["event_sha256"] = event_hash(event)
    append_event(events_path, event)
    apply_event(state, event, stage_order)
    write_json(state_path, state)


def command_validate(args: argparse.Namespace) -> None:
    state = validate_run(Path(args.spec).resolve(), Path(args.state).resolve(), Path(args.events).resolve())
    print(
        json.dumps(
            {
                "status": "PASS_LEDGER_INTEGRITY",
                "run_id": state["run_id"],
                "current_stage": state["current_stage"],
                "aggregate_status": state["aggregate_status"],
                "final_or_release": state["final_or_release"],
                "event_count": state["event_count"],
                "event_head_sha256": state["event_head_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)


def event_common(parser: argparse.ArgumentParser) -> None:
    common(parser)
    parser.add_argument("--writer-id", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--event-id", required=True)
    parser.add_argument("--recorded-at", required=True)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init")
    common(init)
    init.set_defaults(function=command_init)
    record = commands.add_parser("record")
    event_common(record)
    record.add_argument("--status", required=True, choices=sorted(STAGE_STATUSES - {"PENDING"}))
    record.add_argument("--claim-status", choices=sorted(CLAIM_STATUSES))
    record.add_argument("--blocker", action="append")
    record.add_argument("--note", action="append")
    record.set_defaults(function=command_record)
    invalidate = commands.add_parser("invalidate")
    event_common(invalidate)
    invalidate.add_argument("--reason", required=True)
    invalidate.set_defaults(function=command_invalidate)
    validate = commands.add_parser("validate")
    common(validate)
    validate.set_defaults(function=command_validate)
    return root


def main() -> None:
    args = parser().parse_args()
    args.function(args)


if __name__ == "__main__":
    main()
