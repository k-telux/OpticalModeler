#!/usr/bin/env python3
"""Maintain one fail-closed ledger for a whole optical-system build."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path


SPEC_SCHEMA = "opticalmodeler.whole-system-run-spec.v1"
STATE_SCHEMA = "opticalmodeler.whole-system-workflow-state.v1"
EVENT_SCHEMA = "opticalmodeler.whole-system-workflow-event.v1"
PASS = "PASS_TO_NEXT_GATE"
STAGE_STATUSES = {"PENDING", PASS, "BLOCKED", "UNVERIFIED"}
ZERO_HASH = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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
    assert ids[0] == "run_lock", "first stage must be run_lock"
    return stages


def blank_state(spec_path: Path, spec: dict[str, object], stages: list[dict[str, object]]) -> dict[str, object]:
    return {
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


def refresh_summary(state: dict[str, object], stage_order: list[str]) -> None:
    records = state["stages"]
    assert isinstance(records, dict)
    current = next((stage_id for stage_id in stage_order if records[stage_id]["status"] != PASS), None)
    state["current_stage"] = current
    if current is None:
        full_scope = state["audit_scope"] == "FULL_ACTIVE_RULE_REGRESSION"
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
        status = event.get("status")
        assert status in STAGE_STATUSES - {"PENDING"}
        record = state["stages"][stage_id]
        record.update(
            status=status,
            event_id=event["event_id"],
            recorded_at=event["recorded_at"],
            artifacts=deepcopy(event["artifacts"]),
            blockers=deepcopy(event["blockers"]),
            notes=deepcopy(event["notes"]),
        )
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
    for event in events:
        apply_event(state, event, stage_order)
    return state


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
    event.update(
        status=args.status,
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
