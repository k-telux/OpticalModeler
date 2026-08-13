"""Assemble and fail-closed validate the sanitized N04 r3 smoke package."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


FORBIDDEN_FILE_SUFFIXES = {".step", ".stp", ".stl", ".blend", ".pdf", ".zip", ".7z", ".rar"}
FORBIDDEN_TEXT_MARKERS = (
    "C:" + "\\Users\\",
    "C:" + "/Users/",
    "Documents" + "\\Optical Path",
    "Documents" + "/Optical Path",
)
PARTS = ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML")
DRAWING_NAMES = {
    "T1225C": "T1225C.pdf",
    "BA1/M": "BA1_M.pdf",
    "PH75/M": "PH75_M.pdf",
    "TR75/M": "TR75_M.pdf",
    "SM1RC/M": "SM1RC_M.pdf",
    "AC254-045-A-ML": "AC254-045-A-ML.pdf",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path: Path, base: Path, classification: str) -> dict:
    return {
        "relative_path": path.relative_to(base).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "classification": classification,
    }


def copy_public_sources(work: Path, output: Path) -> None:
    metadata = output / "metadata"
    scripts = output / "scripts"
    metadata.mkdir(parents=True, exist_ok=True)
    scripts.mkdir(parents=True, exist_ok=True)
    source_scripts = work if (work / "generate_representative_smoke.py").is_file() else Path(__file__).resolve().parent
    for name in (
        "REPRESENTATIVE_INPUT_LOCK.json",
        "REPRESENTATIVE_CAD_FEATURES.json",
        "CAD_NATIVE_PORT_LOCK.json",
        "CAD_MESH_DERIVATIVES.json",
        "STL_DEGENERATE_AUDIT.json",
        "SM1RC_CLAMP_LOCK.json",
        "OFFICIAL_DRAWING_URL_VERIFY.json",
    ):
        shutil.copy2(work / "measurements" / name, metadata / name)
    shutil.copy2(work / "evidence" / "GENERATOR_REPORT.json", metadata / "GENERATOR_REPORT.json")
    for name in (
        "measure_representative_cad.py",
        "prepare_cad_meshes.py",
        "clean_and_audit_stl.py",
        "measure_sm1rc_clamp_lock.py",
        "generate_representative_smoke.py",
        "audit_reopened_smoke.py",
        "opencv_audit.py",
        "finalize_public_package.py",
        "verify_official_drawings.py",
        "build_representative_params.py",
    ):
        shutil.copy2(source_scripts / name, scripts / name)


def build_sources(root: Path, work: Path, output: Path) -> dict:
    phase1_manifest = load_json(root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json")
    input_lock = load_json(work / "measurements" / "REPRESENTATIVE_INPUT_LOCK.json")
    input_drawings = {item["part_number"]: item for item in input_lock["official_drawing_files"]}
    manifest_records = {item["requested_part_number"]: item for item in phase1_manifest["records"]}
    sources = []
    for part in PARTS:
        item = manifest_records[part]
        step = item["cad_files"][0]
        drawing_catalog = item["cad_pdfs"][0]
        drawing_lock = input_drawings[part]
        drawing_path = work / "vendor_docs" / DRAWING_NAMES[part]
        verified_download = work / "tmp" / "source_url_verify" / ("".join(character if character.isalnum() or character == "-" else "_" for character in part) + ".pdf")
        if sha256(drawing_path) != drawing_lock["sha256"] or drawing_path.stat().st_size != drawing_lock["bytes"]:
            raise RuntimeError(f"official drawing hash/size mismatch: {part}")
        if not verified_download.is_file() or sha256(verified_download) != drawing_lock["sha256"]:
            raise RuntimeError(f"official drawing URL byte verification mismatch: {part}")
        sources.append({
            "part_number": part,
            "official_status": item["official_status"],
            "product_page_url": item["product_page_url"],
            "catalog_metadata_retrieved_utc": item["retrieved_utc"],
            "step": {
                "official_url": step["source_url"],
                "original_filename": step["original_filename"],
                "sha256": step["sha256"],
                "bytes": step["bytes"],
                "transferred_shape_unit": step["bbox"]["unit"],
                "redistribution_decision": "EXCLUDE_FROM_PUBLIC_CANDIDATE",
            },
            "official_drawing": {
                "official_url": drawing_catalog["source_url"],
                "catalog_filename": drawing_catalog["name"],
                "cached_filename_private": drawing_lock["filename"],
                "sha256": drawing_lock["sha256"],
                "bytes": drawing_lock["bytes"],
                "retrieved_utc": datetime.fromtimestamp(drawing_path.stat().st_mtime, timezone.utc).isoformat(),
                "official_url_byte_verification": {
                    "status": "PASS",
                    "verified_sha256": sha256(verified_download),
                    "verified_bytes": verified_download.stat().st_size,
                    "verified_utc": datetime.fromtimestamp(verified_download.stat().st_mtime, timezone.utc).isoformat(),
                },
                "redistribution_decision": "EXCLUDE_FROM_PUBLIC_CANDIDATE",
            },
            "license_and_redistribution_basis": "No explicit vendor-CAD redistribution permission was established; URLs, hashes, and metadata only.",
        })
    return {
        "schema": "opticalmodeler.phase2.representative-sources.v3",
        "status": "PASS",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "phase1_source_lock": {
            "relative_path": "../phase1_source_cad_topology_lock/SOURCE_LOCK.json",
            "sha256": next(item["sha256"] for item in input_lock["phase1_files"] if item["relative_path"] == "SOURCE_LOCK.json"),
        },
        "manufacturer_sources": sources,
        "modeled_non_thorlabs_source": {
            "objects": "generic ISO-like M6 shanks, low-profile/cap heads, and washers",
            "source": "original deterministic script geometry",
            "catalog_claim": False,
        },
    }


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: finalize_public_package.py ROOT")
    root = Path(sys.argv[1]).resolve()
    work = root / "work" / "phase2_representative_smoke_r3"
    output = root / "outputs" / "phase2_representative_smoke_r3"
    phase1 = root / "outputs" / "phase1_source_cad_topology_lock"
    output.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    input_lock = load_json(work / "measurements" / "REPRESENTATIVE_INPUT_LOCK.json")
    phase1_checks = []
    for expected in input_lock["phase1_files"]:
        path = phase1 / expected["relative_path"]
        actual = {"sha256": sha256(path), "bytes": path.stat().st_size}
        passed = actual["sha256"] == expected["sha256"] and actual["bytes"] == expected["bytes"]
        phase1_checks.append({"relative_path": expected["relative_path"], "expected": expected, "actual": actual, "status": "PASS" if passed else "BLOCKED"})
        if not passed:
            failures.append(f"phase1 immutable mismatch: {expected['relative_path']}")

    copy_public_sources(work, output)
    write_json(output / "metadata" / "REPRESENTATIVE_SOURCES.json", build_sources(root, work, output))

    representative = load_json(output / "REPRESENTATIVE_SMOKE_AUDIT.json")
    opencv = load_json(output / "OPENCV_RENDER_AUDIT.json")
    generator = load_json(output / "metadata" / "GENERATOR_REPORT.json")
    stl_audit = load_json(output / "metadata" / "STL_DEGENERATE_AUDIT.json")
    clamp_lock = load_json(output / "metadata" / "SM1RC_CLAMP_LOCK.json")
    stl_parts = {item["part_number"]: item for item in stl_audit["parts"]}
    generator_parts = {item["part_number"]: item for item in generator["official_cad_imports"]}
    reopen_parts = {item["part_number"]: item for item in representative["per_part_face_quality_after_saved_blend_reopen"]["parts"]}
    expected_duplicate_counts = {"T1225C": 0, "BA1/M": 0, "PH75/M": 2, "TR75/M": 8, "SM1RC/M": 2, "AC254-045-A-ML": 0}
    preclean_duplicate_attribution_matches = all(
        stl_parts[part]["pre_clean_private_derivative"]["duplicate_vertex_faces"] == expected
        for part, expected in expected_duplicate_counts.items()
    )
    required_collinear_attribution_matches = (
        stl_parts["SM1RC/M"]["pre_clean_private_derivative"]["distinct_collinear_faces"] == 1
        and stl_parts["TR75/M"]["pre_clean_private_derivative"]["distinct_collinear_faces"] == 24
    )
    postclean_all_zero = all(
        item["post_clean_pre_import_private_derivative"]["duplicate_vertex_faces"] == 0
        and item["post_clean_pre_import_private_derivative"]["distinct_collinear_faces"] == 0
        for item in stl_parts.values()
    )
    blender_import_all_zero = all(
        item["blender_import_face_quality_before_clamp_state"]["invalid_face_count"] == 0
        and item["blender_mesh_face_quality_after_state"]["invalid_face_count"] == 0
        for item in generator_parts.values()
    )
    reopen_all_zero = all(item["invalid_face_count"] == 0 for item in reopen_parts.values())
    retention = representative["narrow_phase_bvh_audit"]["required_retention_contact"]
    clamp_readback = representative["sm1rc_clamped_state_geometry_readback"]
    split_readback = clamp_readback["saved_mesh_split_geometry_readback"]
    analytic_estimate = representative["sm1rc_split_gap_analytic_estimate"]
    status_checks = {
        "representative_smoke": representative["status"] == "PASS",
        "representative_scope_r3": representative["reopen_readback"]["scene_scope"] == "N04_REPRESENTATIVE_ONLY_R3",
        "opencv_render_audit": opencv["status"] == "PASS",
        "opencv_scope_r3": opencv["scope"] == "N04_REPRESENTATIVE_ONLY_R3",
        "generator": generator["status"] == "PASS",
        "generator_scope_r3": generator["scope"] == "N04_REPRESENTATIVE_ONLY_R3",
        "stl_degenerate_audit": stl_audit["status"] == "PASS",
        "sm1rc_clamp_lock": clamp_lock["status"] == "PASS",
        "preclean_duplicate_face_attribution": preclean_duplicate_attribution_matches,
        "preclean_required_collinear_face_attribution": required_collinear_attribution_matches,
        "postclean_invalid_faces_zero_per_part": postclean_all_zero,
        "blender_import_and_post_state_invalid_faces_zero_per_part": blender_import_all_zero,
        "saved_blend_reopen_invalid_faces_zero_per_part": reopen_all_zero,
        "saved_blend_reopen_face_quality_status": representative["per_part_face_quality_after_saved_blend_reopen"]["status"] == "PASS",
        "saved_blend_reopen_status": representative["reopen_readback"]["status"] == "PASS",
        "support_load_path": representative["support_load_path_audit"]["status"] == "PASS",
        "neutral_clearance_rejected_as_contact": retention["neutral_clearance_is_not_contact"] is True,
        "clamped_retention_bvh_contact": retention["status"] == "PASS" and retention["triangle_pair_count"] > 0,
        "clamped_retention_annular_support": retention["annular_support_fraction"] >= retention["minimum_annular_support_fraction"],
        "clamped_geometry_declared_modeled": clamp_readback["manufacturer_supplied_clamped_geometry"] is False,
        "saved_mesh_split_readback": split_readback["status"] == "PASS",
        "saved_mesh_split_checks_all_pass": all(split_readback["checks"].values()),
        "saved_mesh_main_split_measured": split_readback["main_split"]["gap_mm"] is not None,
        "saved_mesh_inner_edge_gap_measured": split_readback["deformed_inner_edge"]["minimum_gap_mm"] is not None,
        "analytic_estimate_not_used_in_geometry_gate": split_readback["analytic_estimate_used_in_geometry_gate"] is False,
        "analytic_estimate_downgraded": analytic_estimate["status"] == "UNVERIFIED_ANALYTIC_ESTIMATE",
        "analytic_estimate_excluded_from_geometry_pass": analytic_estimate["excluded_from_geometry_pass"] is True,
        "no_legacy_residual_split_gap_in_readback": "residual_split_gap_mm" not in clamp_readback,
        "no_legacy_circumferential_takeup_in_readback": "equivalent_circumferential_takeup_mm" not in clamp_readback,
        "clamp_force_and_literal_performance_blocked": clamp_lock["claim_boundary"]["clamp_force_or_literal_performance"] == "BLOCKED",
        "stl_audit_hash_lineage": representative["stl_degenerate_audit_sha256"] == sha256(output / "metadata" / "STL_DEGENERATE_AUDIT.json"),
        "clamp_lock_hash_lineage": representative["sm1rc_clamp_lock_sha256"] == sha256(output / "metadata" / "SM1RC_CLAMP_LOCK.json"),
        "generator_hash_lineage": representative["generator_report_sha256"] == sha256(output / "metadata" / "GENERATOR_REPORT.json"),
        "superseded_r2_gate_blocked": generator["superseded_gate"]["status"] == "BLOCKED" and generator["superseded_gate"]["scope"] == "N04_REPRESENTATIVE_ONLY_R2",
        "overall_model_partial_scoped": representative["global_status_boundaries"]["requested_model"] == "PARTIAL_SCOPED",
        "literal_performance_blocked": representative["global_status_boundaries"]["literal_paper_performance"] == "BLOCKED",
        "full_propagation_unverified": representative["global_status_boundaries"]["full_32_node_propagation"] == "UNVERIFIED",
        "six_official_cad_objects": len(representative["world_mesh_and_bbox_readback"]["parts"]) == 6,
        "zero_undeclared_bvh_pairs": len(representative["narrow_phase_bvh_audit"]["undeclared_opaque_collision_pairs"]) == 0,
        "zero_opaque_ray_hits": representative["zero_radius_ray_audit"]["opaque_hit_count"] == 0,
    }
    failures.extend(f"status disagreement: {name}" for name, passed in status_checks.items() if not passed)

    superseded_manifest = root / "outputs" / "phase2_representative_smoke_r2" / "MANIFEST.json"
    if superseded_manifest.is_file():
        superseded_gate = {
            "schema": "opticalmodeler.phase2.superseded-representative-gate.v2",
            "status": "BLOCKED",
            "scope": "N04_REPRESENTATIVE_ONLY_R2",
            "superseded_by": "N04_REPRESENTATIVE_ONLY_R3",
            "manifest_sha256": sha256(superseded_manifest),
            "manifest_hash_matches_generator_lineage": sha256(superseded_manifest) == generator["superseded_gate"]["manifest_sha256"],
            "reasons": generator["superseded_gate"]["reasons"],
            "core_retention_contact_was_not_the_blocker": True,
            "propagation_authorized": False,
        }
        if not superseded_gate["manifest_hash_matches_generator_lineage"]:
            failures.append("superseded r2 manifest hash mismatch")
    else:
        superseded_gate = {
            "schema": "opticalmodeler.phase2.superseded-representative-gate.v3",
            "status": "UNVERIFIED",
            "scope": "HISTORICAL_N04_R2_NOT_STAGED",
            "applicability": "NOT_APPLICABLE_FRESH_RUN",
            "superseded_source_present": False,
            "reasons": generator["superseded_gate"]["reasons"],
            "propagation_authorized": False,
        }
    write_json(output / "SUPERSEDED_R2_GATE.json", superseded_gate)

    forbidden_files = []
    private_path_hits = []
    json_parse_failures = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "MANIFEST.json"):
        if path.suffix.lower() in FORBIDDEN_FILE_SUFFIXES:
            forbidden_files.append(path.relative_to(output).as_posix())
        if path.suffix.lower() in {".json", ".md", ".py", ".txt"}:
            text = path.read_text(encoding="utf-8")
            for marker in FORBIDDEN_TEXT_MARKERS:
                if marker.lower() in text.lower():
                    private_path_hits.append({"relative_path": path.relative_to(output).as_posix(), "marker": marker})
            if path.suffix.lower() == ".json":
                try:
                    json.loads(text)
                except json.JSONDecodeError as error:
                    json_parse_failures.append({"relative_path": path.relative_to(output).as_posix(), "error": str(error)})
    if forbidden_files:
        failures.append("vendor/archive file type present in public package")
    if private_path_hits:
        failures.append("absolute private path marker present in public package")
    if json_parse_failures:
        failures.append("public JSON parse failure")

    public_audit = {
        "schema": "opticalmodeler.phase2.public-package-audit.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "phase1_immutable_checks": phase1_checks,
        "status_agreement_checks": status_checks,
        "forbidden_vendor_or_archive_files": forbidden_files,
        "absolute_private_path_hits": private_path_hits,
        "json_parse_failures": json_parse_failures,
        "explicit_exclusions": {
            "vendor_step": True,
            "vendor_or_derived_stl": True,
            "vendor_drawings": True,
            "blend_with_vendor_geometry": True,
            "full_32_node_propagation": True,
            "superseded_r2_vendor_geometry": True,
        },
        "global_status_boundaries": {
            "n04_representative_r3_gate": "PASS" if not failures else "BLOCKED",
            "superseded_n04_r2_gate": "BLOCKED",
            "requested_model": "PARTIAL_SCOPED",
            "literal_paper_performance": "BLOCKED",
            "full_32_node_propagation": "UNVERIFIED",
            "vendor_cad_redistribution": "BLOCKED",
        },
        "failures": failures,
    }
    write_json(output / "PUBLIC_PACKAGE_AUDIT.json", public_audit)

    files = []
    for path in sorted(item for item in output.rglob("*") if item.is_file() and item.name != "MANIFEST.json"):
        if path.parts[-2] == "renders":
            classification = "BLENDER_RENDER_EVIDENCE"
        elif path.parts[-2] == "audits" and path.suffix.lower() == ".png":
            classification = "OPENCV_AUDIT_OVERLAY"
        elif "scripts" in path.parts:
            classification = "ORIGINAL_DISTRIBUTABLE_SCRIPT"
        elif "metadata" in path.parts:
            classification = "METADATA_NO_VENDOR_GEOMETRY"
        else:
            classification = "PUBLIC_WALKTHROUGH_OR_AUDIT"
        files.append(record(path, output, classification))
    manifest = {
        "schema": "opticalmodeler.phase2.public-manifest.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "hash_algorithm": "SHA-256",
        "self_hash": "OMITTED_TO_AVOID_RECURSION",
        "artifact_count": len(files),
        "artifacts": files,
        "global_status_boundaries": public_audit["global_status_boundaries"],
    }
    write_json(output / "MANIFEST.json", manifest)

    manifest_readback = load_json(output / "MANIFEST.json")
    manifest_failures = []
    for item in manifest_readback["artifacts"]:
        path = output / item["relative_path"]
        if not path.is_file() or path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            manifest_failures.append(item["relative_path"])
    if manifest_failures:
        raise RuntimeError(f"manifest readback failed: {manifest_failures}")
    if failures:
        raise RuntimeError(f"public package BLOCKED: {failures}")
    print(json.dumps({
        "status": "PASS",
        "phase1_file_checks": len(phase1_checks),
        "public_artifact_count": len(files),
        "forbidden_vendor_or_archive_files": len(forbidden_files),
        "absolute_private_path_hits": len(private_path_hits),
        "manifest_readback_failures": len(manifest_failures),
    }, indent=2))


if __name__ == "__main__":
    main()
