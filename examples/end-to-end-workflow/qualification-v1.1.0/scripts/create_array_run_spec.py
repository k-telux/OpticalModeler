#!/usr/bin/env python3
"""Create the 12-gate ledger spec for one scaled N04 qualification run."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(sys.argv[1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
COUNT = CONFIG["station_count"]


def digest(relative: str) -> str:
    return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()


def artifact(role: str, path: str, kind: str = "RUN_OUTPUT", assertions: list[dict] | None = None, frozen: bool = False) -> dict:
    return {"role": role, "path": path, "kind": kind, "sha256": digest(path) if frozen else None, "json_assertions": assertions or []}


spec = {
    "schema": "opticalmodeler.whole-system-run-spec.v1",
    "mode": "WHOLE_SYSTEM_END_TO_END",
    "run_id": CONFIG["run_id"],
    "writer_id": CONFIG["writer_id"],
    "single_writer": True,
    "allow_module_stitching": False,
    "require_claim_status": True,
    "created_at": "2026-08-18T00:00:00-04:00",
    "workspace_root": ".",
    "revision_root": ".",
    "audit_scope": "PARTIAL_SCOPED",
    "system": {"station_count": COUNT, "nodes": CONFIG["total_nodes"], "directed_edges": CONFIG["total_directed_edges"]},
    "stages": [
        {"id": "run_lock", "required_artifacts": [artifact("run_config", "RUN_CONFIG.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/single_writer", "equals": True}, {"pointer": "/allow_module_stitching", "equals": False}], frozen=True)]},
        {"id": "source_lock", "required_artifacts": [
            artifact("source_lock", "outputs/phase1_source_cad_topology_lock/SOURCE_LOCK.json", "FROZEN_INPUT", [{"pointer": "/status", "equals": "PASS"}], True),
            artifact("source_artifact_fetch", "outputs/phase1_source_cad_topology_lock/SOURCE_ARTIFACT_FETCH_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}]),
            artifact("source_bundle_commit", "outputs/phase1_source_cad_topology_lock/SOURCE_BUNDLE_COMMIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}]),
        ]},
        {"id": "topology_lock", "required_artifacts": [artifact("array_topology", "outputs/phase1_source_cad_topology_lock/ARRAY_TOPOLOGY_MAP.json", "FROZEN_INPUT", [{"pointer": "/status", "equals": "PASS"}, {"pointer": "/station_count", "equals": COUNT}, {"pointer": "/counts/nodes", "equals": 32 * COUNT}, {"pointer": "/counts/directed_edge_traversals", "equals": 44 * COUNT}], True)]},
        {"id": "cad_provenance_lock", "required_artifacts": [
            artifact("cad_manifest", "outputs/phase1_source_cad_topology_lock/CAD_MANIFEST.json", "FROZEN_INPUT", [{"pointer": "/status", "equals": "PASS"}, {"pointer": "/model_scope_status", "equals": "PARTIAL_SCOPED"}], True),
            artifact("cache_seed_audit", "work/vendor_cad_cache/CACHE_SEED_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/verified_seeded_file_count", "equals": 54}]),
            artifact("cad_fetch_audit", "work/vendor_cad_cache/CAD_FETCH_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/verified_file_count", "equals": 54}]),
            artifact("official_drawing_url_verify", "work/phase2_representative_smoke_r3/measurements/OFFICIAL_DRAWING_URL_VERIFY.json", assertions=[{"pointer": "/status", "equals": "PASS"}]),
            artifact("artifact_contract_preflight", "work/phase2_representative_smoke_r3/measurements/ARTIFACT_CONTRACT_PREFLIGHT.json", assertions=[{"pointer": "/status", "equals": "PASS"}]),
            artifact("live_cad_source_audit", "work/vendor_cad_cache/CAD_LIVE_SOURCE_AUDIT.json", assertions=[{"pointer": "/expected_file_count", "equals": 54}, {"pointer": "/retrieved_file_count", "equals": 54}]),
        ]},
        {"id": "deterministic_replay", "required_artifacts": [artifact("array_lock_replay", "work/array_scale/evidence/ARRAY_LOCK_REPLAY.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/station_count", "equals": COUNT}, {"pointer": "/difference_paths", "equals": []}, {"pointer": "/automatic_reciprocal_edge_generation", "equals": False}])]},
        {"id": "representative_smoke", "required_artifacts": [artifact("representative_saved_scene_audit", "outputs/phase2_representative_smoke_r3/REPRESENTATIVE_SMOKE_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/vendor_cad_or_mesh_in_public_output", "equals": 0}])]},
        {"id": "full_scene_build", "required_artifacts": [
            artifact("array_generated_blend", f"work/array_scale/scene/N04_ARRAY_{COUNT}x_GENERATED.blend"),
            artifact("array_generator_report", "work/array_scale/evidence/ARRAY_GENERATOR_REPORT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/station_count", "equals": COUNT}, {"pointer": "/total_nodes", "equals": 32 * COUNT}]),
        ]},
        {"id": "saved_scene_reopen", "required_artifacts": [
            artifact("array_audited_blend", f"work/array_scale/scene/N04_ARRAY_{COUNT}x_AUDITED.blend"),
            artifact("array_reopen_audit", "work/array_scale/evidence/ARRAY_REOPEN_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/total_nodes", "equals": 32 * COUNT}, {"pointer": "/total_directed_edges", "equals": 44 * COUNT}, {"pointer": "/failures", "equals": []}]),
        ]},
        {"id": "whole_system_optomechanical_audit", "required_artifacts": [artifact("array_second_reopen", "work/array_scale/evidence/ARRAY_SECOND_REOPEN.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/station_count", "equals": COUNT}, {"pointer": "/official_instance_count", "equals": 154 * COUNT}, {"pointer": "/modeled_load_link_count", "equals": 156 * COUNT}, {"pointer": "/failures", "equals": []}])]},
        {"id": "visual_audit", "required_artifacts": [artifact("array_opencv", "work/array_scale/evidence/ARRAY_OPENCV_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/render_count", "equals": 4}, {"pointer": "/failures", "equals": []}])]},
        {"id": "export_and_sanitization", "required_artifacts": [
            artifact("sanitization_audit", "public_candidate/SANITIZATION_AUDIT.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/vendor_geometry_included", "equals": False}, {"pointer": "/blend_included", "equals": False}]),
            artifact("public_contact_sheet", "public_candidate/N04_ARRAY_CONTACT_SHEET.png"),
            artifact("public_png_sanitization", "public_candidate/PNG_SANITIZATION.json", assertions=[{"pointer": "/pixel_data_unchanged", "equals": True}]),
        ]},
        {"id": "final_consistency", "required_artifacts": [artifact("final_consistency", "public_candidate/ARRAY_FINAL_CONSISTENCY.json", assertions=[{"pointer": "/status", "equals": "PASS"}, {"pointer": "/aggregate_scope_status", "equals": "PARTIAL_SCOPED"}, {"pointer": "/final_or_release", "equals": False}])]},
    ],
}
(ROOT / "RUN_SPEC.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({"status": "PASS", "run_id": CONFIG["run_id"], "stations": COUNT, "stages": len(spec["stages"])}, indent=2))
