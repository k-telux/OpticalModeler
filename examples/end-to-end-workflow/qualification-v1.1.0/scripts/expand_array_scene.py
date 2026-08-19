#!/usr/bin/env python3
"""Expand the freshly generated and reopened N04 scene into a rigid station array."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
COUNT = CONFIG["station_count"]
SPACING = CONFIG["station_spacing_m"]
BASE = ROOT / "work" / "array_scale"
SCENE = BASE / "scene"
EVIDENCE = BASE / "evidence"
SCENE.mkdir(parents=True, exist_ok=True)
EVIDENCE.mkdir(parents=True, exist_ok=True)
OUTPUT = SCENE / f"N04_ARRAY_{COUNT}x_GENERATED.blend"

SCIENCE_COLLECTIONS = (
    "OFFICIAL_THORLABS_CAD_PRIVATE",
    "OFFSCENE_OFFICIAL_ELECTRICAL_ENDPOINTS_PRIVATE",
    "MODELED_NON_THORLABS_MECHANICS",
    "AUDIT_OVERLAYS_AND_PRESENTATION_BEAMS",
    "NODE_LABELS",
)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def prefixed(station: str, value: object, kind: str, name_map: dict[str, str] | None = None) -> object:
    if not isinstance(value, str):
        return value
    if kind in {"node_id", "from_node", "to_node", "edge_id", "branch_id"}:
        return f"{station}/{value.split('/', 1)[-1]}"
    if kind in {"from_object", "to_object"}:
        return value if station == "S01" else (name_map or {}).get(value, f"{station}__{value}")
    return value


def translated_json(value: str, offset: Vector, matrix: bool = False) -> str:
    data = json.loads(value)
    if matrix:
        data[0][3] += offset.x
        data[1][3] += offset.y
        data[2][3] += offset.z
    else:
        data[0] += offset.x
        data[1] += offset.y
        data[2] += offset.z
    return json.dumps(data, separators=(",", ":"))


def update_properties(obj: bpy.types.Object, station: str, base_name: str, offset: Vector, name_map: dict[str, str] | None = None) -> None:
    obj["station_id"] = station
    obj["base_object_name"] = base_name
    for key in ("node_id", "from_node", "to_node", "edge_id", "branch_id", "from_object", "to_object"):
        if key in obj:
            obj[key] = prefixed(station, obj[key], key, name_map)
    for key in ("from_surface_vertex_world_m", "to_surface_vertex_world_m"):
        if key in obj:
            obj[key] = translated_json(obj[key], offset)
    if "native_mm_to_world_matrix" in obj:
        obj["native_mm_to_world_matrix"] = translated_json(obj["native_mm_to_world_matrix"], offset, matrix=True)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


base_objects: list[tuple[bpy.types.Object, str]] = []
for collection_name in SCIENCE_COLLECTIONS:
    collection = bpy.data.collections[collection_name]
    base_objects.extend((obj, collection_name) for obj in collection.objects)
base_lights = list(bpy.data.collections["LIGHTING"].objects)
base_min = Vector((math.inf, math.inf, math.inf))
base_max = Vector((-math.inf, -math.inf, -math.inf))
for obj, _ in base_objects:
    for corner in obj.bound_box:
        world = obj.matrix_world @ Vector(corner)
        for axis in range(3):
            base_min[axis] = min(base_min[axis], world[axis])
            base_max[axis] = max(base_max[axis], world[axis])
required_spacing = (base_max.x - base_min.x) + CONFIG.get("clearance_margin_m", 0.25)
if SPACING < required_spacing:
    raise RuntimeError(f"station spacing {SPACING:.6f} m is below reopened-mesh requirement {required_spacing:.6f} m")

for obj, _ in base_objects:
    update_properties(obj, "S01", obj.name, Vector((0.0, 0.0, 0.0)))
for light in base_lights:
    light["station_id"] = "S01"
    light["base_object_name"] = light.name

created = []
for station_index in range(1, COUNT):
    station = f"S{station_index + 1:02d}"
    offset = Vector((station_index * SPACING, 0.0, 0.0))
    collections: dict[str, bpy.types.Collection] = {}
    for collection_name in SCIENCE_COLLECTIONS:
        copy_collection = bpy.data.collections.new(f"{station}__{collection_name}")
        bpy.context.scene.collection.children.link(copy_collection)
        collections[collection_name] = copy_collection
    station_created = []
    name_map = {}
    for original, collection_name in base_objects:
        duplicate = original.copy()
        duplicate.data = original.data
        duplicate.name = f"{station}__{original.name}"
        duplicate.matrix_world = Matrix.Translation(offset) @ original.matrix_world
        collections[collection_name].objects.link(duplicate)
        name_map[original.name] = duplicate.name
        station_created.append((duplicate, original))
        created.append(duplicate)
    for duplicate, original in station_created:
        update_properties(duplicate, station, original.name, offset, name_map)
    light_collection = bpy.data.collections.new(f"{station}__LIGHTING")
    bpy.context.scene.collection.children.link(light_collection)
    for original in base_lights:
        duplicate = original.copy()
        duplicate.data = original.data.copy()
        duplicate.name = f"{station}__{original.name}"
        duplicate.matrix_world = Matrix.Translation(offset) @ original.matrix_world
        duplicate["station_id"] = station
        duplicate["base_object_name"] = original.name
        light_collection.objects.link(duplicate)

camera_collection = bpy.data.collections.get("CAMERAS")
center = Vector((((COUNT - 1) * SPACING) / 2.0, -0.10, -0.22))
span = (COUNT - 1) * SPACING + 2.7
camera_specs = [
    ("CAM_ARRAY_PERSPECTIVE", center + Vector((0.0, -max(5.2, span * 0.78), max(3.5, span * 0.55))), 52.0, None),
    ("CAM_ARRAY_TOP", center + Vector((0.0, 0.0, max(6.5, span))), 50.0, span / 1.48),
    ("CAM_ARRAY_FIRST", Vector((0.0, -2.7, 2.55)), 54.0, None),
    ("CAM_ARRAY_LAST", Vector(((COUNT - 1) * SPACING, -2.7, 2.55)), 54.0, None),
]
for name, location, lens, ortho_scale in camera_specs:
    data = bpy.data.cameras.new(name + "_DATA")
    data.lens = lens
    if ortho_scale is not None:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    camera = bpy.data.objects.new(name, data)
    camera.location = location
    look_at(camera, center if "ARRAY_" in name and name not in {"CAM_ARRAY_FIRST", "CAM_ARRAY_LAST"} else Vector((location.x, -0.1, -0.22)))
    camera_collection.objects.link(camera)

scene = bpy.context.scene
input_blend = Path(bpy.data.filepath).name
scene["array_run_id"] = CONFIG["run_id"]
scene["array_station_count"] = COUNT
scene["array_station_spacing_m"] = SPACING
scene["array_total_node_count"] = CONFIG["total_nodes"]
scene["array_total_directed_edges"] = CONFIG["total_directed_edges"]
scene["array_expected_official_instances"] = 154 * COUNT
scene["array_expected_modeled_load_links"] = 156 * COUNT
scene["array_scope"] = "MULTI_STATION_SCALE_QUALIFICATION_NOT_LITERAL_PAPER_SYSTEM"
scene["array_model_scope_status"] = "PARTIAL_SCOPED"
scene["array_final_or_release"] = False
scene["array_base_regression_sha256"] = digest(ROOT / "work" / "full_32_node_propagation_v3" / "evidence" / "REOPEN_FULL_REGRESSION.json")
scene.camera = bpy.data.objects["CAM_ARRAY_PERSPECTIVE"]
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), check_existing=False)

report = {
    "schema": "opticalmodeler.n04-array-generator-report.v1",
    "status": "PASS",
    "scope": scene["array_scope"],
    "run_id": CONFIG["run_id"],
    "blender_version": bpy.app.version_string,
    "input_base_blend": input_blend,
    "output_blend": OUTPUT.relative_to(ROOT).as_posix(),
    "station_count": COUNT,
    "station_spacing_m": SPACING,
    "base_station_world_bbox_m": {"min": list(base_min), "max": list(base_max)},
    "required_spacing_m": required_spacing,
    "spacing_preflight": "PASS",
    "base_science_object_count": len(base_objects),
    "created_science_object_count": len(created),
    "total_science_object_count": len(base_objects) * COUNT,
    "total_nodes": CONFIG["total_nodes"],
    "total_directed_edges": CONFIG["total_directed_edges"],
    "official_instances": 154 * COUNT,
    "modeled_load_links": 156 * COUNT,
    "data_policy": "LINKED_IDENTICAL_MESH_DATABLOCKS_WITH_RIGID_WORLD_TRANSLATION",
    "base_regression_sha256": scene["array_base_regression_sha256"],
    "final_or_release": False,
}
(EVIDENCE / "ARRAY_GENERATOR_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
