"""Lock the official SM1RC/M clamping mechanism and modeled clamped state.

This does not claim a manufacturer-specified clamp force. It establishes the
native locking-screw geometry and the exact contact state that the Blender/BVH
audit must independently reproduce. Circumferential take-up is retained only
as an explicitly unverified analytic estimate; it is not saved-mesh evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


CONTACT_INTERFERENCE_MM = 0.005
MIN_ANNULAR_SUPPORT_FRACTION = 0.25


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def close(first: float, second: float, tolerance: float = 1e-4) -> bool:
    return abs(first - second) <= tolerance


def features_by_part(data: dict, part_number: str) -> list[dict]:
    part = next(item for item in data["parts"] if item["part_number"] == part_number)
    return [item["feature"] for item in part["selected_native_features"]]


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: measure_sm1rc_clamp_lock.py ROOT")
    root = Path(sys.argv[1]).resolve()
    work = root / "work" / "phase2_representative_smoke_r3"
    measurements = work / "measurements"
    cad_features_path = measurements / "REPRESENTATIVE_CAD_FEATURES.json"
    input_lock_path = measurements / "REPRESENTATIVE_INPUT_LOCK.json"
    cad_features = load_json(cad_features_path)
    input_lock = load_json(input_lock_path)
    sm1rc = features_by_part(cad_features, "SM1RC/M")
    lens = features_by_part(cad_features, "AC254-045-A-ML")

    bore_faces = [
        item for item in sm1rc
        if item["type"] == "CYLINDER"
        and close(item.get("radius_mm", 0.0), 15.3035)
        and abs(item["axis_direction"][2]) >= 0.9999
    ]
    bore_radii = sorted({item["radius_mm"] for item in bore_faces})
    split_planes = sorted(
        (
            item for item in sm1rc
            if item["type"] == "PLANE"
            and abs(item["normal"][0]) >= 0.9999
            and close(abs(item["origin_mm"][0]), 0.79375)
            and item["bbox"]["min_mm"][1] > 15.0
            and item["bbox"]["min_mm"][2] <= 5.08 <= item["bbox"]["max_mm"][2]
        ),
        key=lambda item: item["origin_mm"][0],
    )
    locking_screw_cylinders = [
        item for item in sm1rc
        if item["type"] == "CYLINDER"
        and abs(item["axis_direction"][0]) >= 0.9999
        and close(item["axis_origin_mm"][1], 19.05)
        and close(item["axis_origin_mm"][2], 5.08)
        and 1.9 <= item.get("radius_mm", 0.0) <= 2.2
    ]
    lens_outer_faces = [
        item for item in lens
        if item["type"] == "CYLINDER"
        and close(item.get("radius_mm", 0.0), 15.24)
        and abs(item["axis_direction"][0]) >= 0.9999
        and item["area_mm2"] > 500.0
    ]

    failures = []
    if bore_radii != [15.3035] or len(bore_faces) < 2:
        failures.append("SM1RC/M native bore radius not uniquely established")
    if len(split_planes) != 2:
        failures.append("SM1RC/M two split faces not uniquely established")
    if len(locking_screw_cylinders) < 4:
        failures.append("M4 locking screw/through-axis cylinders not established")
    if len(lens_outer_faces) != 2:
        failures.append("AC254-045-A-ML outer clamping cylinder not established")
    if failures:
        raise RuntimeError(failures)

    bore_radius = bore_radii[0]
    lens_radius = 15.24
    neutral_radial_clearance = bore_radius - lens_radius
    target_clamped_bore_radius = lens_radius - CONTACT_INTERFERENCE_MM
    required_radial_deflection = bore_radius - target_clamped_bore_radius
    required_circumferential_takeup = 2.0 * math.pi * required_radial_deflection
    split_coordinates = [item["origin_mm"][0] for item in split_planes]
    neutral_split_gap = split_coordinates[1] - split_coordinates[0]
    residual_split_gap = neutral_split_gap - required_circumferential_takeup
    screw_axis_y = sum(item["axis_origin_mm"][1] for item in locking_screw_cylinders) / len(locking_screw_cylinders)
    screw_axis_z = sum(item["axis_origin_mm"][2] for item in locking_screw_cylinders) / len(locking_screw_cylinders)
    screw_crosses_both_split_faces = all(
        item["bbox"]["min_mm"][1] <= screw_axis_y <= item["bbox"]["max_mm"][1]
        and item["bbox"]["min_mm"][2] <= screw_axis_z <= item["bbox"]["max_mm"][2]
        for item in split_planes
    )
    screw_body_bridges_split = any(
        item["bbox"]["min_mm"][0] < split_coordinates[0]
        and item["bbox"]["max_mm"][0] > split_coordinates[1]
        for item in locking_screw_cylinders
    )
    if neutral_radial_clearance <= 0:
        failures.append("neutral fit is not a clearance fit")
    if required_radial_deflection <= 0:
        failures.append("modeled contact requires non-positive radial deflection")
    if not screw_crosses_both_split_faces or not screw_body_bridges_split:
        failures.append("M4 locking-screw geometry does not bridge the split")

    drawing_locks = {item["part_number"]: item for item in input_lock["official_drawing_files"]}
    report = {
        "schema": "opticalmodeler.phase2.sm1rc-clamp-lock.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "claim_boundary": {
            "geometric_retention_state": "GATED",
            "manufacturer_native_neutral_geometry": "PRESERVED_IN_PRE_DEFORMATION_AUDIT",
            "clamped_state_geometry": "MODELED_ELASTIC_DEFLECTION_OF_OFFICIAL_CAD_DERIVATIVE",
            "clamp_force_or_literal_performance": "BLOCKED",
        },
        "official_drawing_evidence": {
            "SM1RC/M": {
                "sha256": drawing_locks["SM1RC/M"]["sha256"],
                "statements": ["accepts SM1 series lens tubes", "30.6 mm nominal bore", "M4 locking screw"],
            },
            "AC254-045-A-ML": {
                "sha256": drawing_locks["AC254-045-A-ML"]["sha256"],
                "statements": ["30.5 mm nominal mount outside diameter"],
            },
        },
        "native_features_before_placement": {
            "sm1rc_bore_axis": [0.0, 0.0, 1.0],
            "sm1rc_bore_radius_mm": bore_radius,
            "ac254_mount_outer_radius_mm": lens_radius,
            "neutral_radial_clearance_mm": neutral_radial_clearance,
            "split_face_x_mm": split_coordinates,
            "neutral_split_gap_mm": neutral_split_gap,
            "locking_screw_axis_origin_mm": [0.0, screw_axis_y, screw_axis_z],
            "locking_screw_axis_direction": [1.0, 0.0, 0.0],
            "locking_screw_nominal_thread": "M4",
            "locking_screw_crosses_both_split_faces": screw_crosses_both_split_faces,
            "locking_screw_body_bridges_split": screw_body_bridges_split,
        },
        "modeled_clamped_state": {
            "target_bore_radius_mm": target_clamped_bore_radius,
            "numerical_contact_interference_mm": CONTACT_INTERFERENCE_MM,
            "required_inward_radial_deflection_mm": required_radial_deflection,
            "deformation_rule": "move only vertices on the measured 15.3035 mm cylindrical bore radially to 15.235 mm; retain all other official-CAD vertices",
            "minimum_annular_support_fraction": MIN_ANNULAR_SUPPORT_FRACTION,
            "required_scene_evidence": [
                "SM1RC/M-to-AC254 BVH contact exists",
                "radial interference is 0.005 mm within tolerance",
                "contact angular support fraction >= 0.25",
                "main split gap is measured from the saved-Blend reopened evaluated mesh",
                "deformed inner-edge minimum gap is measured from the saved-Blend reopened evaluated mesh",
                "locking-screw axis crosses and bridges the split"
            ],
        },
        "analytic_split_gap_estimate": {
            "status": "UNVERIFIED_ANALYTIC_ESTIMATE",
            "excluded_from_geometry_pass": True,
            "method": "neutral split gap minus 2*pi times required inward radial deflection",
            "equivalent_circumferential_takeup_estimate_mm": required_circumferential_takeup,
            "residual_split_gap_estimate_mm": residual_split_gap,
            "reason": "the generator deforms only selected bore vertices; this uniform-circumference estimate is not applied to the saved mesh",
        },
        "source_measurement_hashes": {
            "REPRESENTATIVE_CAD_FEATURES.json": sha256(cad_features_path),
            "REPRESENTATIVE_INPUT_LOCK.json": sha256(input_lock_path),
        },
        "failures": failures,
    }
    output = measurements / "SM1RC_CLAMP_LOCK.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "neutral_radial_clearance_mm": neutral_radial_clearance,
        "required_radial_deflection_mm": required_radial_deflection,
        "neutral_split_gap_mm": neutral_split_gap,
        "analytic_split_gap_estimate_status": "UNVERIFIED_ANALYTIC_ESTIMATE",
        "residual_split_gap_estimate_mm": residual_split_gap,
        "locking_screw_crosses_and_bridges_split": screw_crosses_both_split_faces and screw_body_bridges_split,
        "failures": failures,
    }, indent=2))
    raise SystemExit(0 if not failures else 2)


if __name__ == "__main__":
    main()
