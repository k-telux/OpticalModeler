#!/usr/bin/env python3
"""First factory reopen audit for a scaled N04 station array."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
COUNT = CONFIG["station_count"]
SPACING = CONFIG["station_spacing_m"]
BASE = ROOT / "work" / "array_scale"
SCENE = BASE / "scene"
EVIDENCE = BASE / "evidence"
OUTPUT = SCENE / f"N04_ARRAY_{COUNT}x_AUDITED.blend"
REPORT = EVIDENCE / "ARRAY_REOPEN_AUDIT.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def matrix_error(a, b) -> float:
    return max(abs(a[row][column] - b[row][column]) for row in range(4) for column in range(4))


def scientific(obj: bpy.types.Object) -> bool:
    return obj.type in {"MESH", "FONT"} and "station_id" in obj and "base_object_name" in obj


science = [obj for obj in bpy.data.objects if scientific(obj)]
stations = {f"S{index + 1:02d}": [] for index in range(COUNT)}
failures = []
expected_opened = (SCENE / f"N04_ARRAY_{COUNT}x_GENERATED.blend").resolve()
actual_opened = Path(bpy.data.filepath).resolve()
if actual_opened != expected_opened:
    failures.append(f"wrong opened blend: {actual_opened.name} != {expected_opened.name}")
for obj in science:
    station = obj["station_id"]
    if station not in stations:
        failures.append(f"unexpected station id {station}: {obj.name}")
        continue
    stations[station].append(obj)

base = {obj["base_object_name"]: obj for obj in stations["S01"]}
expected_base_count = len(base)
station_records = []
bounds = {}
for index, (station, objects) in enumerate(stations.items()):
    offset = Vector((index * SPACING, 0.0, 0.0))
    station_failures = []
    minimum = Vector((math.inf, math.inf, math.inf))
    maximum = Vector((-math.inf, -math.inf, -math.inf))
    for obj in objects:
        base_name = obj["base_object_name"]
        reference = base.get(base_name)
        if reference is None:
            station_failures.append(f"missing base reference: {obj.name} -> {base_name}")
            continue
        expected = reference.matrix_world.copy()
        expected.translation += offset
        error = matrix_error(obj.matrix_world, expected)
        if error > 2e-6:
            station_failures.append(f"matrix drift {obj.name}: {error}")
        if obj.data is not reference.data:
            station_failures.append(f"mesh/data lineage drift: {obj.name}")
        for key in ("from_surface_vertex_world_m", "to_surface_vertex_world_m"):
            if key not in obj or key not in reference:
                continue
            actual = Vector(json.loads(obj[key]))
            source = Vector(json.loads(reference[key])) + offset
            if (actual - source).length > 2e-6:
                station_failures.append(f"world-point drift {obj.name} {key}")
        for key in ("from_object", "to_object"):
            if key in obj and bpy.data.objects.get(obj[key]) is None:
                station_failures.append(f"unresolved object reference {obj.name} {key}={obj[key]}")
        for corner in obj.bound_box:
            world = obj.matrix_world @ Vector(corner)
            for axis in range(3):
                minimum[axis] = min(minimum[axis], world[axis])
                maximum[axis] = max(maximum[axis], world[axis])
    node_ids = {obj["node_id"] for obj in objects if "node_id" in obj and str(obj["node_id"]).split("/", 1)[-1].startswith("N")}
    edge_ids = {obj["edge_id"] for obj in objects if "edge_id" in obj}
    official = sum("official_thorlabs_component_identity" in obj for obj in objects)
    load_links = sum("from_object" in obj and "to_object" in obj for obj in objects)
    expected_node_ids = {f"{station}/N{number:02d}" for number in range(1, 33)}
    expected_edge_ids = {f"{station}/E{number:03d}" for number in range(1, 45)}
    checks = {
        "object_count_matches_base": len(objects) == expected_base_count,
        "node_ids_exact": node_ids == expected_node_ids,
        "edge_ids_exact": edge_ids == expected_edge_ids,
        "official_instances_154": official == 154,
        "modeled_load_links_156": load_links == 156,
        "rigid_translation_and_shared_data": not station_failures,
    }
    if not all(checks.values()):
        failures.extend(f"{station}: {message}" for message in station_failures)
        failures.extend(f"{station}: failed {key}" for key, value in checks.items() if not value)
    bounds[station] = (minimum, maximum)
    station_records.append({
        "station_id": station,
        "offset_m": list(offset),
        "science_objects": len(objects),
        "unique_node_ids": len(node_ids),
        "unique_edge_ids": len(edge_ids),
        "official_instances": official,
        "modeled_load_links": load_links,
        "world_bbox_m": {"min": list(minimum), "max": list(maximum)},
        "checks": checks,
        "failures": station_failures,
    })

cross_station = []
for index in range(COUNT - 1):
    left, right = f"S{index + 1:02d}", f"S{index + 2:02d}"
    gap = bounds[right][0].x - bounds[left][1].x
    cross_station.append({"left": left, "right": right, "x_gap_m": gap, "status": "PASS" if gap > 0.25 else "BLOCKED"})
    if gap <= 0.25:
        failures.append(f"cross-station gap too small: {left}/{right} {gap}")

base_reopen_path = ROOT / "work" / "full_32_node_propagation_v3" / "evidence" / "REOPEN_FULL_REGRESSION.json"
base_second_path = ROOT / "work" / "full_32_node_propagation_v3" / "evidence" / "GATE_BLEND_SECOND_REOPEN.json"
base_reopen = json.loads(base_reopen_path.read_text(encoding="utf-8"))
base_second = json.loads(base_second_path.read_text(encoding="utf-8"))
if base_reopen["status"] != "PASS" or base_reopen["failures"]:
    failures.append("fresh same-run base reopen did not pass")
if base_second["status"] != "PASS" or base_second["failures"]:
    failures.append("fresh same-run base second reopen did not pass")
if base_second["all_used_mesh_invalid_faces_total"] != 0:
    failures.append("fresh same-run base mesh invalid faces are nonzero")

scene = bpy.context.scene
scene["array_reopen_status"] = "PASS" if not failures else "BLOCKED"
report = {
    "schema": "opticalmodeler.n04-array-reopen-audit.v1",
    "status": "PASS" if not failures else "BLOCKED",
    "scope": scene.get("array_scope"),
    "run_id": CONFIG["run_id"],
    "blender_version": bpy.app.version_string,
    "opened_blend": actual_opened.relative_to(ROOT).as_posix(),
    "opened_blend_sha256": digest(actual_opened),
    "expected_opened_blend": expected_opened.relative_to(ROOT).as_posix(),
    "station_count": COUNT,
    "science_object_count": len(science),
    "total_nodes": len({obj["node_id"] for obj in science if "node_id" in obj and str(obj["node_id"]).split("/", 1)[-1].startswith("N")}),
    "total_directed_edges": len({obj["edge_id"] for obj in science if "edge_id" in obj}),
    "official_instances": sum("official_thorlabs_component_identity" in obj for obj in science),
    "modeled_load_links": sum("from_object" in obj and "to_object" in obj for obj in science),
    "unique_serialized_meshes": len({obj.data for obj in science if obj.type == "MESH"}),
    "mesh_evidence": {
        "method": "ALL_REPLICAS_SHARE_THE_FRESH_SAME_RUN_BASE_MESH_DATABLOCKS_AND_RIGID_TRANSLATIONS",
        "fresh_base_reopen_sha256": digest(base_reopen_path),
        "fresh_base_second_reopen_sha256": digest(base_second_path),
        "post_clean_invalid_faces": base_second["all_used_mesh_invalid_faces_total"],
    },
    "station_records": station_records,
    "cross_station_separation": cross_station,
    "status_boundaries": {
        "model_scope": "PARTIAL_SCOPED",
        "literal_paper_multi_station_system": "BLOCKED_NOT_CLAIMED",
        "visual_evidence": "PENDING_SECOND_REOPEN",
        "final_or_release": False,
    },
    "failures": failures,
}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
if failures:
    print(json.dumps(report, indent=2))
    raise RuntimeError(f"array reopen audit failed: {len(failures)}")
scene["array_reopen_audit_sha256"] = digest(REPORT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), check_existing=False)
print(json.dumps({"status": report["status"], "stations": COUNT, "nodes": report["total_nodes"], "edges": report["total_directed_edges"], "official_instances": report["official_instances"], "modeled_load_links": report["modeled_load_links"], "output": OUTPUT.relative_to(ROOT).as_posix()}, indent=2))
