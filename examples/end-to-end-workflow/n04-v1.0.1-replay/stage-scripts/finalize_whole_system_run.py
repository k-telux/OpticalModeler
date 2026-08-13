#!/usr/bin/env python3
"""Create scoped final-consistency and sanitization reports for one N04 run."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


FORBIDDEN_SUFFIXES = {".step", ".stp", ".stl", ".blend", ".zip", ".7z", ".rar"}
PRIVATE_PATH = re.compile(rb"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/(?:Users|home)/[^/\s]+/)")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: finalize_whole_system_run.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    full = root / "work" / "full_32_node_propagation_v3"
    evidence = full / "evidence"
    public = root / "public_candidate"
    public.mkdir(parents=True, exist_ok=True)

    source_contact_sheet = full / "audits" / "FULL_32_RENDER_CONTACT_SHEET.png"
    public_contact_sheet = public / "FULL_32_RENDER_CONTACT_SHEET.png"
    shutil.copy2(source_contact_sheet, public_contact_sheet)
    repository_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(repository_root / "scripts"))
    from sanitize_png import sanitize

    png_sanitization = sanitize(public_contact_sheet)
    png_sanitization["path"] = public_contact_sheet.name
    write(public / "PNG_SANITIZATION.json", png_sanitization)

    source = load(root / "outputs" / "phase1_source_cad_topology_lock" / "SOURCE_LOCK.json")
    topology = load(root / "outputs" / "phase1_source_cad_topology_lock" / "TOPOLOGY_MAP.json")
    cad = load(root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json")
    cad_fetch = load(root / "work" / "vendor_cad_cache" / "CAD_FETCH_AUDIT.json")
    representative = load(root / "outputs" / "phase2_representative_smoke_r3" / "REPRESENTATIVE_SMOKE_AUDIT.json")
    cad_mesh = load(full / "measurements" / "FULL_CAD_MESH_AUDIT.json")
    replay = load(evidence / "BUILD_PARAMS_PUBLIC_RECOMPUTE_READBACK.json")
    generated = load(evidence / "GENERATOR_REPORT.json")
    reopened = load(evidence / "REOPEN_FULL_REGRESSION.json")
    second = load(evidence / "GATE_BLEND_SECOND_REOPEN.json")
    visual = load(evidence / "OPENCV_RENDER_AUDIT.json")

    artifacts = [
        root / "outputs" / "phase1_source_cad_topology_lock" / "SOURCE_LOCK.json",
        root / "outputs" / "phase1_source_cad_topology_lock" / "TOPOLOGY_MAP.json",
        root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json",
        root / "work" / "vendor_cad_cache" / "CAD_FETCH_AUDIT.json",
        root / "outputs" / "phase2_representative_smoke_r3" / "MANIFEST.json",
        full / "measurements" / "FULL_CAD_MESH_AUDIT.json",
        full / "measurements" / "CAD_NATIVE_PORT_LOCK_FULL.json",
        full / "BUILD_PARAMS.json",
        evidence / "BUILD_PARAMS_PUBLIC_RECOMPUTE_READBACK.json",
        evidence / "GENERATOR_REPORT.json",
        evidence / "REOPEN_FULL_REGRESSION.json",
        evidence / "GATE_BLEND_SECOND_REOPEN.json",
        evidence / "OPENCV_RENDER_AUDIT.json",
        public / "FULL_32_RENDER_CONTACT_SHEET.png",
        public / "PNG_SANITIZATION.json",
    ]
    missing = [str(path.relative_to(root)).replace("\\", "/") for path in artifacts if not path.is_file()]
    records = [
        {"path": str(path.relative_to(root)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in artifacts if path.is_file()
    ]
    forbidden_files, private_hits = [], []
    for path in sorted(item for item in public.rglob("*") if item.is_file()):
        relative = str(path.relative_to(public)).replace("\\", "/")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            forbidden_files.append(relative)
        if PRIVATE_PATH.search(path.read_bytes()):
            private_hits.append(relative)

    sanitization = {
        "schema": "opticalmodeler.whole-system-sanitization-audit.v1",
        "status": "PASS" if not forbidden_files and not private_hits else "BLOCKED",
        "scope": "N04_32_NODE_PUBLIC_CANDIDATE",
        "public_candidate_root": "public_candidate",
        "vendor_geometry_included": False,
        "blend_included": False,
        "forbidden_files": forbidden_files,
        "absolute_private_path_hits": private_hits,
        "claim_boundary": "PUBLIC_METADATA_AND_RASTER_EVIDENCE_ONLY; VENDOR_CAD_AND_BLEND_EXCLUDED",
    }
    write(public / "SANITIZATION_AUDIT.json", sanitization)

    checks = {
        "source_lock_pass": source["status"] == "PASS",
        "topology_lock_pass": topology["status"] == "PASS",
        "node_count_32": topology["counts"]["nodes"] == 32,
        "directed_edges_44": topology["counts"]["directed_edge_traversals"] == 44,
        "cad_provenance_pass": cad["status"] == "PASS",
        "cad_model_scope_partial": cad["model_scope_status"] == "PARTIAL_SCOPED",
        "official_cad_fetch_54_pass": (
            cad_fetch["status"] == "PASS"
            and cad_fetch["expected_file_count"] == 54
            and cad_fetch["verified_file_count"] == 54
        ),
        "representative_reopen_pass": representative["status"] == "PASS",
        "cad_mesh_54_pass": cad_mesh["status"] == "PASS" and cad_mesh["processed_cad_file_count"] == 54,
        "cad_mesh_invalid_faces_zero": cad_mesh["totals"]["post_clean_invalid_faces"] == 0,
        "semantic_replay_pass": replay["status"] == "PASS" and replay["difference_paths"] == [],
        "full_generation_pass": generated["status"] == "PASS",
        "first_reopen_pass": reopened["status"] == "PASS" and reopened["failures"] == [],
        "second_reopen_pass": second["status"] == "PASS" and second["failures"] == [],
        "opencv_pass": visual["status"] == "PASS" and visual["render_count"] == 9,
        "artifact_set_complete": not missing,
        "sanitization_pass": sanitization["status"] == "PASS",
        "public_raster_pixel_payload_unchanged": png_sanitization["pixel_data_unchanged"] is True,
    }
    final = {
        "schema": "opticalmodeler.whole-system-final-consistency.v1",
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "aggregate_scope_status": "PARTIAL_SCOPED",
        "final_or_release": False,
        "system": {"id": "n04-lightsheet", "nodes": 32, "directed_edges": 44, "families": 16},
        "scene": {
            "audited_blend_relative_private_path": "work/full_32_node_propagation_v3/scene/FULL_32_NODE_PROPAGATION_GATE_v3.blend",
            "sha256": sha256(full / "scene" / "FULL_32_NODE_PROPAGATION_GATE_v3.blend"),
            "bytes": (full / "scene" / "FULL_32_NODE_PROPAGATION_GATE_v3.blend").stat().st_size,
            "official_instances": second["official_instance_count"],
            "modeled_load_links": second["modeled_load_link_count"],
        },
        "checks": checks,
        "missing_artifacts": missing,
        "artifact_records": records,
        "status_boundaries": {
            "literal_paper_performance": "BLOCKED",
            "vendor_cad_redistribution": "BLOCKED",
            "force_torque_and_dynamic_calibration": "BLOCKED",
            "visual_evidence_is_not_physical_proof": True,
        },
    }
    write(public / "FINAL_CONSISTENCY_AUDIT.json", final)
    print(json.dumps({"status": final["status"], "aggregate_scope_status": final["aggregate_scope_status"], "final_or_release": False, "checks": checks}, indent=2))
    raise SystemExit(final["status"] != "PASS")


if __name__ == "__main__":
    main()
