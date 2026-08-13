"""Join OpenCascade readback to the frozen semantic-axis rules before placement."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parents[2]
BASE = ROOT / "work" / "full_32_node_propagation_v3"
MEASUREMENTS = BASE / "measurements"
R3_PORTS = ROOT / "outputs" / "phase2_representative_smoke_r3" / "metadata" / "CAD_NATIVE_PORT_LOCK.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize(values):
    length = math.sqrt(sum(value * value for value in values))
    if length == 0:
        raise ValueError("zero axis")
    return [value / length for value in values]


def main() -> None:
    build_path = BASE / "BUILD_PARAMS.json"
    cad_path = MEASUREMENTS / "FULL_CAD_MESH_AUDIT.json"
    build = read_json(build_path)
    cad = read_json(cad_path)
    r3 = read_json(R3_PORTS)
    if cad["status"] != "PASS":
        raise RuntimeError("full CAD mesh audit is not PASS")
    first_by_part = {}
    for item in cad["parts"]:
        first_by_part.setdefault(item["part_number"], item)
    r3_n04 = next(item for item in r3["parts"] if item["part_number"] == "AC254-045-A-ML")

    nodes = []
    failures = []
    for node in build["nodes"]:
        node_id = node["node_id"]
        part = node["primary_part_number"]
        rule = node["cad_native_semantic_port"]
        if part == "MODELED_EXPERIMENTAL_CHAMBER":
            nodes.append({
                "node_id": node_id, "part_number": part, "status": "PASS",
                "identity": "NON_THORLABS_EXPERIMENTAL_OBJECT_MODELED",
                "native_frame": "modeled metres at deterministic origin",
                "native_origin_mm": [0.0, 0.0, 0.0], "native_axis": [1.0, 0.0, 0.0],
                "clear_aperture_radius_mm": 6.0, "placement_applied": False,
            })
            continue
        item = first_by_part[part]
        bbox = item["opencascade_readback"]["optimal_bbox_mm"]
        minimum, maximum = bbox["min_mm"], bbox["max_mm"]
        center = [(minimum[index] + maximum[index]) / 2.0 for index in range(3)]
        axis = normalize(rule["native_axis"])
        axis_half_extent = sum(abs(axis[index]) * (maximum[index] - minimum[index]) / 2.0 for index in range(3))
        origin = center
        method = (
            "OpenCascade optimal-bbox symmetry center measured in untouched native STEP frame; "
            "semantic axis selected by locked component-family geometry rule"
        )
        inherited = False
        if node_id == "N04":
            origin = r3_n04["native_interfaces"]["optical_axis"]["axis_point_mm"]
            axis = r3_n04["native_interfaces"]["optical_axis"]["axis"]
            axis_half_extent = (
                r3_n04["native_interfaces"]["output_glass_vertex_mm"][0]
                - r3_n04["native_interfaces"]["input_glass_vertex_mm"][0]
            ) / 2.0
            method = "accepted N04 r3 CAD-native optical axis and measured glass vertices; no placement applied"
            inherited = True
        ports = {
            "in_mm": [origin[index] - axis[index] * axis_half_extent for index in range(3)],
            "out_mm": [origin[index] + axis[index] * axis_half_extent for index in range(3)],
        }
        finite = all(math.isfinite(value) for value in origin + axis + ports["in_mm"] + ports["out_mm"])
        local_failures = []
        if not finite:
            local_failures.append("non-finite native transform")
        if rule["clear_aperture_radius_mm"] <= 0:
            local_failures.append("non-positive aperture")
        failures.extend(f"{node_id}: {reason}" for reason in local_failures)
        nodes.append({
            "node_id": node_id,
            "part_number": part,
            "status": "PASS" if not local_failures else "BLOCKED",
            "measurement_method": method,
            "semantic_axis_kind": rule["native_axis_kind"],
            "native_origin_mm": origin,
            "native_axis": axis,
            "native_ports_mm": ports,
            "axis_half_extent_mm": axis_half_extent,
            "clear_aperture_radius_mm": rule["clear_aperture_radius_mm"],
            "opencascade_optimal_bbox_mm": bbox,
            "source_step_sha256": item["official_source"]["sha256"],
            "accepted_n04_r3_transform_inherited": inherited,
            "placement_applied": False,
            "failures": local_failures,
        })
    output = {
        "schema": "opticalmodeler.full32.cad-native-port-lock.v1",
        "status": "PASS" if not failures and len(nodes) == 32 else "BLOCKED",
        "scope": "ALL_32_NODES_PRE_PLACEMENT",
        "cad_native_unit": "millimetre",
        "placement_applied": False,
        "node_count": len(nodes),
        "method_boundary": (
            "Transforms locate semantic optical centers and axes in manufacturer-native CAD. "
            "They do not assert optical prescription, literal literature performance, or unlisted connector tolerances."
        ),
        "n04_r3_port_lock_sha256": sha256(R3_PORTS),
        "full_cad_mesh_audit_sha256": sha256(cad_path),
        "build_params_sha256": sha256(build_path),
        "nodes": nodes,
        "failures": failures,
    }
    destination = MEASUREMENTS / "CAD_NATIVE_PORT_LOCK_FULL.json"
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"], "nodes": len(nodes), "failures": failures,
        "output": str(destination.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2))
    raise SystemExit(0 if output["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
