#!/usr/bin/env python3
"""Derive representative build parameters from current-run reopen evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_representative_params.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    work = root / "work" / "phase2_representative_smoke_r3"
    output = root / "outputs" / "phase2_representative_smoke_r3"
    audit = load(output / "REPRESENTATIVE_SMOKE_AUDIT.json")
    clamp = load(work / "measurements" / "SM1RC_CLAMP_LOCK.json")
    stl = load(work / "measurements" / "STL_DEGENERATE_AUDIT.json")
    generator = load(work / "evidence" / "GENERATOR_REPORT.json")
    input_lock = load(work / "measurements" / "REPRESENTATIVE_INPUT_LOCK.json")
    gap = audit["sm1rc_clamped_state_geometry_readback"]
    split = gap["saved_mesh_split_geometry_readback"]
    per_part = {item["part_number"]: item for item in stl["parts"]}

    params = {
        "schema": "opticalmodeler.phase2.representative-build-params.v4",
        "status": "PASS",
        "scope": "N04_REPRESENTATIVE_ONLY_R3_CURRENT_RUN",
        "global_status_boundaries": audit["global_status_boundaries"],
        "superseded_r2": {
            "status": generator["superseded_gate"]["status"],
            "propagation_authorized": False,
            "source_staged_in_current_run": False,
        },
        "determinism": {
            "manual_unlogged_transforms": False,
            "randomness_used": False,
            "fixed_seed": None,
            "coordinate_source": "metadata/CAD_NATIVE_PORT_LOCK.json",
            "scene_units": "metre",
            "cad_and_evaluated_local_mesh_units": "millimetre",
        },
        "representative_node": input_lock["representative_node"],
        "sm1rc_clamp_model": {
            "component_identity": gap["component_identity"],
            "manufacturer_supplied_clamped_geometry": gap["manufacturer_supplied_clamped_geometry"],
            "geometry_state": gap["geometry_state"],
            "neutral_bore_radius_mm": clamp["native_features_before_placement"]["sm1rc_bore_radius_mm"],
            "lens_mount_radius_mm": clamp["native_features_before_placement"]["ac254_mount_outer_radius_mm"],
            "neutral_radial_clearance_mm": gap["neutral_radial_clearance_mm"],
            "neutral_clearance_is_contact": False,
            "target_bore_radius_mm": clamp["modeled_clamped_state"]["target_bore_radius_mm"],
            "required_inward_radial_deflection_mm": clamp["modeled_clamped_state"]["required_inward_radial_deflection_mm"],
            "numerical_contact_interference_mm": clamp["modeled_clamped_state"]["numerical_contact_interference_mm"],
            "deformed_vertex_count": gap["selected_clamped_bore_vertex_count"],
            "claim_boundary": gap["claim_boundary"],
        },
        "saved_mesh_split_gap_gate": {
            "measurement_source": split["measurement_source"],
            "coordinate_frame": split["coordinate_frame"],
            "coordinate_tolerance_mm": split["selection_rule"]["coordinate_tolerance_mm"],
            "gap_tolerance_mm": split["selection_rule"]["gap_tolerance_mm"],
            "minimum_open_gap_mm": 0.5,
            "observed_main_split_gap_mm": split["main_split"]["gap_mm"],
            "observed_deformed_inner_edge_minimum_gap_mm": split["deformed_inner_edge"]["minimum_gap_mm"],
            "analytic_estimate_used_in_geometry_gate": split["analytic_estimate_used_in_geometry_gate"],
        },
        "analytic_split_gap_estimate": audit["sm1rc_split_gap_analytic_estimate"],
        "per_part_invalid_face_gate": {
            "pre_clean_duplicate_vertex_faces": {part: value["pre_clean_private_derivative"]["duplicate_vertex_faces"] for part, value in per_part.items()},
            "pre_clean_distinct_collinear_faces": {part: value["pre_clean_private_derivative"]["distinct_collinear_faces"] for part, value in per_part.items()},
            "required_invalid_faces_per_part_after_cleanup_import_state_and_reopen": 0,
        },
        "geometry_gates": {
            "opencascade_bbox_method": "BRepBndLib.AddOptimal_s(useTriangulation=false,useShapeTolerance=false)",
            "bbox_tolerance_mm": generator["bbox_tolerance_mm"],
            "uniform_cad_mm_to_world_m_scale": 0.001,
            "ray_radius_m": 0.0,
            "clear_aperture_radius_mm": audit["zero_radius_ray_audit"]["clear_aperture_radius_mm"],
            "bvh_space": "evaluated world mesh",
            "bvh_physical_object_count": audit["narrow_phase_bvh_audit"]["physical_object_count"],
            "minimum_annular_support_fraction": clamp["modeled_clamped_state"]["minimum_annular_support_fraction"],
        },
        "render": {
            "blender_version": generator["blender_version"],
            "engine": "BLENDER_EEVEE",
            "resolution_px": [audit["render_evidence"][0]["width"], audit["render_evidence"][0]["height"]],
            "views": ["side", "axial"],
        },
    }
    destination = output / "BUILD_PARAMS.json"
    destination.write_text(json.dumps(params, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": params["status"], "output": "outputs/phase2_representative_smoke_r3/BUILD_PARAMS.json"}, indent=2))


if __name__ == "__main__":
    main()
