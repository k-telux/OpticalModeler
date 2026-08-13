"""Create deterministic input, layout, family, and native-port locks.

This script writes only to the new full-propagation revision. Frozen Phase 1
and the current run's N04 representative files are verified and hashed, never
copied back or modified.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def verify_manifest(root: Path, manifest: dict) -> None:
    if manifest.get("status") != "PASS" or manifest.get("scope") != "N04_REPRESENTATIVE_ONLY_R3":
        raise RuntimeError("current-run N04 representative manifest is not PASS")
    artifacts = manifest.get("artifacts", [])
    if manifest.get("artifact_count") != len(artifacts):
        raise RuntimeError("current-run N04 representative manifest count mismatch")
    for record in artifacts:
        path = root / record["relative_path"]
        if not path.is_file() or path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise RuntimeError(f"current-run N04 representative artifact mismatch: {record['relative_path']}")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def rel(path: Path, root: Path) -> str:
    return str(path.relative_to(root)).replace("\\", "/")


def file_record(path: Path, root: Path) -> dict:
    return {"relative_path": rel(path, root), "bytes": path.stat().st_size, "sha256": sha256(path)}


def snapped(x: float, y: float) -> list[float]:
    # Table holes are 25 mm pitch with centers 12.5 mm from the edge.
    gx = -1.2375 + round((x + 1.2375) / 0.025) * 0.025
    gy = -0.5875 + round((y + 0.5875) / 0.025) * 0.025
    return [round(gx, 7), round(gy, 7), 0.125]


FAMILY_BY_NODE = {
    "N01": "SOURCE_LAUNCH", "N02": "SOURCE_LAUNCH",
    "N03": "DICHROIC_KM2536", "N26": "DICHROIC_KM2536", "N29": "DICHROIC_KM2536",
    "N04": "SM1RC_LENS", "N06": "SM1RC_LENS", "N07": "SM1RC_LENS", "N10": "SM1RC_LENS",
    "N05": "PINHOLE_STAGE", "N08": "CYL_LENS_CLR1", "N09": "RESONANT_SCANNER",
    "N11": "GALVO_GHS", "N12": "SM2RC_LENS", "N13": "SM2RC_LENS",
    "N17": "SM2RC_LENS", "N18": "SM2RC_LENS", "N25": "SM2RC_LENS",
    "N14": "OBJECTIVE_SM2RC", "N16": "OBJECTIVE_SM2RC", "N22": "OBJECTIVE_SM2RC",
    "N15": "EXPERIMENTAL_CHAMBER", "N19": "PBS_CUBE",
    "N20": "POLARIS_MIRROR", "N21": "POLARIS_MIRROR", "N28": "POLARIS_MIRROR", "N31": "POLARIS_MIRROR",
    "N23": "WAVEPLATE_RSP1", "N24": "LPS_REMOTE_MIRROR",
    "N27": "FILTER_LMR1", "N30": "FILTER_LMR1", "N32": "CAMERA",
}

PRIMARY_PART = {
    "N01": "RCF15P-P01", "N02": "RCF15P-P01", "N03": "DMLP505R",
    "N04": "AC254-045-A-ML", "N05": "P50K", "N06": "AC254-150-A-ML",
    "N07": "GBE03-A", "N08": "ACY254-050-A", "N09": "GRS8-AG",
    "N10": "AC254-100-A-ML", "N11": "GVS111/M", "N12": "AC508-100-A-ML",
    "N13": "ACT508-200-A-ML", "N14": "N40X-NIR", "N15": "MODELED_EXPERIMENTAL_CHAMBER",
    "N16": "N40X-NIR", "N17": "TTL200-A", "N18": "ACT508-300-A-ML",
    "N19": "CCM1-PBS251/M", "N20": "BB1-E02", "N21": "BB1-E02",
    "N22": "DL20X-PA", "N23": "AQWP10M-580", "N24": "PF03-03-P01",
    "N25": "ACT508-300-A-ML", "N26": "DMLP605R", "N27": "MF525-39",
    "N28": "BB1-E02", "N29": "DMLP605R", "N30": "FELH0650",
    "N31": "BB1-E02", "N32": "CS165MU1/M",
}

# Optical axes/normals are manufacturer-native directions.  The semantic port
# origin is measured from the OpenCascade optimal-bbox center in prepare output;
# no placement, rotation, or scale is applied while making this measurement.
PORT_RULE = {
    "RCF15P-P01": ("axis", [0, 0, 1], 7.5),
    "DMLP505R": ("surface_normal", [0, 0, 1], 10.0),
    "DMLP605R": ("surface_normal", [0, 0, 1], 10.0),
    "AC254-045-A-ML": ("axis", [1, 0, 0], 11.43),
    "AC254-100-A-ML": ("axis", [1, 0, 0], 11.43),
    "AC254-150-A-ML": ("axis", [1, 0, 0], 11.43),
    "P50K": ("axis", [1, 0, 0], 0.025),
    "GBE03-A": ("axis", [0, 0, 1], 3.0),
    "ACY254-050-A": ("axis", [1, 0, 0], 10.0),
    "GRS8-AG": ("scanner_axis", [1, 0, 0], 4.0),
    "GVS111/M": ("scanner_axis", [1, 0, 0], 4.0),
    "AC508-100-A-ML": ("axis", [1, 0, 0], 22.86),
    "ACT508-200-A-ML": ("axis", [0, 0, 1], 22.86),
    "ACT508-300-A-ML": ("axis", [0, 0, 1], 22.86),
    "N40X-NIR": ("axis", [1, 0, 0], 3.0),
    "TTL200-A": ("axis", [0, 0, 1], 20.0),
    "CCM1-PBS251/M": ("cube_axes", [1, 0, 0], 9.0),
    "BB1-E02": ("surface_normal", [0, 0, 1], 11.0),
    "DL20X-PA": ("axis", [0, 0, 1], 3.0),
    "AQWP10M-580": ("axis", [1, 0, 0], 10.0),
    "PF03-03-P01": ("surface_normal", [0, 0, 1], 3.0),
    "MF525-39": ("axis", [0, 0, 1], 10.5),
    "FELH0650": ("axis", [0, 0, 1], 10.5),
    "CS165MU1/M": ("sensor_normal", [0, 0, 1], 2.0),
}

LAYOUT = {
    "N01": (-0.78, 0.47), "N02": (-0.78, 0.13), "N03": (-0.58, 0.30),
    "N04": (-0.40, 0.30), "N05": (-0.22, 0.30), "N06": (-0.04, 0.30),
    "N07": (0.14, 0.30), "N08": (0.32, 0.30), "N09": (0.50, 0.30),
    "N10": (0.68, 0.30), "N11": (0.86, 0.30), "N12": (0.86, 0.12),
    "N13": (0.86, -0.06), "N14": (0.86, -0.24), "N15": (0.86, -0.42),
    "N16": (0.68, -0.42), "N17": (0.50, -0.42), "N18": (0.32, -0.42),
    "N19": (0.14, -0.42), "N20": (-0.04, -0.27), "N21": (-0.04, -0.54),
    "N22": (-0.22, -0.42), "N23": (-0.40, -0.42), "N24": (-0.58, -0.42),
    "N25": (0.32, -0.16), "N26": (0.50, -0.16), "N27": (0.78, -0.02),
    "N28": (1.03, 0.02), "N29": (1.15, -0.16), "N30": (0.70, -0.27),
    "N31": (0.95, -0.42), "N32": (1.15, -0.54),
}

# These are optical port centers, not table-hole anchor centers.  The v2
# clearance repair moved both branch-end assemblies away from the main return
# path; passing them through snapped() silently reconstructed stale positions.
# The override is therefore part of the lock, with its rationale and policy
# serialized into BUILD_PARAMS.  No manual or downstream transform is allowed.
FINAL_PORT_CENTER_OVERRIDES_M = {
    "N30": {
        "world_port_center_m": [0.7125, -0.55, 0.125],
        "reason": "E041 red-filter branch clearance repair retained from the independently audited v2 saved Blend",
        "policy": "EXPLICIT_OPTICAL_PORT_CENTER; DO_NOT_APPLY_TABLE_HOLE_SNAPPING",
    },
    "N31": {
        "world_port_center_m": [0.9625, -0.55, 0.125],
        "reason": "E042 first-hit BB1-E02 endpoint clearance repair retained from the independently audited v2 saved Blend",
        "policy": "EXPLICIT_OPTICAL_PORT_CENTER; DO_NOT_APPLY_TABLE_HOLE_SNAPPING",
    },
}

FAMILIES = {
    "SOURCE_LAUNCH": ["N01", "N02"],
    "DICHROIC_KM2536": ["N03", "N26", "N29"],
    "SM1RC_LENS": ["N04", "N06", "N07", "N10"],
    "PINHOLE_STAGE": ["N05"], "CYL_LENS_CLR1": ["N08"],
    "RESONANT_SCANNER": ["N09"], "GALVO_GHS": ["N11"],
    "SM2RC_LENS": ["N12", "N13", "N17", "N18", "N25"],
    "OBJECTIVE_SM2RC": ["N14", "N16", "N22"], "EXPERIMENTAL_CHAMBER": ["N15"],
    "PBS_CUBE": ["N19"], "POLARIS_MIRROR": ["N20", "N21", "N28", "N31"],
    "WAVEPLATE_RSP1": ["N23"], "LPS_REMOTE_MIRROR": ["N24"],
    "FILTER_LMR1": ["N27", "N30"], "CAMERA": ["N32"],
}


def build_payloads(root: Path, generated_utc: str) -> tuple[dict, dict, dict]:
    """Recompute all lock-stage payloads without writing any files."""
    phase1 = root / "outputs" / "phase1_source_cad_topology_lock"
    r3 = root / "outputs" / "phase2_representative_smoke_r3"
    topology = read_json(phase1 / "TOPOLOGY_MAP.json")
    cad = read_json(phase1 / "CAD_MANIFEST.json")
    r3_manifest = read_json(r3 / "MANIFEST.json")
    if topology["counts"]["nodes"] != 32 or topology["counts"]["directed_edge_traversals"] != 44:
        raise RuntimeError("frozen topology count drift")
    if len(cad["scoped_substitutions"]) != 17:
        raise RuntimeError("frozen substitution count drift")
    verify_manifest(r3, r3_manifest)

    phase1_files = sorted(path for path in phase1.rglob("*") if path.is_file())
    r3_files = [
        r3 / "MANIFEST.json", r3 / "REPRESENTATIVE_SMOKE_AUDIT.json", r3 / "BUILD_PARAMS.json",
        r3 / "metadata" / "CAD_NATIVE_PORT_LOCK.json", r3 / "metadata" / "SM1RC_CLAMP_LOCK.json",
        r3 / "metadata" / "STL_DEGENERATE_AUDIT.json", r3 / "metadata" / "CAD_MESH_DERIVATIVES.json",
        r3 / "PUBLIC_PACKAGE_AUDIT.json",
    ]
    input_lock = {
        "schema": "opticalmodeler.full32.input-lock.v3",
        "generated_utc": generated_utc,
        "status": "PASS",
        "scope": "FULL_32_NODE_PROPAGATION_GATE_ONLY",
        "phase1_immutable": True,
        "n04_r3_immutable": True,
        "phase1_files": [file_record(path, root) for path in phase1_files],
        "n04_r3_files": [file_record(path, root) for path in r3_files],
        "accepted_n04_r3_manifest_sha256": sha256(r3 / "MANIFEST.json"),
        "accepted_n04_r3_public_artifact_count": r3_manifest.get("public_artifact_count"),
        "permission_boundary": {
            "approved": "propagate frozen 32-node topology and N04 r3 assembly root transform",
            "not_approved": ["literal paper performance", "final claim", "release or publication"],
        },
    }

    nodes = []
    topology_nodes = {node["id"]: node for node in topology["nodes"]}
    for node_id in sorted(topology_nodes):
        part = PRIMARY_PART[node_id]
        snapped_position = snapped(*LAYOUT[node_id])
        override = FINAL_PORT_CENTER_OVERRIDES_M.get(node_id)
        position = list(override["world_port_center_m"] if override else snapped_position)
        port = None
        if part in PORT_RULE:
            kind, axis, aperture = PORT_RULE[part]
            port = {
                "measurement_status": "PASS",
                "measurement_note": "frozen topology-space port; CAD-native bbox/port join is independently gated",
                "method": "OpenCascade optimal-bbox center plus family-locked manufacturer-native semantic axis",
                "native_axis_kind": kind,
                "native_axis": axis,
                "clear_aperture_radius_mm": aperture,
                "native_origin_mm": "JOIN_FROM_FULL_CAD_MESH_AUDIT",
                "placement_applied": False,
            }
        nodes.append({
            "node_id": node_id,
            "label": topology_nodes[node_id]["label"],
            "literature_role": topology_nodes[node_id]["literature_role"],
            "frozen_status": topology_nodes[node_id]["status"],
            "family_id": FAMILY_BY_NODE[node_id],
            "primary_part_number": part,
            "support_template": topology_nodes[node_id]["support_template"],
            "world_port_center_m": position,
            "world_port_center_source": "DOCUMENTED_LOCK_OVERRIDE" if override else "TABLE_GRID_SNAPPED_LAYOUT",
            "snapped_layout_candidate_m": snapped_position,
            "documented_port_center_override": override,
            "cad_native_semantic_port": port,
            "branch_membership": topology_nodes[node_id]["branch_membership"],
        })

    family_records = []
    for family_id, node_ids in FAMILIES.items():
        family_records.append({
            "family_id": family_id,
            "node_ids": node_ids,
            "status": "UNVERIFIED",
            "inherited_n04_pass": False,
            "required_independent_gates": [
                "official_cad_bbox_and_scale", "cad_native_semantic_port", "post_and_load_path",
                "pre_import_and_reopen_mesh_cleanliness", "zero_radius_aperture_ray", "narrow_phase_bvh",
            ],
            "n04_root_transform_policy": (
                "N04 uses accepted r3 local assembly root transform; every saved-Blend instance is re-audited"
                if family_id == "SM1RC_LENS" else "NO_N04_PASS_OR_TRANSFORM_INHERITANCE"
            ),
        })
    family_lock = {
        "schema": "opticalmodeler.full32.family-lock.v3",
        "generated_utc": generated_utc,
        "status": "UNVERIFIED",
        "family_count": len(family_records),
        "families": family_records,
        "global_claim_boundary": {
            "requested_model": "PARTIAL_SCOPED",
            "literal_paper_performance": "BLOCKED",
            "full_final_or_release": "BLOCKED",
            "full_final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        },
    }

    build = {
        "schema": "opticalmodeler.full32.build-params.v3",
        "generated_utc": generated_utc,
        "status": "PASS",
        "determinism": {
            "random_seed": 0,
            "manual_unlogged_transforms": 0,
            "documented_port_center_override_count": len(FINAL_PORT_CENTER_OVERRIDES_M),
            "writer_count": 1,
        },
        "documented_port_center_overrides_m": FINAL_PORT_CENTER_OVERRIDES_M,
        "units": {"scene": "metre", "cad_native": "millimetre", "uniform_cad_scale": 0.001},
        "world_frame": topology["coordinate_frame"],
        "table": {
            "part_number": "T1225C", "frame_part_number": "TF1225R7",
            "top_z_m": 0.0, "bounds_m": {"x": [-1.25, 1.25], "y": [-0.6, 0.6], "z_top": 0.0},
            "hole_grid_m": {"pitch": 0.025, "x_first": -1.2375, "y_first": -0.5875},
        },
        "optical_height_m": 0.125,
        "nodes": nodes,
        "edges": topology["edges"],
        "branch_points": topology["branch_points"],
        "source_merges": topology["source_merges"],
        "imaging_relays": topology["imaging_relays"],
        "render": {"engine": "BLENDER_EEVEE", "resolution": [1600, 1000], "transparent": False},
        "audit_thresholds": {
            "blender_bbox_error_mm": 0.50,
            "zero_radius_mechanical_clearance_m": 0.0,
            "port_center_error_mm": 0.05,
            "axis_angular_error_deg": 0.05,
            "load_link_minimum_bvh_pairs": 1,
            "final_invalid_face_count": 0,
        },
        "status_boundaries": {
            "model_scope": "PARTIAL_SCOPED", "literal_paper_performance": "BLOCKED",
            "substitution_count": 17, "S4FC488_source_diagnostics": "PARTIAL_SCOPED",
            "S4FC637_source_diagnostics": "PARTIAL_SCOPED", "final_or_release": "BLOCKED",
            "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        },
    }
    return input_lock, family_lock, build


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_ROOT
    base = root / "work" / "full_32_node_propagation_v3"
    measurements = base / "measurements"
    generated_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    input_lock, family_lock, build = build_payloads(root, generated_utc)
    write_json(measurements / "FULL_INPUT_LOCK.json", input_lock)
    write_json(measurements / "FAMILY_LOCK.json", family_lock)
    write_json(base / "BUILD_PARAMS.json", build)
    print(json.dumps({
        "status": "PASS", "nodes": len(build["nodes"]), "edges": len(build["edges"]),
        "families": len(family_lock["families"]), "substitutions": build["status_boundaries"]["substitution_count"],
        "documented_port_center_overrides": sorted(FINAL_PORT_CENTER_OVERRIDES_M),
        "input_lock": rel(measurements / "FULL_INPUT_LOCK.json", root),
        "family_lock": rel(measurements / "FAMILY_LOCK.json", root),
        "build_params": rel(base / "BUILD_PARAMS.json", root),
    }, indent=2))


if __name__ == "__main__":
    main()
