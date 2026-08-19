#!/usr/bin/env python3
"""Second factory reopen and render gate for the scaled N04 station array."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
COUNT = CONFIG["station_count"]
BASE = ROOT / "work" / "array_scale"
EVIDENCE = BASE / "evidence"
RENDERS = EVIDENCE / "renders"
RENDERS.mkdir(parents=True, exist_ok=True)
REPORT = EVIDENCE / "ARRAY_SECOND_REOPEN.json"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def scientific(obj: bpy.types.Object) -> bool:
    return obj.type in {"MESH", "FONT"} and "station_id" in obj and "base_object_name" in obj


failures = []
scene = bpy.context.scene
expected_opened = (BASE / "scene" / f"N04_ARRAY_{COUNT}x_AUDITED.blend").resolve()
actual_opened = Path(bpy.data.filepath).resolve()
if actual_opened != expected_opened:
    failures.append(f"wrong opened blend: {actual_opened.name} != {expected_opened.name}")
expected_properties = {
    "array_run_id": CONFIG["run_id"],
    "array_station_count": COUNT,
    "array_total_node_count": CONFIG["total_nodes"],
    "array_total_directed_edges": CONFIG["total_directed_edges"],
    "array_expected_official_instances": 154 * COUNT,
    "array_expected_modeled_load_links": 156 * COUNT,
    "array_reopen_status": "PASS",
}
readback = {key: scene.get(key) for key in expected_properties}
for key, expected in expected_properties.items():
    if readback[key] != expected:
        failures.append(f"scene property drift {key}: {readback[key]!r} != {expected!r}")
science = [obj for obj in bpy.data.objects if scientific(obj)]
stations = {obj["station_id"] for obj in science}
nodes = {obj["node_id"] for obj in science if "node_id" in obj and str(obj["node_id"]).split("/", 1)[-1].startswith("N")}
edges = {obj["edge_id"] for obj in science if "edge_id" in obj}
official = sum("official_thorlabs_component_identity" in obj for obj in science)
load_links = sum("from_object" in obj and "to_object" in obj for obj in science)
checks = {
    "station_ids_exact": stations == {f"S{index + 1:02d}" for index in range(COUNT)},
    "node_count_exact": len(nodes) == 32 * COUNT,
    "edge_count_exact": len(edges) == 44 * COUNT,
    "official_instance_count_exact": official == 154 * COUNT,
    "modeled_load_link_count_exact": load_links == 156 * COUNT,
}
failures.extend(f"failed {key}" for key, value in checks.items() if not value)

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1600
scene.render.resolution_y = 950
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"
exposures = {"CAM_ARRAY_PERSPECTIVE": 0.0, "CAM_ARRAY_TOP": -1.05, "CAM_ARRAY_FIRST": 0.0, "CAM_ARRAY_LAST": 0.0}

render_records = []
camera_names = ("CAM_ARRAY_PERSPECTIVE", "CAM_ARRAY_TOP", "CAM_ARRAY_FIRST", "CAM_ARRAY_LAST")
for camera_name in camera_names:
    camera = bpy.data.objects.get(camera_name)
    if camera is None:
        failures.append(f"missing camera: {camera_name}")
        continue
    destination = RENDERS / f"{camera_name}.png"
    scene.camera = camera
    scene.view_settings.exposure = exposures[camera_name]
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    render_records.append({
        "camera": camera_name,
        "relative_private_path": destination.relative_to(ROOT).as_posix(),
        "bytes": destination.stat().st_size,
        "sha256": digest(destination),
    })

report = {
    "schema": "opticalmodeler.n04-array-second-reopen.v1",
    "status": "PASS" if not failures else "BLOCKED",
    "scope": scene.get("array_scope"),
    "run_id": CONFIG["run_id"],
    "blender_version": bpy.app.version_string,
    "opened_blend": actual_opened.relative_to(ROOT).as_posix(),
    "opened_blend_sha256": digest(actual_opened),
    "expected_opened_blend": expected_opened.relative_to(ROOT).as_posix(),
    "scene_status_readback": readback,
    "checks": checks,
    "station_count": COUNT,
    "science_object_count": len(science),
    "node_count": len(nodes),
    "directed_edge_count": len(edges),
    "official_instance_count": official,
    "modeled_load_link_count": load_links,
    "render_records": render_records,
    "status_boundaries": {
        "render_quality_only": True,
        "model_scope": "PARTIAL_SCOPED",
        "literal_paper_multi_station_system": "BLOCKED_NOT_CLAIMED",
        "final_or_release": False,
    },
    "failures": failures,
}
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "station_count": COUNT, "node_count": len(nodes), "render_count": len(render_records), "failures": failures}, indent=2))
if failures:
    raise RuntimeError(f"array second reopen failed: {len(failures)}")
