#!/usr/bin/env python3
"""Runnable standard-library checks for the whole-system workflow ledger."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py"
MODULE_SPEC = importlib.util.spec_from_file_location("workflow_ledger_under_test", TOOL)
assert MODULE_SPEC and MODULE_SPEC.loader
LEDGER = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(LEDGER)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class WorkflowLedgerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.revision = self.root / "revision"
        self.revision.mkdir()
        self.input_path = self.root / "input.json"
        self.output_path = self.revision / "output.json"
        write_json(self.input_path, {"status": "PASS", "count": 2})
        write_json(self.output_path, {"status": "PASS", "collisions": 0})
        self.spec = self.root / "RUN_SPEC.json"
        self.state = self.revision / "WORKFLOW_STATE.json"
        self.events = self.revision / "WORKFLOW_EVENTS.jsonl"
        write_json(
            self.spec,
            {
                "schema": "opticalmodeler.whole-system-run-spec.v1",
                "mode": "WHOLE_SYSTEM_END_TO_END",
                "run_id": "self-test-run",
                "writer_id": "writer-one",
                "single_writer": True,
                "allow_module_stitching": False,
                "workspace_root": ".",
                "revision_root": "revision",
                "audit_scope": "FULL_ACTIVE_RULE_REGRESSION",
                "stages": [
                    {"id": "run_lock", "required_artifacts": []},
                    {
                        "id": "source_lock",
                        "required_artifacts": [
                            {
                                "role": "input",
                                "path": "input.json",
                                "kind": "FROZEN_INPUT",
                                "sha256": digest(self.input_path),
                                "json_assertions": [
                                    {"pointer": "/status", "equals": "PASS"},
                                    {"pointer": "/count", "equals": 2},
                                ],
                            }
                        ],
                    },
                    {"id": "topology_lock", "required_artifacts": []},
                    {"id": "cad_provenance_lock", "required_artifacts": []},
                    {"id": "deterministic_replay", "required_artifacts": []},
                    {"id": "representative_smoke", "required_artifacts": []},
                    {"id": "full_scene_build", "required_artifacts": []},
                    {"id": "saved_scene_reopen", "required_artifacts": []},
                    {"id": "whole_system_optomechanical_audit", "required_artifacts": []},
                    {"id": "visual_audit", "required_artifacts": []},
                    {"id": "export_and_sanitization", "required_artifacts": []},
                    {
                        "id": "final_consistency",
                        "required_artifacts": [
                            {
                                "role": "output",
                                "path": "revision/output.json",
                                "kind": "RUN_OUTPUT",
                                "sha256": None,
                                "json_assertions": [
                                    {"pointer": "/status", "equals": "PASS"},
                                    {"pointer": "/collisions", "equals": 0},
                                ],
                            }
                        ],
                    },
                ],
            },
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_tool(self, *arguments: str, succeeds: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(TOOL), *arguments], capture_output=True, text=True, check=False
        )
        if succeeds and result.returncode != 0:
            self.fail(result.stderr or result.stdout)
        if not succeeds and result.returncode == 0:
            self.fail("command unexpectedly succeeded")
        return result

    def common(self) -> list[str]:
        return ["--spec", str(self.spec), "--state", str(self.state), "--events", str(self.events)]

    def init(self) -> None:
        self.run_tool("init", *self.common())

    def record(self, stage: str, event_id: str, writer: str = "writer-one", succeeds: bool = True, claim_status: str | None = None) -> None:
        event_number = int(event_id.removeprefix("E"))
        arguments = [
            "record",
            *self.common(),
            "--writer-id",
            writer,
            "--stage",
            stage,
            "--status",
            "PASS_TO_NEXT_GATE",
            "--event-id",
            event_id,
            "--recorded-at",
            f"2026-08-13T00:{event_number:02d}:00Z",
        ]
        if claim_status:
            arguments.extend(("--claim-status", claim_status))
        self.run_tool(*arguments, succeeds=succeeds)

    def record_remaining(self, start_event: int = 3) -> None:
        stages = [
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
        ]
        for offset, stage in enumerate(stages):
            self.record(stage, f"E{start_event + offset:03d}")

    def test_complete_run_and_tamper_detection(self) -> None:
        self.init()
        self.record("run_lock", "E001")
        self.record("source_lock", "E002")
        self.record_remaining()
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["aggregate_status"], "PASS")
        self.assertTrue(summary["final_or_release"])
        write_json(self.output_path, {"status": "PASS", "collisions": 1})
        self.run_tool("validate", *self.common(), succeeds=False)

    def test_wrong_writer_and_out_of_order_gate_fail(self) -> None:
        self.init()
        self.record("run_lock", "E001", writer="writer-two", succeeds=False)
        self.record("run_lock", "E001")
        self.record("final_consistency", "E002", succeeds=False)

    def test_invalid_candidate_never_changes_ledger_bytes(self) -> None:
        for command in ("record", "invalidate"):
            for index, (event_id, recorded_at) in enumerate((
                ("E002", "2026-08-13T00:00:00Z"),
                ("E002", "not-a-timestamp"),
                ("E002", "2026-02-30T00:01:00Z"),
                ("E001", "2026-08-13T00:02:00Z"),
                ("", "2026-08-13T00:02:00Z"),
            )):
                with self.subTest(command=command, event_id=event_id, recorded_at=recorded_at):
                    self.state = self.revision / f"state-{command}-{index}.json"
                    self.events = self.revision / f"events-{command}-{index}.jsonl"
                    self.init()
                    self.record("run_lock", "E001")
                    before = (self.state.read_bytes(), self.events.read_bytes())
                    extra = ["--status", "PASS_TO_NEXT_GATE"] if command == "record" else ["--reason", "regression"]
                    self.run_tool(
                        command, *self.common(), "--writer-id", "writer-one",
                        "--stage", "source_lock", "--event-id", event_id,
                        "--recorded-at", recorded_at, *extra, succeeds=False,
                    )
                    self.assertEqual((self.state.read_bytes(), self.events.read_bytes()), before)
                    self.run_tool("validate", *self.common())

    def test_equal_timestamps_and_back_to_back_invalidation(self) -> None:
        self.init()
        timestamp = "2026-08-13T00:01:00Z"
        for event_id, command, stage in (
            ("E001", "record", "run_lock"),
            ("E002", "record", "source_lock"),
            ("E003", "invalidate", "source_lock"),
            ("E004", "record", "source_lock"),
        ):
            extra = ["--status", "PASS_TO_NEXT_GATE"] if command == "record" else ["--reason", "regression"]
            self.run_tool(
                command, *self.common(), "--writer-id", "writer-one",
                "--stage", stage, "--event-id", event_id,
                "--recorded-at", timestamp, *extra,
            )
            self.run_tool("validate", *self.common())
        self.record_remaining(start_event=5)
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["aggregate_status"], "PASS")
        self.assertTrue(summary["final_or_release"])

    def test_complete_partial_scope_stays_non_release(self) -> None:
        spec = json.loads(self.spec.read_text(encoding="utf-8"))
        spec["audit_scope"] = "PARTIAL_SCOPED"
        write_json(self.spec, spec)
        self.init()
        self.record("run_lock", "E001")
        self.record("source_lock", "E002")
        self.record_remaining()
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["aggregate_status"], "PARTIAL_SCOPED")
        self.assertFalse(summary["final_or_release"])

    def test_partial_claim_blocks_full_scope_release(self) -> None:
        self.init()
        self.record("run_lock", "E001")
        self.record("source_lock", "E002")
        stages = [
            "topology_lock", "cad_provenance_lock", "deterministic_replay", "representative_smoke",
            "full_scene_build", "saved_scene_reopen", "whole_system_optomechanical_audit",
            "visual_audit", "export_and_sanitization",
        ]
        for index, stage in enumerate(stages, 3):
            self.record(stage, f"E{index:03d}")
        self.record("final_consistency", "E012", claim_status="PARTIAL_SCOPED")
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["aggregate_status"], "PARTIAL_SCOPED")
        self.assertFalse(summary["final_or_release"])

    def test_json_assertion_and_invalidation_fail_closed(self) -> None:
        self.init()
        self.record("run_lock", "E001")
        write_json(self.input_path, {"status": "FAIL", "count": 2})
        self.record("source_lock", "E002", succeeds=False)
        write_json(self.input_path, {"status": "PASS", "count": 2})
        self.record("source_lock", "E002")
        self.record_remaining()
        self.run_tool(
            "invalidate",
            *self.common(),
            "--writer-id",
            "writer-one",
            "--stage",
            "source_lock",
            "--event-id",
            "E013",
            "--recorded-at",
            "2026-08-13T00:13:00Z",
            "--reason",
            "upstream source changed",
        )
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["current_stage"], "source_lock")
        self.assertEqual(summary["aggregate_status"], "UNVERIFIED")
        self.assertFalse(summary["final_or_release"])

    def test_drifted_downstream_can_invalidate_but_upstream_drift_cannot(self) -> None:
        self.init()
        self.record("run_lock", "E001")
        self.record("source_lock", "E002")
        self.record_remaining()
        write_json(self.output_path, {"status": "PASS", "collisions": 1})
        self.run_tool(
            "invalidate",
            *self.common(),
            "--writer-id",
            "writer-one",
            "--stage",
            "final_consistency",
            "--event-id",
            "E013",
            "--recorded-at",
            "2026-08-13T00:13:00Z",
            "--reason",
            "downstream artifact drifted before invalidation",
        )
        summary = json.loads(self.run_tool("validate", *self.common()).stdout)
        self.assertEqual(summary["current_stage"], "final_consistency")
        write_json(self.output_path, {"status": "PASS", "collisions": 0})
        self.record("final_consistency", "E014")
        write_json(self.input_path, {"status": "PASS", "count": 3})
        self.run_tool(
            "invalidate",
            *self.common(),
            "--writer-id",
            "writer-one",
            "--stage",
            "final_consistency",
            "--event-id",
            "E015",
            "--recorded-at",
            "2026-08-13T00:15:00Z",
            "--reason",
            "attempt to skip changed upstream input",
            succeeds=False,
        )

    def test_forged_replay_order_and_artifact_contract_fail(self) -> None:
        self.init()
        self.record("run_lock", "E001")
        self.record("source_lock", "E002")
        self.record_remaining()
        spec = LEDGER.load_json(self.spec)
        events = LEDGER.read_events(self.events)

        forged_order = json.loads(json.dumps(events))
        forged_order[1]["stage_id"] = "final_consistency"
        forged_order[1]["event_sha256"] = LEDGER.event_hash(forged_order[1])
        with self.assertRaises(AssertionError):
            LEDGER.replay(self.spec, spec, forged_order)

        forged_artifact = json.loads(json.dumps(events))
        forged_artifact[-1]["artifacts"][0]["path"] = "revision/not-the-spec-output.json"
        forged_artifact[-1]["event_sha256"] = LEDGER.event_hash(forged_artifact[-1])
        state = LEDGER.replay(self.spec, spec, forged_artifact)
        with self.assertRaises(AssertionError):
            LEDGER.reconcile_recorded_artifacts(spec, state)

        duplicate_id = json.loads(json.dumps(events))
        duplicate_id[1]["event_id"] = duplicate_id[0]["event_id"]
        duplicate_id[1]["event_sha256"] = LEDGER.event_hash(duplicate_id[1])
        with self.assertRaises(AssertionError):
            LEDGER.replay(self.spec, spec, duplicate_id)

        decreasing_time = json.loads(json.dumps(events))
        decreasing_time[1]["recorded_at"] = "2026-08-12T23:59:00Z"
        decreasing_time[1]["event_sha256"] = LEDGER.event_hash(decreasing_time[1])
        with self.assertRaises(AssertionError):
            LEDGER.replay(self.spec, spec, decreasing_time)

        invalid_time = json.loads(json.dumps(events))
        invalid_time[1]["recorded_at"] = "2026-08-13 00:02:00+00:00"
        invalid_time[1]["event_sha256"] = LEDGER.event_hash(invalid_time[1])
        with self.assertRaises(AssertionError):
            LEDGER.replay(self.spec, spec, invalid_time)


if __name__ == "__main__":
    unittest.main()
