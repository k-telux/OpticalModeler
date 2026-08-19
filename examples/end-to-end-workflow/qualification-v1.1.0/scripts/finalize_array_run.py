#!/usr/bin/env python3
"""Create a sanitized public candidate and scoped final consistency for one array run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path


FORBIDDEN_SUFFIXES = {".step", ".stp", ".stl", ".blend", ".blend1", ".zip", ".7z", ".rar"}
PRIVATE_PATH = re.compile(rb"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/(?:Users|home)/[^/\s]+/)")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    args = parser.parse_args()
    root, repo = args.run_root.resolve(), args.repo.resolve()
    config = read(root / "RUN_CONFIG.json")
    full = root / "work" / "full_32_node_propagation_v3"
    array = root / "work" / "array_scale"
    evidence = array / "evidence"
    public = root / "public_candidate"
    public.mkdir(parents=True, exist_ok=True)

    source_sheet = evidence / "audits" / "N04_ARRAY_CONTACT_SHEET.png"
    public_sheet = public / "N04_ARRAY_CONTACT_SHEET.png"
    shutil.copy2(source_sheet, public_sheet)
    sys.path.insert(0, str(repo / "scripts"))
    from sanitize_png import sanitize

    png_report = sanitize(public_sheet)
    png_report["path"] = public_sheet.name
    write(public / "PNG_SANITIZATION.json", png_report)

    topology = read(root / "outputs" / "phase1_source_cad_topology_lock" / "ARRAY_TOPOLOGY_MAP.json")
    cache_seed = read(root / "work" / "vendor_cad_cache" / "CACHE_SEED_AUDIT.json")
    cad_fetch = read(root / "work" / "vendor_cad_cache" / "CAD_FETCH_AUDIT.json")
    representative = read(root / "outputs" / "phase2_representative_smoke_r3" / "REPRESENTATIVE_SMOKE_AUDIT.json")
    cad_mesh = read(full / "measurements" / "FULL_CAD_MESH_AUDIT.json")
    base_reopen = read(full / "evidence" / "REOPEN_FULL_REGRESSION.json")
    base_second = read(full / "evidence" / "GATE_BLEND_SECOND_REOPEN.json")
    generated = read(evidence / "ARRAY_GENERATOR_REPORT.json")
    reopened = read(evidence / "ARRAY_REOPEN_AUDIT.json")
    second = read(evidence / "ARRAY_SECOND_REOPEN.json")
    visual = read(evidence / "ARRAY_OPENCV_AUDIT.json")
    audited_blend = array / "scene" / f"N04_ARRAY_{config['station_count']}x_AUDITED.blend"
    checks = {
        "run_config_pass": config["status"] == "PASS" and config["single_writer"] is True and config["allow_module_stitching"] is False,
        "topology_counts": topology["counts"]["nodes"] == 32 * config["station_count"] and topology["counts"]["directed_edge_traversals"] == 44 * config["station_count"],
        "cache_seed_54_pass": cache_seed["status"] == "PASS" and cache_seed["verified_seeded_file_count"] == 54,
        "cad_fetch_54_pass": cad_fetch["status"] == "PASS" and cad_fetch["verified_file_count"] == 54,
        "representative_reopen_pass": representative["status"] == "PASS",
        "full_cad_54_clean": cad_mesh["status"] == "PASS" and cad_mesh["processed_cad_file_count"] == 54 and cad_mesh["totals"]["post_clean_invalid_faces"] == 0,
        "base_first_reopen_pass": base_reopen["status"] == "PASS" and base_reopen["failures"] == [],
        "base_second_reopen_pass": base_second["status"] == "PASS" and base_second["failures"] == [],
        "array_generation_pass": generated["status"] == "PASS",
        "array_first_reopen_pass": reopened["status"] == "PASS" and reopened["failures"] == [],
        "array_second_reopen_pass": second["status"] == "PASS" and second["failures"] == [],
        "array_opencv_pass": visual["status"] == "PASS" and visual["render_count"] == 4,
        "public_png_pixels_unchanged": png_report["pixel_data_unchanged"] is True,
        "audited_blend_exists": audited_blend.is_file(),
    }
    final = {
        "schema": "opticalmodeler.n04-array-final-consistency.v1",
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "aggregate_scope_status": "PARTIAL_SCOPED",
        "final_or_release": False,
        "run_id": config["run_id"],
        "system": {
            "station_count": config["station_count"],
            "nodes": config["total_nodes"],
            "directed_edges": config["total_directed_edges"],
            "official_instances": second["official_instance_count"],
            "modeled_load_links": second["modeled_load_link_count"],
        },
        "scene": {
            "relative_private_path": audited_blend.relative_to(root).as_posix(),
            "bytes": audited_blend.stat().st_size if audited_blend.is_file() else 0,
            "sha256": digest(audited_blend) if audited_blend.is_file() else None,
        },
        "public_raster": {"path": public_sheet.name, "bytes": public_sheet.stat().st_size, "sha256": digest(public_sheet)},
        "checks": checks,
        "status_boundaries": {
            "literal_paper_multi_station_system": "BLOCKED_NOT_CLAIMED",
            "base_substitutions": "PARTIAL_SCOPED",
            "vendor_cad_redistribution": "BLOCKED",
            "force_torque_dynamic_calibration": "BLOCKED",
            "visual_evidence_is_not_physical_proof": True,
        },
    }
    write(public / "ARRAY_FINAL_CONSISTENCY.json", final)

    forbidden, private_hits = [], []
    for path in sorted(item for item in public.rglob("*") if item.is_file()):
        relative = path.relative_to(public).as_posix()
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            forbidden.append(relative)
        if PRIVATE_PATH.search(path.read_bytes()):
            private_hits.append(relative)
    sanitization = {
        "schema": "opticalmodeler.n04-array-sanitization-audit.v1",
        "status": "PASS" if not forbidden and not private_hits else "BLOCKED",
        "scope": "PUBLIC_METADATA_AND_SANITIZED_RASTER_ONLY",
        "vendor_geometry_included": False,
        "blend_included": False,
        "forbidden_files": forbidden,
        "absolute_private_path_hits": private_hits,
        "pixel_payload_unchanged": png_report["pixel_data_unchanged"],
    }
    write(public / "SANITIZATION_AUDIT.json", sanitization)
    print(json.dumps({"status": final["status"], "sanitization": sanitization["status"], "aggregate_scope_status": final["aggregate_scope_status"], "final_or_release": False, "checks": checks}, indent=2))
    raise SystemExit(final["status"] != "PASS" or sanitization["status"] != "PASS")


if __name__ == "__main__":
    main()
