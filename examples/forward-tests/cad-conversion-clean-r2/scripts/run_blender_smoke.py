#!/usr/bin/env python3
"""Run raw/clean/reopen Blender smoke stages for OCCT-passing representatives."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from lock_runtime import BLENDER_ROOT, sha256, utc_now


ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "work" / "phase2"
PRIVATE = PHASE2 / "private" / "blender_r4"
AUDIT = PHASE2 / "audit"
STAGE_SCRIPT = PHASE2 / "scripts" / "blender_stage.py"
BLENDER_EXE = BLENDER_ROOT / "blender.exe"
OCCT_AUDIT_PATH = AUDIT / "OCCT_XCAF_AUDIT.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def file_record(path: Path) -> dict[str, object]:
    return {"bytes": path.stat().st_size, "sha256": sha256(path), "private": True}


def blender_environment() -> dict[str, str]:
    env = os.environ.copy()
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    state = PRIVATE / "runtime-state"
    for name in ("config", "scripts", "datafiles", "temp"):
        (state / name).mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "PATH": os.pathsep.join((str(BLENDER_ROOT), str(windows / "System32"), str(windows))),
            "BLENDER_USER_CONFIG": str(state / "config"),
            "BLENDER_USER_SCRIPTS": str(state / "scripts"),
            "BLENDER_USER_DATAFILES": str(state / "datafiles"),
            "TMP": str(state / "temp"),
            "TEMP": str(state / "temp"),
            "PYTHONNOUSERSITE": "1",
            "OMP_NUM_THREADS": "1",
        }
    )
    return env


def run_stage(command: list[str], log: Path, timeout: int) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        env=blender_environment(),
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    log.write_text(result.stdout, encoding="utf-8", newline="\n")
    if result.returncode != 0:
        raise RuntimeError(f"Blender stage failed, exit={result.returncode}, private log={relative(log)}")


def audit_signature(audit: dict) -> dict[str, object]:
    return {
        "mesh_object_count": audit["mesh_object_count"],
        "object_name_set_sha256": audit["object_name_set_sha256"],
        "object_name_max_length": audit["object_name_max_length"],
        "unique_material_count": audit["unique_material_count"],
        "material_name_set_sha256": audit["material_name_set_sha256"],
        "totals": audit["totals"],
        "evaluated_world_bbox_m": audit["evaluated_world_bbox_m"],
        "scene_unit_system": audit["scene_unit_system"],
        "scene_unit_scale_length": audit["scene_unit_scale_length"],
        "max_world_scale_abs_error_from_one": audit["max_world_scale_abs_error_from_one"],
        "max_world_axis_abs_error_from_identity": audit["max_world_axis_abs_error_from_identity"],
    }


def max_bbox_error(left: list[float], right: list[float]) -> float:
    if len(left) != 6 or len(right) != 6:
        return math.inf
    return max(abs(a - b) for a, b in zip(left, right))


def cleanup_accounting(raw: dict, clean: dict) -> dict[str, object]:
    operations = clean["operations"]
    removed_vertices = sum(item["actual_bmesh_removed_counts"]["vertices"] for item in operations)
    removed_edges = sum(item["actual_bmesh_removed_counts"]["edges"] for item in operations)
    deleted_faces = sum(item["actual_bmesh_removed_counts"]["polygons"] for item in operations)
    implicit_faces = sum(item["faces_removed_implicitly_by_merge"] for item in operations)
    explicit_faces = sum(item["faces_removed_by_explicit_delete"] for item in operations)
    validate_vertex_delta = sum(item["validate_count_delta"]["vertices"] for item in operations)
    validate_edge_delta = sum(item["validate_count_delta"]["edges"] for item in operations)
    validate_polygon_delta = sum(item["validate_count_delta"]["polygons"] for item in operations)
    expected_vertices = raw["totals"]["vertex_count"] - removed_vertices + validate_vertex_delta
    expected_edges = raw["totals"]["edge_count"] - removed_edges + validate_edge_delta
    expected_polygons = raw["totals"]["polygon_count"] - deleted_faces + validate_polygon_delta
    actual_vertices = clean["after"]["totals"]["vertex_count"]
    actual_edges = clean["after"]["totals"]["edge_count"]
    actual_polygons = clean["after"]["totals"]["polygon_count"]
    no_hidden_topology_operation = all(
        not item["hole_filling_performed"] and not item["cross_object_merge_performed"] for item in operations
    )
    all_changes_attributed = all(item["all_bmesh_count_changes_attributed"] for item in operations)
    fixed_points = all(item["merge_operator_fixed_point_reached"] for item in operations)
    status = (
        "PASS"
        if expected_vertices == actual_vertices
        and expected_edges == actual_edges
        and expected_polygons == actual_polygons
        and no_hidden_topology_operation
        and all_changes_attributed
        else "BLOCKED"
    )
    return {
        "status": status,
        "raw_vertex_count": raw["totals"]["vertex_count"],
        "vertices_removed_by_all_attributed_bmesh_operations": removed_vertices,
        "edges_removed_by_all_attributed_bmesh_operations": removed_edges,
        "validate_vertex_delta": validate_vertex_delta,
        "expected_post_vertex_count": expected_vertices,
        "actual_post_vertex_count": actual_vertices,
        "raw_edge_count": raw["totals"]["edge_count"],
        "validate_edge_delta": validate_edge_delta,
        "expected_post_edge_count": expected_edges,
        "actual_post_edge_count": actual_edges,
        "raw_polygon_count": raw["totals"]["polygon_count"],
        "faces_removed_by_all_attributed_bmesh_operations": deleted_faces,
        "faces_removed_implicitly_during_merge": implicit_faces,
        "faces_removed_by_explicit_degenerate_delete": explicit_faces,
        "validate_polygon_delta": validate_polygon_delta,
        "expected_post_polygon_count": expected_polygons,
        "actual_post_polygon_count": actual_polygons,
        "merge_operator_fixed_point_reached_for_all_objects": fixed_points,
        "hole_filling_performed": False,
        "cross_object_merge_performed": False,
        "all_bmesh_count_changes_attributed": all_changes_attributed,
        "mesh_validate_changed_object_count": sum(bool(item["mesh_validate_reported_change"]) for item in operations),
    }


def verify_runtime() -> dict:
    runtime = load_json(PHASE2 / "RUNTIME_LOCK.json")
    if runtime["status"] != "PASS" or runtime["blender"]["version"] != "4.5.12 LTS":
        raise RuntimeError("Blender runtime lock is not PASS")
    if sha256(BLENDER_EXE) != runtime["blender"]["core_binary"]["sha256"]:
        raise RuntimeError("Blender executable hash changed")
    return runtime


def stage_commands(
    sku: str,
    obj: Path,
    raw_blend: Path,
    clean_blend: Path,
    raw_audit: Path,
    clean_audit: Path,
    reopen_audit: Path,
    render: Path,
) -> tuple[list[str], list[str], list[str]]:
    base = [str(BLENDER_EXE), "--background", "--factory-startup", "--disable-autoexec"]
    raw = base + [
        "--python",
        str(STAGE_SCRIPT),
        "--",
        "--mode",
        "raw",
        "--sku",
        sku,
        "--obj",
        str(obj),
        "--blend",
        str(raw_blend),
        "--audit",
        str(raw_audit),
    ]
    clean = base + [
        str(raw_blend),
        "--python",
        str(STAGE_SCRIPT),
        "--",
        "--mode",
        "clean",
        "--sku",
        sku,
        "--blend",
        str(clean_blend),
        "--audit",
        str(clean_audit),
        "--render",
        str(render),
    ]
    reopen = base + [
        str(clean_blend),
        "--python",
        str(STAGE_SCRIPT),
        "--",
        "--mode",
        "reopen",
        "--sku",
        sku,
        "--audit",
        str(reopen_audit),
    ]
    return raw, clean, reopen


def main() -> int:
    runtime = verify_runtime()
    occt = load_json(OCCT_AUDIT_PATH)
    if len(occt["results"]) != 4:
        raise RuntimeError("OCCT representative count changed")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    AUDIT.mkdir(parents=True, exist_ok=True)
    converted: list[dict[str, object]] = []
    blocked: list[dict[str, object]] = []
    for item in occt["results"]:
        sku = item["sku"]
        slug = re.sub(r"[^A-Za-z0-9]+", "_", sku).strip("_")
        if item["serial_mesh_gate"] != "PASS":
            blocked.append(
                {
                    "sku": sku,
                    "status": "BLOCKED",
                    "reason": "OCCT serial meshing did not achieve NoError with all faces triangulated; Blender import prohibited.",
                    "occt_serial_mesh_result": item["run1"]["serial_mesh_result"],
                    "occt_empty_face_count": item["run1"]["post_mesh_counts"]["empty_face_count"],
                    "blender_executed": False,
                }
            )
            continue
        sku_dir = PRIVATE / slug
        if sku_dir.exists():
            raise RuntimeError(f"canonical Blender directory already exists; fail closed: {relative(sku_dir)}")
        sku_dir.mkdir(parents=True)
        obj = PHASE2 / "private" / "occt_r2" / slug / "run1" / "model.obj"
        if not obj.is_file() or sha256(obj) != item["run1"]["obj"]["sha256"]:
            raise RuntimeError(f"OCCT OBJ handoff mismatch: {sku}")
        raw_blend = sku_dir / "raw.blend"
        clean_blend = sku_dir / "clean.blend"
        raw_audit = sku_dir / "raw_audit.json"
        clean_audit = sku_dir / "clean_audit.json"
        reopen_audit = sku_dir / "reopen_audit.json"
        render = sku_dir / "audit_render.png"
        raw_log = sku_dir / "raw.log"
        clean_log = sku_dir / "clean.log"
        reopen_log = sku_dir / "reopen.log"
        raw_command, clean_command, reopen_command = stage_commands(
            sku, obj, raw_blend, clean_blend, raw_audit, clean_audit, reopen_audit, render
        )
        run_stage(raw_command, raw_log, timeout=3600)
        run_stage(clean_command, clean_log, timeout=7200)
        run_stage(reopen_command, reopen_log, timeout=3600)
        raw = load_json(raw_audit)
        clean = load_json(clean_audit)
        reopen = load_json(reopen_audit)
        raw_reopen_match = audit_signature(raw) == audit_signature(clean["before"])
        clean_reopen_match = audit_signature(clean["after"]) == audit_signature(reopen)
        obj_bbox = item["run1"]["obj"]["vertex_bbox_m"]
        raw_obj_bbox_error = max_bbox_error(raw["evaluated_world_bbox_m"], obj_bbox)
        native_bbox_error = (
            max_bbox_error(raw["evaluated_world_bbox_m"], [value * 0.001 for value in item["run1"]["native_bbox_mm"]])
            if item["run1"]["native_bbox_bounded"]
            else None
        )
        raw_clean_bbox_error = max_bbox_error(raw["evaluated_world_bbox_m"], clean["after"]["evaluated_world_bbox_m"])
        clean_reopen_bbox_error = max_bbox_error(clean["after"]["evaluated_world_bbox_m"], reopen["evaluated_world_bbox_m"])
        bbox_gate = (
            raw_obj_bbox_error <= 2.0e-6
            and (native_bbox_error is None or native_bbox_error <= 2.0e-6)
            and raw_clean_bbox_error <= 1.0e-12
            and clean_reopen_bbox_error <= 1.0e-12
        )
        frame_gate = (
            raw["scene_unit_system"] == "METRIC"
            and math.isclose(raw["scene_unit_scale_length"], 1.0, rel_tol=0.0, abs_tol=1.0e-15)
            and raw["max_world_scale_abs_error_from_one"] <= 1.0e-12
            and raw["max_world_axis_abs_error_from_identity"] <= 1.0e-12
        )
        name_matches = raw["exact_source_group_to_blender_object_name_match_count"]
        source_groups = raw["source_obj_groups"]["unique_group_count"]
        blender_name_status = "PASS" if name_matches == source_groups else "PARTIAL_SCOPED"
        source_colors = item["run1"]["xcaf"]["color_definition_count"]
        blender_materials = raw["unique_material_count"]
        color_count_match = source_colors == blender_materials
        color_status = "PASS" if source_colors == 0 and blender_materials == 0 else "PARTIAL_SCOPED"
        accounting = cleanup_accounting(raw, clean)
        post_defects = clean["after"]["totals"]
        solid_present = item["run1"]["aggregate_topology"]["solid"] > 0
        cleanup_residuals = {
            "exact_duplicate_vertices": post_defects["exact_duplicate_vertex_count_within_object"],
            "zero_area_triangles": post_defects["zero_area_triangle_count_exact"],
            "collinear_triangles": post_defects["collinear_triangle_count_relative"],
            "nonmanifold_edges": post_defects["nonmanifold_edge_count"],
            "orientation_conflict_edges": post_defects["orientation_conflict_edge_count"],
            "loose_edges": post_defects["loose_edge_count"],
            "zero_face_normals": post_defects["zero_face_normal_count"],
            "nonunit_face_normals": post_defects["nonunit_face_normal_count"],
            "open_boundary_edges_for_solid_model": post_defects["open_boundary_edge_count"] if solid_present else 0,
        }
        cleanup_status = "PARTIAL_SCOPED" if any(cleanup_residuals.values()) else "PASS"
        post_finite_gate = post_defects["nonfinite_vertex_count"] == 0
        hard_pass = (
            raw_reopen_match
            and clean_reopen_match
            and bbox_gate
            and frame_gate
            and accounting["status"] == "PASS"
            and post_finite_gate
        )
        scoped_factors = {
            "occt_item_status": item["status"],
            "blender_name_retention": blender_name_status,
            "color_material_retention": color_status,
            "post_cleanup_mesh_status": cleanup_status,
            "semantic_ports": "UNVERIFIED",
        }
        status = "BLOCKED" if not hard_pass else ("PARTIAL_SCOPED" if any(value != "PASS" for value in scoped_factors.values()) else "PASS")
        converted.append(
            {
                "sku": sku,
                "status": status,
                "raw_import": raw,
                "explicit_cleanup": clean,
                "saved_clean_blend_reopen": reopen,
                "raw_blend_reopen_gate": "PASS" if raw_reopen_match else "BLOCKED",
                "saved_clean_blend_reopen_gate": "PASS" if clean_reopen_match else "BLOCKED",
                "bbox_gate": {
                    "status": "PASS" if bbox_gate else "BLOCKED",
                    "raw_vs_occt_derived_obj_max_abs_error_m": raw_obj_bbox_error,
                    "raw_vs_occt_native_brep_max_abs_error_m": native_bbox_error,
                    "raw_vs_clean_max_abs_error_m": raw_clean_bbox_error,
                    "clean_vs_reopen_max_abs_error_m": clean_reopen_bbox_error,
                    "native_brep_reference_status": item["native_bbox_gate"],
                    "tolerance_m": 2.0e-6,
                },
                "unit_scale_axis_gate": "PASS" if frame_gate else "BLOCKED",
                "cleanup_accounting_gate": accounting,
                "retention": {
                    "assembly_or_group_names": blender_name_status,
                    "source_obj_unique_group_count": source_groups,
                    "exact_blender_object_name_match_count": name_matches,
                    "source_xcaf_color_definition_count": source_colors,
                    "blender_unique_material_count": blender_materials,
                    "colors_to_materials": color_status,
                    "color_definition_to_material_count_match": color_count_match,
                    "color_rgba_value_retention": "UNVERIFIED" if source_colors else "NOT_APPLICABLE",
                    "color_face_assignment_retention": "UNVERIFIED" if source_colors else "NOT_APPLICABLE",
                    "hierarchy_claim_limit": "OBJ/Blender group objects do not prove one-to-one XCAF occurrence hierarchy retention.",
                },
                "post_cleanup_status": cleanup_status,
                "post_cleanup_residuals": cleanup_residuals,
                "post_cleanup_nonfinite_vertex_gate": "PASS" if post_finite_gate else "BLOCKED",
                "scoped_factors": scoped_factors,
                "private_files": {
                    "raw_blend": file_record(raw_blend),
                    "clean_blend": file_record(clean_blend),
                    "raw_stage_audit": file_record(raw_audit),
                    "clean_stage_audit": file_record(clean_audit),
                    "reopen_stage_audit": file_record(reopen_audit),
                    "raw_log": file_record(raw_log),
                    "clean_log": file_record(clean_log),
                    "reopen_log": file_record(reopen_log),
                    "audit_render": file_record(render),
                },
                "public_geometry_policy": "OBJ and Blend remain private; only audit metadata, hashes, original scripts, and the original audit render are eligible for the public package.",
            }
        )
        print(json.dumps({"sku": sku, "status": status, "reopen": clean_reopen_match, "bbox": bbox_gate}, sort_keys=True), flush=True)
    hard_converted = all(item["status"] != "BLOCKED" for item in converted)
    overall_status = "BLOCKED" if blocked or not hard_converted else ("PARTIAL_SCOPED" if any(item["status"] == "PARTIAL_SCOPED" for item in converted) else "PASS")
    payload = {
        "schema": "opticalmodeler.phase2_mesh_blender_audit.v1",
        "status": overall_status,
        "generated_at_utc": utc_now(),
        "runtime": {
            "blender_version": runtime["blender"]["version"],
            "blender_exe_sha256": runtime["blender"]["core_binary"]["sha256"],
        },
        "execution_policy": "Raw OBJ import with validate_meshes=false; explicit audited cleanup in a fresh process; saved clean Blend reopened in a third process; no GLB; blocked OCCT meshes are not imported.",
        "rejected_preflight": [
            {
                "status": "REJECTED",
                "reason": "An RMS10X axis probe using NEGATIVE_Y produced a 180-degree Z rotation. Canonical runs use forward_axis=Y, up_axis=Z and require an identity world axis matrix.",
                "private_evidence_retained": True,
            },
            {
                "status": "REJECTED",
                "reason": "Blender r1 cleanup accounting omitted faces and edges removed implicitly by merge-by-distance. Canonical r2 records every pass before merge, after merge, and after explicit delete, and requires zero unattributed count delta.",
                "private_evidence_retained": True,
            },
            {
                "status": "SUPERSEDED_FOR_PUBLIC_SANITIZATION",
                "reason": "An earlier pass used a reserved isolation-token-shaped local variable. The publishable script uses a behavior-equivalent rename and a full three-stage rerun so its hash exactly matches execution.",
                "private_evidence_retained": True,
            },
            {
                "status": "SUPERSEDED_FOR_AUDIT_TIGHTENING",
                "reason": "A prior publishable run used sampled name comparison and count-only color retention. Canonical r4 reruns with complete name sets, color value and face assignment limits, residual mesh classification, and raw-clean-reopen bbox gates.",
                "private_evidence_retained": True,
            },
        ],
        "converted_count": len(converted),
        "blocked_before_blender_count": len(blocked),
        "converted": converted,
        "blocked_before_blender": blocked,
        "script_hashes": {
            "blender_stage_py_sha256": sha256(STAGE_SCRIPT),
            "run_blender_smoke_py_sha256": sha256(Path(__file__)),
        },
        "vendor_and_derived_geometry_publication": "PROHIBITED",
    }
    output = AUDIT / "MESH_AND_BLENDER_AUDIT.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": overall_status, "audit_sha256": sha256(output), "converted": len(converted), "blocked": len(blocked)}, sort_keys=True))
    return 0 if hard_converted else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise
