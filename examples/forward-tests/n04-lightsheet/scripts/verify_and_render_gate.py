"""Second reopen of the audited gate Blend plus role-specific audit renders."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
BASE = ROOT / "work" / "full_32_node_propagation_v3"
MEASUREMENTS = BASE / "measurements"
EVIDENCE = BASE / "evidence"
SCENE_DIR = BASE / "scene"
RENDERS = BASE / "renders"
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
AUDITED_BLEND = SCENE_DIR / "FULL_32_NODE_PROPAGATION_GATE_v3.blend"
REPORT_PATH = EVIDENCE / "GATE_BLEND_SECOND_REOPEN.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mesh_invalid_face_count(mesh):
    invalid = 0
    for polygon in mesh.polygons:
        if len(polygon.vertices) != 3:
            invalid += 1
            continue
        a, b, c = (mesh.vertices[index].co for index in polygon.vertices)
        edges = (b - a, c - b, a - c)
        edge_squared = [edge.length_squared for edge in edges]
        if min(edge_squared) == 0.0:
            invalid += 1
            continue
        double_area = (b - a).cross(c - a).length
        if double_area <= 1e-12 or double_area / max(edge_squared) <= 1e-12:
            invalid += 1
    return invalid


def object_world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[axis] for point in points) for axis in range(3)]
    maximum = [max(point[axis] for point in points) for axis in range(3)]
    return {"min_m": minimum, "max_m": maximum}


def segment_intersects_aabb(start, end, bbox):
    direction = end - start
    low, high = 0.0, 1.0
    for axis in range(3):
        if abs(direction[axis]) < 1e-15:
            if start[axis] < bbox["min_m"][axis] or start[axis] > bbox["max_m"][axis]:
                return False
            continue
        first = (bbox["min_m"][axis] - start[axis]) / direction[axis]
        second = (bbox["max_m"][axis] - start[axis]) / direction[axis]
        if first > second:
            first, second = second, first
        low, high = max(low, first), min(high, second)
        if low > high:
            return False
    return True


def world_bvh(obj):
    vertices = [tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    polygons = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=True, epsilon=1e-7)


def bvh_first_hit(obj, start, end):
    vector = end - start
    location, normal, polygon, distance = world_bvh(obj).ray_cast(start, vector.normalized(), vector.length)
    if location is None:
        return None
    return {
        "object_name": obj.name, "node_id": obj.get("node_id"),
        "part_number": obj.get("part_number"), "provenance": obj.get("provenance"),
        "distance_m": float(distance), "world_location_m": list(location),
        "world_normal": list(normal), "polygon_index": int(polygon),
    }


def ensure_camera(name, location, target, lens):
    camera = bpy.data.objects.get(name)
    if camera:
        return camera
    data = bpy.data.cameras.new(f"DATA__{name}")
    data.lens = lens
    data.sensor_width = 36.0
    camera = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = location
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera["provenance"] = "DETERMINISTIC_SECOND_REOPEN_AUDIT_CAMERA"
    return camera


def main():
    RENDERS.mkdir(parents=True, exist_ok=True)
    build = load_json(BASE / "BUILD_PARAMS.json")
    topology = load_json(PHASE1 / "TOPOLOGY_MAP.json")
    generator = load_json(EVIDENCE / "GENERATOR_REPORT.json")
    regression_path = EVIDENCE / "REOPEN_FULL_REGRESSION.json"
    regression = load_json(regression_path)
    failures = []
    current = Path(bpy.data.filepath).resolve()
    if current != AUDITED_BLEND.resolve():
        failures.append(f"unexpected opened blend {current}")
    if regression["status"] != "PASS":
        failures.append("first reopen regression not PASS")

    expected_properties = {
        "scope": "FULL_32_NODE_PROPAGATION_GATE_V3",
        "propagation_gate_status": "PASS",
        "propagation_gate_reason": "SAVED_BLEND_REOPEN_REGRESSION_PASSED",
        "full_32_node_propagation_gate": "PASS",
        "phase1_immutable": True,
        "n04_r3_immutable": True,
        "node_count": 32,
        "directed_edge_traversal_count": 44,
        "family_count": 16,
        "model_scope_status": "PARTIAL_SCOPED",
        "literal_paper_performance": "BLOCKED",
        "final_or_release_status": "BLOCKED",
        "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        "substitution_count": 17,
        "S4FC488_source_diagnostics": "PARTIAL_SCOPED",
        "S4FC637_source_diagnostics": "PARTIAL_SCOPED",
        "vendor_cad_public_redistribution": "BLOCKED",
    }
    readback = {key: bpy.context.scene.get(key) for key in expected_properties}
    for key, value in expected_properties.items():
        if readback[key] != value:
            failures.append(f"scene property {key} drift")
    if bpy.context.scene.get("reopen_regression_sha256") != sha256(regression_path):
        failures.append("serialized reopen regression hash mismatch")

    official = [obj for obj in bpy.data.objects if obj.get("official_thorlabs_component_identity")]
    if len(official) != generator["official_instance_count"]:
        failures.append(f"official instance count {len(official)} != {generator['official_instance_count']}")
    official_meshes = {obj.data.name: obj.data for obj in official}
    used_mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]
    used_meshes = {obj.data.name: obj.data for obj in used_mesh_objects}
    invalid_by_mesh = {name: mesh_invalid_face_count(mesh) for name, mesh in sorted(used_meshes.items())}
    if any(invalid_by_mesh.values()):
        failures.append("second reopen all-used-mesh invalid faces")
    if len(used_meshes) != regression["counts"]["unique_serialized_meshes"]:
        failures.append("second reopen used mesh datablock count drift")

    centers = {item["node_id"]: Vector(item["world_port_center_m"]) for item in build["nodes"]}
    node_readback = []
    for node_id in sorted(centers):
        marker = bpy.data.objects.get(f"PORT_MARKER__{node_id}")
        label = bpy.data.objects.get(f"LABEL__{node_id}")
        marker_error = (marker.matrix_world.translation - centers[node_id]).length * 1000.0 if marker else float("inf")
        official_count = sum(obj.get("node_id") == node_id for obj in official)
        chamber_count = sum(obj.name == "MODELED_NON_THORLABS__N15__EXPERIMENTAL_CHAMBER" for obj in bpy.data.objects) if node_id == "N15" else 0
        status = "PASS" if marker_error <= 0.05 and label and (official_count > 0 or chamber_count == 1) else "BLOCKED"
        if status != "PASS":
            failures.append(f"second reopen node identity {node_id}")
        node_readback.append({
            "node_id": node_id, "marker_error_mm": marker_error,
            "official_object_count": official_count, "modeled_chamber_count": chamber_count,
            "label_present": bool(label), "status": status,
        })

    beams = [obj for obj in bpy.data.objects if obj.name.startswith("PRESENTATION_BEAM__")]
    beam_edge_ids = sorted(obj.get("edge_id") for obj in beams)
    expected_edge_ids = sorted(edge["id"] for edge in topology["edges"])
    if beam_edge_ids != expected_edge_ids:
        failures.append("presentation beam edge-id coverage drift")
    load_links = [obj for obj in bpy.data.objects if obj.name.startswith("MODELED_LOAD_LINK__") or obj.name.startswith("MODELED_FRAME_TABLE_LOAD_LINK__")]
    if len(load_links) != regression["counts"]["modeled_load_links"]:
        failures.append("modeled load-link count drift")
    if any(obj.get("official_thorlabs_claim") is not False for obj in load_links):
        failures.append("modeled load link acquired official claim")
    chamber = bpy.data.objects.get("MODELED_NON_THORLABS__N15__EXPERIMENTAL_CHAMBER")
    if not chamber or chamber.get("catalog_component_claim") is not False:
        failures.append("experimental chamber provenance drift")

    # Independent second-session reproduction of the repaired E042/N31 first
    # hit. The ray includes every visible official and modeled physical object.
    n30, n31 = centers["N30"], centers["N31"]
    e042_direction = (n31 - n30).normalized()
    e042_start = n30 + e042_direction * 0.004
    e042_end = n31 + e042_direction * 0.080
    physical = [
        obj for obj in used_mesh_objects
        if (obj.get("official_thorlabs_component_identity") and not obj.hide_render)
        or obj.get("optical_clearance_class") == "PHYSICAL_OPAQUE"
    ]
    e042_hits = []
    for obj in physical:
        if obj.get("node_id") in {"GLOBAL", "N30"}:
            continue
        if not segment_intersects_aabb(e042_start, e042_end, object_world_bbox(obj)):
            continue
        hit = bvh_first_hit(obj, e042_start, e042_end)
        if hit:
            e042_hits.append(hit)
    e042_hits.sort(key=lambda item: item["distance_m"])
    n31_primary = next(obj for obj in official if obj.get("node_id") == "N31" and obj.get("part_number") == "BB1-E02")
    first_hit = e042_hits[0] if e042_hits else None
    n31_node_audit = next(item for item in regression["node_audits"] if item["node_id"] == "N31")
    n31_axis = Vector(n31_node_audit["world_axis"])
    n31_port = Vector(n31_node_audit["native_port_world_center_m"])
    if first_hit:
        delta = Vector(first_hit["world_location_m"]) - n31_port
        e042_surface_offset_mm = (delta - n31_axis * delta.dot(n31_axis)).length * 1000.0
    else:
        e042_surface_offset_mm = math.inf
    e042_readback = {
        "start_m": list(e042_start), "end_m": list(e042_end),
        "physical_object_scope_count": len(physical),
        "sorted_first_hit_per_object": e042_hits,
        "first_hit_object": first_hit["object_name"] if first_hit else None,
        "expected_target_object": n31_primary.name,
        "actual_surface_aperture_offset_mm": e042_surface_offset_mm,
        "clear_aperture_radius_mm": 11.0,
        "status": "PASS" if (
            first_hit and first_hit["object_name"] == n31_primary.name
            and e042_surface_offset_mm <= 11.0
        ) else "BLOCKED",
    }
    if e042_readback["status"] != "PASS":
        failures.append("second reopen E042/N31 first-hit or surface aperture")

    # Independently recompute the two stage endpoint contacts; the paired
    # controller must remain excluded from the mechanical load path.
    n24_stage = next(obj for obj in official if obj.get("node_id") == "N24" and obj.get("assembly_subrole") == "GUIDED_PIEZO_STAGE")
    n24_controller = next(obj for obj in official if obj.get("node_id") == "N24" and obj.get("assembly_subrole") == "PAIRED_CONTROLLER")
    stage_links = [
        obj for obj in load_links
        if obj.get("from_object") == n24_stage.name or obj.get("to_object") == n24_stage.name
    ]
    stage_bvh = world_bvh(n24_stage)
    stage_contacts = []
    for link in stage_links:
        pairs = len(world_bvh(link).overlap(stage_bvh))
        stage_contacts.append({"link_object": link.name, "bvh_contact_pairs": pairs, "status": "PASS" if pairs > 0 else "BLOCKED"})
    controller_in_path = any(
        obj.get("from_object") == n24_controller.name or obj.get("to_object") == n24_controller.name
        for obj in load_links
    )
    n24_stage_readback = {
        "stage_object": n24_stage.name, "controller_object": n24_controller.name,
        "stage_endpoint_contacts": stage_contacts,
        "controller_in_load_path": controller_in_path,
        "status": "PASS" if len(stage_contacts) >= 2 and all(item["status"] == "PASS" for item in stage_contacts) and not controller_in_path else "BLOCKED",
    }
    if n24_stage_readback["status"] != "PASS":
        failures.append("second reopen N24 stage load path")

    # ponytail: each camera keeps one fixed exposure; a single global exposure
    # washed out the orthographic top view and weakened its audit value.
    ensure_camera("CAM_N24_STAGE_GATE", (-0.84, -0.83, 0.43), centers["N24"] + Vector((0.0, 0.0, -0.015)), 72.0)
    ensure_camera("CAM_E042_N31_GATE", (1.12, -0.88, 0.42), centers["N31"], 72.0)
    render_plan = [
        ("CAM_FULL_PERSPECTIVE", "FULL_32_overall_perspective.png", 0.35),
        ("CAM_FULL_TOP", "FULL_32_overall_top.png", -1.00),
        ("CAM_FAMILY_SOURCE", "FAMILY_source_launch.png", 0.25),
        ("CAM_FAMILY_SCANNERS", "FAMILY_scanners_relay.png", 0.25),
        ("CAM_FAMILY_BRANCH_RELAY", "FAMILY_branch_remote_relay.png", 0.25),
        ("CAM_FAMILY_DETECTOR", "FAMILY_spectral_detector.png", 0.25),
        ("CAM_N04_REAUDIT", "FAMILY_N04_reaudit.png", 0.25),
        ("CAM_N24_STAGE_GATE", "CRITICAL_N24_stage_load_path.png", 0.15),
        ("CAM_E042_N31_GATE", "CRITICAL_E042_N31_first_hit.png", 0.15),
    ]
    scene = bpy.context.scene
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    render_records = []
    if failures:
        raise RuntimeError(f"second reopen pre-render gate failed: {failures}")
    for camera_name, filename, exposure in render_plan:
        camera = bpy.data.objects.get(camera_name)
        if not camera:
            raise RuntimeError(f"missing camera {camera_name}")
        scene.camera = camera
        scene.view_settings.exposure = exposure
        destination = RENDERS / filename
        scene.render.filepath = str(destination)
        bpy.ops.render.render(write_still=True)
        if not destination.is_file() or destination.stat().st_size < 10000:
            raise RuntimeError(f"render missing/too small {filename}")
        render_records.append({
            "camera": camera_name, "relative_private_path": str(destination.relative_to(ROOT)).replace("\\", "/"),
            "exposure": exposure, "bytes": destination.stat().st_size, "sha256": sha256(destination),
        })
        print(f"RENDER {camera_name} -> {filename} {destination.stat().st_size} bytes", flush=True)

    report = {
        "schema": "opticalmodeler.full32.gate-second-reopen.v3",
        "status": "PASS",
        "scope": "FULL_32_NODE_PROPAGATION_GATE_V3_NOT_FINAL_OR_RELEASE",
        "blender_version": bpy.app.version_string,
        "audited_blend": {"relative_private_path": str(current.relative_to(ROOT)).replace("\\", "/"), "bytes": current.stat().st_size, "sha256": sha256(current)},
        "scene_status_readback": readback,
        "regression_report_sha256": sha256(regression_path),
        "official_instance_count": len(official),
        "official_unique_mesh_count": len(official_meshes),
        "all_used_mesh_object_count": len(used_mesh_objects),
        "all_used_unique_mesh_count": len(used_meshes),
        "all_used_mesh_invalid_faces_total": sum(invalid_by_mesh.values()),
        "all_used_mesh_invalid_faces_by_mesh": invalid_by_mesh,
        "node_readback": node_readback,
        "presentation_beam_count": len(beams),
        "modeled_load_link_count": len(load_links),
        "E042_N31_factory_reopen_readback": e042_readback,
        "N24_stage_factory_reopen_readback": n24_stage_readback,
        "render_records": render_records,
        "status_boundaries": {
            "model_scope": "PARTIAL_SCOPED", "literal_paper_performance": "BLOCKED",
            "S4FC488_source_diagnostics": "PARTIAL_SCOPED", "S4FC637_source_diagnostics": "PARTIAL_SCOPED",
            "final_or_release": "BLOCKED",
            "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        },
        "failures": [],
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS", "blend_sha256": report["audited_blend"]["sha256"],
        "official_instances": len(official), "nodes": len(node_readback), "renders": len(render_records),
        "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
