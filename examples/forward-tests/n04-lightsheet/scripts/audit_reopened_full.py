"""Reopen and fail-closed audit the full 32-node saved Blend.

This script is intentionally independent of generator-time PASS labels.  It
reads the serialized meshes and transforms, performs per-object world-bbox and
mesh checks, per-node native-port/aperture/mechanical-ray checks, per-edge
zero-radius collision checks, and narrow-phase BVH load-contact checks.  Only a
fully passing run writes the audited gate Blend; no final/release claim is made.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import OrderedDict
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
BASE = ROOT / "work" / "full_32_node_propagation_v3"
MEASUREMENTS = BASE / "measurements"
EVIDENCE = BASE / "evidence"
SCENE_DIR = BASE / "scene"
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
GENERATED_BLEND = SCENE_DIR / "FULL_32_NODE_PROPAGATION_v3.blend"
AUDITED_BLEND = SCENE_DIR / "FULL_32_NODE_PROPAGATION_GATE_v3.blend"
REPORT_PATH = EVIDENCE / "REOPEN_FULL_REGRESSION.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def mesh_face_quality(mesh):
    duplicate = 0
    collinear = 0
    non_triangular = 0
    for polygon in mesh.polygons:
        if len(polygon.vertices) != 3:
            non_triangular += 1
            continue
        a, b, c = (mesh.vertices[index].co for index in polygon.vertices)
        edges = (b - a, c - b, a - c)
        edge_squared = [edge.length_squared for edge in edges]
        if min(edge_squared) == 0.0:
            duplicate += 1
            continue
        double_area = (b - a).cross(c - a).length
        if double_area <= 1e-12 or double_area / max(edge_squared) <= 1e-12:
            collinear += 1
    return {
        "triangle_count": len(mesh.polygons) - non_triangular,
        "non_triangular_faces": non_triangular,
        "duplicate_vertex_faces": duplicate,
        "distinct_collinear_faces": collinear,
        "invalid_face_count": duplicate + collinear + non_triangular,
    }


def object_world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def max_bbox_error_mm(first, second):
    return max(abs(first[key][axis] - second[key][axis]) * 1000.0 for key in ("min_m", "max_m", "size_m") for axis in range(3))


def unit(vector):
    value = Vector(vector)
    return value.normalized() if value.length else Vector((1.0, 0.0, 0.0))


def angle_degrees(first, second):
    dot = max(-1.0, min(1.0, unit(first).dot(unit(second))))
    return math.degrees(math.acos(dot))


def segment_intersects_aabb(start, end, bbox, padding=0.0):
    direction = end - start
    low, high = 0.0, 1.0
    for axis in range(3):
        minimum = bbox["min_m"][axis] - padding
        maximum = bbox["max_m"][axis] + padding
        if abs(direction[axis]) < 1e-15:
            if start[axis] < minimum or start[axis] > maximum:
                return False
            continue
        first = (minimum - start[axis]) / direction[axis]
        second = (maximum - start[axis]) / direction[axis]
        if first > second:
            first, second = second, first
        low = max(low, first)
        high = min(high, second)
        if low > high:
            return False
    return True


def ray_cast_world(obj, start, end):
    inverse = obj.matrix_world.inverted_safe()
    local_start = inverse @ start
    local_end = inverse @ end
    local_vector = local_end - local_start
    if local_vector.length <= 1e-12:
        return None
    hit, location, normal, polygon_index = obj.ray_cast(local_start, local_vector.normalized(), distance=local_vector.length)
    if not hit:
        return None
    world_location = obj.matrix_world @ location
    segment_length = (end - start).length
    distance = (world_location - start).length
    if distance > segment_length + 1e-8:
        return None
    return {"distance_m": distance, "world_location_m": list(world_location), "polygon_index": int(polygon_index)}


def ray_cast_bvh_world(obj, start, end, cache):
    """Two-sided world-space ray cast used for physical first-hit truth."""
    vector = end - start
    if vector.length <= 1e-12:
        return None
    location, normal, polygon_index, distance = cache.get(obj).ray_cast(
        start, vector.normalized(), vector.length,
    )
    if location is None:
        return None
    return {
        "distance_m": float(distance),
        "world_location_m": list(location),
        "world_normal": list(normal),
        "polygon_index": int(polygon_index),
        "ray_method": "WORLD_BVH_TWO_SIDED_FIRST_SURFACE",
    }


def world_bvh(obj, epsilon=1e-7):
    vertices = [tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    polygons = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return BVHTree.FromPolygons(
        vertices, polygons,
        all_triangles=all(len(polygon) == 3 for polygon in polygons),
        epsilon=epsilon,
    )


class BVHCache:
    def __init__(self, maximum=10):
        self.maximum = maximum
        self.values = OrderedDict()

    def get(self, obj):
        key = obj.name
        if key in self.values:
            value = self.values.pop(key)
            self.values[key] = value
            return value
        value = world_bvh(obj)
        self.values[key] = value
        while len(self.values) > self.maximum:
            self.values.popitem(last=False)
        return value


def overlap_count(first, second, cache):
    if not segment_intersects_aabb(Vector(first["min_m"]), Vector(first["max_m"]), second, 0.0):
        # The segment helper is not an AABB overlap test for diagonals in every
        # case; use the exact scalar test below before declaring separation.
        pass
    a = cache.get(bpy.data.objects[first["name"]])
    b = cache.get(bpy.data.objects[second["name"]])
    return len(a.overlap(b))


def aabb_overlap(first, second):
    return all(first["min_m"][axis] <= second["max_m"][axis] and second["min_m"][axis] <= first["max_m"][axis] for axis in range(3))


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    build = load_json(BASE / "BUILD_PARAMS.json")
    topology = load_json(PHASE1 / "TOPOLOGY_MAP.json")
    ports = load_json(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK_FULL.json")
    family_lock = load_json(MEASUREMENTS / "FAMILY_LOCK.json")
    generator = load_json(EVIDENCE / "GENERATOR_REPORT.json")
    cad_audit = load_json(MEASUREMENTS / "FULL_CAD_MESH_AUDIT.json")
    failures = []

    current_path = Path(bpy.data.filepath).resolve()
    if current_path != GENERATED_BLEND.resolve():
        failures.append(f"opened unexpected Blend: {current_path}")
    if generator["status"] != "PASS" or cad_audit["status"] != "PASS" or ports["status"] != "PASS":
        failures.append("upstream generator/CAD/port lock is not PASS")

    expected_scene = {
        "scope": "FULL_32_NODE_PROPAGATION_GATE_V3", "phase1_immutable": True,
        "n04_r3_immutable": True, "node_count": 32, "directed_edge_traversal_count": 44,
        "family_count": 16, "model_scope_status": "PARTIAL_SCOPED",
        "literal_paper_performance": "BLOCKED", "final_or_release_status": "BLOCKED",
        "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        "propagation_gate_status": "UNVERIFIED", "propagation_gate_reason": "PENDING_SAVED_BLEND_REOPEN",
        "substitution_count": 17, "S4FC488_source_diagnostics": "PARTIAL_SCOPED",
        "S4FC637_source_diagnostics": "PARTIAL_SCOPED", "vendor_cad_public_redistribution": "BLOCKED",
    }
    scene_readback = {key: bpy.context.scene.get(key) for key in expected_scene}
    for key, expected in expected_scene.items():
        if scene_readback[key] != expected:
            failures.append(f"scene status drift {key}: {scene_readback[key]!r} != {expected!r}")

    official_objects = [obj for obj in bpy.data.objects if obj.get("official_thorlabs_component_identity")]
    used_mesh_objects = [obj for obj in bpy.data.objects if obj.type == "MESH"]

    # Fail closed over every in-use serialized mesh, including all modeled load
    # links, frame links, chamber geometry, markers, and presentation beams.
    mesh_quality = {}
    used_mesh_names = {obj.data.name for obj in used_mesh_objects}
    for mesh in (bpy.data.meshes[name] for name in sorted(used_mesh_names)):
        quality = mesh_face_quality(mesh)
        mesh_quality[mesh.name] = quality
        if quality["invalid_face_count"]:
            failures.append(f"reopen used mesh invalid faces {mesh.name}: {quality['invalid_face_count']}")

    expected_instances = {item["object_name"]: item for item in generator["official_instances"]}
    if len(official_objects) != len(expected_instances):
        failures.append(f"official instance count {len(official_objects)} != {len(expected_instances)}")
    object_bbox = {}
    instance_audits = []
    for obj in sorted(official_objects, key=lambda item: item.name):
        expected = expected_instances.get(obj.name)
        if not expected:
            failures.append(f"unlocked official object after reopen: {obj.name}")
            continue
        actual_bbox = object_world_bbox(obj)
        object_bbox[obj.name] = actual_bbox
        error = max_bbox_error_mm(actual_bbox, expected["expected_world_bbox"])
        quality = mesh_quality[obj.data.name]
        property_checks = {
            "part_number": obj.get("part_number") == expected["part_number"],
            "node_id": obj.get("node_id") == expected["node_id"],
            "assembly_subrole": obj.get("assembly_subrole") == expected["assembly_subrole"],
            "source_step_sha256": obj.get("source_step_sha256") == expected["source_step_sha256"],
            "official_identity": obj.get("official_thorlabs_component_identity") is True,
            "redistribution_excluded": obj.get("redistribution_decision") == "EXCLUDE_FROM_PUBLIC_CANDIDATE",
        }
        status = "PASS" if error <= build["audit_thresholds"]["blender_bbox_error_mm"] and not quality["invalid_face_count"] and all(property_checks.values()) else "BLOCKED"
        if status != "PASS":
            failures.append(f"official object reopen gate {obj.name}")
        instance_audits.append({
            "object_name": obj.name, "node_id": expected["node_id"], "part_number": expected["part_number"],
            "mesh_name": obj.data.name, "mesh_face_quality": quality,
            "actual_world_bbox": actual_bbox, "expected_world_bbox": expected["expected_world_bbox"],
            "world_bbox_error_mm": error, "property_checks": property_checks, "status": status,
        })

    modeled_physical_objects = [
        obj for obj in used_mesh_objects
        if obj.get("optical_clearance_class") == "PHYSICAL_OPAQUE"
    ]
    physical_objects = [obj for obj in official_objects if not obj.hide_render] + modeled_physical_objects
    for obj in physical_objects:
        object_bbox.setdefault(obj.name, object_world_bbox(obj))

    nodes = {item["node_id"]: item for item in build["nodes"]}
    centers = {node_id: Vector(item["world_port_center_m"]) for node_id, item in nodes.items()}
    ports_by_node = {item["node_id"]: item for item in ports["nodes"]}
    edge_in = {node_id: [] for node_id in nodes}
    edge_out = {node_id: [] for node_id in nodes}
    for edge in topology["edges"]:
        edge_out[edge["from_node"]].append(edge)
        edge_in[edge["to_node"]].append(edge)

    def through_direction(node_id):
        forward_out = [edge for edge in edge_out[node_id] if edge.get("direction") != "return"] or edge_out[node_id]
        forward_in = [edge for edge in edge_in[node_id] if edge.get("direction") != "return"] or edge_in[node_id]
        if forward_out:
            return unit(centers[forward_out[0]["to_node"]] - centers[node_id])
        if forward_in:
            return unit(centers[node_id] - centers[forward_in[0]["from_node"]])
        return Vector((1.0, 0.0, 0.0))

    mirror_nodes = {"N03", "N09", "N11", "N20", "N21", "N24", "N26", "N28", "N29", "N31"}

    def surface_normal(node_id):
        incoming = [edge for edge in edge_in[node_id] if edge.get("direction") != "return"] or edge_in[node_id]
        outgoing = [edge for edge in edge_out[node_id] if edge.get("direction") != "return"] or edge_out[node_id]
        if incoming and outgoing:
            d_in = unit(centers[node_id] - centers[incoming[0]["from_node"]])
            d_out = unit(centers[outgoing[0]["to_node"]] - centers[node_id])
            candidate = d_in - d_out
            if candidate.length > 1e-6:
                return candidate.normalized()
        direction = through_direction(node_id)
        return Vector((-direction.y, direction.x, 0.0)).normalized()

    def expected_axis(node_id, part):
        return surface_normal(node_id) if node_id in mirror_nodes or part in {"DMLP505R", "DMLP605R", "BB1-E02", "PF03-03-P01"} else through_direction(node_id)

    primary_object = {}
    for node_id, node in nodes.items():
        if node_id == "N15":
            primary_object[node_id] = bpy.data.objects.get("MODELED_NON_THORLABS__N15__EXPERIMENTAL_CHAMBER")
            continue
        matches = [obj for obj in official_objects if obj.get("node_id") == node_id and obj.get("part_number") == node["primary_part_number"]]
        if not matches:
            failures.append(f"{node_id}: missing primary object")
            primary_object[node_id] = None
        else:
            primary_object[node_id] = sorted(matches, key=lambda item: item.name)[0]

    # Per-node semantic ports and full target traversal. Optical first-hit truth
    # uses two-sided world BVHs, not Blender's one-sided object ray cast.
    optical_cache = BVHCache(maximum=12)
    open_aperture_primary_parts = {"P50K"}
    measured_centers = {}
    measured_axes = {}
    node_audits = []
    for node_id in sorted(nodes):
        node = nodes[node_id]
        port = ports_by_node[node_id]
        marker = bpy.data.objects.get(f"PORT_MARKER__{node_id}")
        marker_error = (marker.matrix_world.translation - centers[node_id]).length * 1000.0 if marker else float("inf")
        obj = primary_object[node_id]
        if node_id == "N15":
            measured_center = obj.matrix_world.translation if obj else Vector((math.inf, math.inf, math.inf))
            measured_axis = through_direction(node_id)
        elif obj:
            measured_center = obj.matrix_world @ Vector(port["native_origin_mm"])
            measured_axis = (obj.matrix_world.to_3x3() @ Vector(port["native_axis"])).normalized()
        else:
            measured_center = Vector((math.inf, math.inf, math.inf))
            measured_axis = Vector((0.0, 0.0, 0.0))
        center_error = (measured_center - centers[node_id]).length * 1000.0
        axis_target = expected_axis(node_id, node["primary_part_number"])
        axis_error = min(angle_degrees(measured_axis, axis_target), angle_degrees(-measured_axis, axis_target)) if measured_axis.length else float("inf")
        measured_centers[node_id] = measured_center
        measured_axes[node_id] = measured_axis

        aperture_traversals = []
        mechanical_hits = []
        target_assembly = [item for item in physical_objects if item.get("node_id") == node_id]
        for edge in edge_in[node_id]:
            direction = unit(centers[node_id] - centers[edge["from_node"]])
            start = centers[edge["from_node"]] + direction * 0.004
            end = centers[node_id] + direction * 0.080
            hits = []
            for item in target_assembly:
                bbox = object_bbox[item.name]
                if not segment_intersects_aabb(start, end, bbox, 0.0):
                    continue
                hit = ray_cast_bvh_world(item, start, end, optical_cache)
                if hit:
                    hits.append({
                        "object_name": item.name, "node_id": item.get("node_id"),
                        "part_number": item.get("part_number"), "provenance": item.get("provenance"),
                        **hit,
                    })
            hits.sort(key=lambda item: item["distance_m"])
            primary_hit_index = next((index for index, item in enumerate(hits) if item["object_name"] == obj.name), None) if obj else None
            primary_surface_expected = node["primary_part_number"] not in open_aperture_primary_parts
            closest = start + direction * (measured_center - start).dot(direction)
            semantic_port_line_offset_mm = (closest - measured_center).length * 1000.0
            surface_hit_radial_offset_mm = None
            if primary_surface_expected and primary_hit_index is not None:
                primary_hit = hits[primary_hit_index]
                hit_point = Vector(primary_hit["world_location_m"])
                delta = hit_point - measured_center
                surface_hit_radial_offset_mm = (delta - measured_axis * delta.dot(measured_axis)).length * 1000.0
                preceding_hits = hits[:primary_hit_index]
                first_hit_is_primary = primary_hit_index == 0
            elif not primary_surface_expected:
                primary_hit = None
                preceding_hits = hits
                first_hit_is_primary = not hits
            else:
                primary_hit = None
                preceding_hits = hits
                first_hit_is_primary = False
            radial_offset_mm = (
                surface_hit_radial_offset_mm
                if edge["id"] == "E042" and surface_hit_radial_offset_mm is not None
                else semantic_port_line_offset_mm
            )
            aperture_measurement_mode = (
                "ACTUAL_TARGET_SURFACE_HIT_OFFSET_FOR_E042_N31"
                if edge["id"] == "E042"
                else "MEASURED_ZERO_RADIUS_LINE_TO_CAD_NATIVE_SEMANTIC_PORT"
            )
            aperture_pass = (
                first_hit_is_primary
                and radial_offset_mm <= port["clear_aperture_radius_mm"]
            )
            mechanical_hits.extend({"edge_id": edge["id"], **item} for item in preceding_hits)
            aperture_traversals.append({
                "edge_id": edge["id"], "branch_id": edge["branch_id"], "direction": edge["direction"],
                "traversal_side": "TARGET_INCOMING",
                "zero_radius_start_m": list(start), "zero_radius_end_m": list(end),
                "primary_surface_expected": primary_surface_expected,
                "first_hit_is_primary_or_open_aperture": first_hit_is_primary,
                "measured_primary_hit": primary_hit,
                "semantic_port_line_offset_mm": semantic_port_line_offset_mm,
                "surface_hit_radial_offset_mm": surface_hit_radial_offset_mm,
                "zero_radius_radial_offset_mm": radial_offset_mm,
                "clear_aperture_radius_mm": port["clear_aperture_radius_mm"],
                "preceding_physical_hits": preceding_hits,
                "all_target_assembly_hits": hits,
                "ray_method": "WORLD_BVH_TWO_SIDED_FULL_TARGET_TRAVERSAL",
                "aperture_measurement_mode": aperture_measurement_mode,
                "status": "PASS" if aperture_pass else "BLOCKED",
            })
        if not edge_in[node_id]:
            # Source-only nodes originate at their measured CAD-native port.
            delta = measured_center - centers[node_id]
            radial_offset_mm = (delta - measured_axis * delta.dot(measured_axis)).length * 1000.0
            aperture_traversals.append({
                "edge_id": None, "branch_id": None, "direction": "source",
                "traversal_side": "CAD_NATIVE_SOURCE_PORT_ORIGIN",
                "zero_radius_radial_offset_mm": radial_offset_mm,
                "clear_aperture_radius_mm": port["clear_aperture_radius_mm"],
                "first_hit_is_primary_or_open_aperture": True,
                "ray_method": "MEASURED_CAD_NATIVE_PORT_ORIGIN",
                "status": "PASS" if radial_offset_mm <= port["clear_aperture_radius_mm"] else "BLOCKED",
            })
        node_status = (
            "PASS" if marker_error <= 0.05 and center_error <= build["audit_thresholds"]["port_center_error_mm"]
            and axis_error <= build["audit_thresholds"]["axis_angular_error_deg"]
            and all(item["status"] == "PASS" for item in aperture_traversals) and not mechanical_hits else "BLOCKED"
        )
        if node_status != "PASS":
            failures.append(f"{node_id}: port/aperture/mechanical-ray gate")
        node_audits.append({
            "node_id": node_id, "family_id": node["family_id"], "primary_part_number": node["primary_part_number"],
            "frozen_status": node["frozen_status"], "marker_error_mm": marker_error,
            "native_port_world_center_m": list(measured_center), "expected_world_center_m": list(centers[node_id]),
            "port_center_error_mm": center_error, "world_axis": list(measured_axis), "expected_axis": list(axis_target),
            "axis_angular_error_deg": axis_error, "aperture_traversals": aperture_traversals,
            "mechanical_zero_radius_hits": mechanical_hits, "status": node_status,
        })

    # Every edge is extended through the target plane. All official and modeled
    # physical objects are in scope; the first physical interaction must be the
    # declared target primary (or no hit for a declared open pinhole aperture).
    edge_audits = []
    global_exclusions = {"GLOBAL"}
    for edge in topology["edges"]:
        start_center, end_center = centers[edge["from_node"]], centers[edge["to_node"]]
        direction = unit(end_center - start_center)
        start = start_center + direction * 0.004
        end = end_center + direction * 0.080
        hits = []
        for item in physical_objects:
            node_id = item.get("node_id")
            if node_id in global_exclusions or node_id == edge["from_node"]:
                continue
            bbox = object_bbox[item.name]
            if not segment_intersects_aabb(start, end, bbox, 0.0):
                continue
            hit = ray_cast_bvh_world(item, start, end, optical_cache)
            if hit:
                hits.append({
                    "object_name": item.name, "node_id": node_id,
                    "part_number": item.get("part_number"), "provenance": item.get("provenance"),
                    **hit,
                })
        hits.sort(key=lambda item: item["distance_m"])
        target = primary_object[edge["to_node"]]
        target_part = nodes[edge["to_node"]]["primary_part_number"]
        primary_surface_expected = target_part not in open_aperture_primary_parts
        primary_hit_index = next((index for index, item in enumerate(hits) if target and item["object_name"] == target.name), None)
        if primary_surface_expected and primary_hit_index is not None:
            target_hit = hits[primary_hit_index]
            collisions = hits[:primary_hit_index]
            first_hit_is_target = primary_hit_index == 0
            hit_point = Vector(target_hit["world_location_m"])
            axis = measured_axes[edge["to_node"]]
            delta = hit_point - measured_centers[edge["to_node"]]
            surface_hit_radial_offset_mm = (delta - axis * delta.dot(axis)).length * 1000.0
        elif not primary_surface_expected:
            target_hit = None
            collisions = hits
            first_hit_is_target = not hits
            axis = measured_axes[edge["to_node"]]
            surface_hit_radial_offset_mm = None
        else:
            target_hit = None
            collisions = hits
            first_hit_is_target = False
            surface_hit_radial_offset_mm = None
        closest = start + direction * (measured_centers[edge["to_node"]] - start).dot(direction)
        semantic_port_line_offset_mm = (closest - measured_centers[edge["to_node"]]).length * 1000.0
        radial_offset_mm = (
            surface_hit_radial_offset_mm
            if edge["id"] == "E042" and surface_hit_radial_offset_mm is not None
            else semantic_port_line_offset_mm
        )
        aperture_measurement_mode = (
            "ACTUAL_TARGET_SURFACE_HIT_OFFSET_FOR_E042_N31"
            if edge["id"] == "E042"
            else "MEASURED_ZERO_RADIUS_LINE_TO_CAD_NATIVE_SEMANTIC_PORT"
        )
        aperture_radius_mm = ports_by_node[edge["to_node"]]["clear_aperture_radius_mm"]
        aperture_pass = radial_offset_mm <= aperture_radius_mm
        status = "PASS" if first_hit_is_target and aperture_pass else "BLOCKED"
        if status != "PASS":
            failures.append(f"{edge['id']}: full-target zero-radius first-hit/aperture gate")
        edge_audits.append({
            "edge_id": edge["id"], "from_node": edge["from_node"], "to_node": edge["to_node"],
            "branch_id": edge["branch_id"], "direction": edge["direction"],
            "zero_radius_start_m": list(start), "zero_radius_end_m": list(end),
            "target_primary_object": target.name if target else None,
            "target_primary_surface_expected": primary_surface_expected,
            "first_hit_is_target_primary_or_open_aperture": first_hit_is_target,
            "measured_target_first_hit": target_hit,
            "semantic_port_line_offset_mm": semantic_port_line_offset_mm,
            "surface_hit_radial_offset_mm": surface_hit_radial_offset_mm,
            "measured_target_aperture_offset_mm": radial_offset_mm,
            "target_clear_aperture_radius_mm": aperture_radius_mm,
            "collision_count_before_target": len(collisions), "collisions_before_target": collisions,
            "all_physical_hits_to_80mm_past_target": hits,
            "physical_object_scope_count": len(physical_objects),
            "modeled_physical_object_scope_count": len(modeled_physical_objects),
            "ray_method": "WORLD_BVH_TWO_SIDED_FULL_TARGET_TRAVERSAL",
            "aperture_measurement_mode": aperture_measurement_mode,
            "status": status,
        })

    # Narrow-phase BVH overlaps between each modeled generic load link and its
    # declared from/to load-path objects.
    cache = BVHCache(maximum=8)
    load_links = [obj for obj in bpy.data.objects if obj.name.startswith("MODELED_LOAD_LINK__") or obj.name.startswith("MODELED_FRAME_TABLE_LOAD_LINK__")]
    load_contact_audits = []
    contact_fail_nodes = set()
    for link in sorted(load_links, key=lambda item: item.name):
        link_bbox = object_world_bbox(link)
        endpoints = []
        for endpoint_kind in ("from_object", "to_object"):
            endpoint_name = link.get(endpoint_kind)
            endpoint = bpy.data.objects.get(endpoint_name) if endpoint_name else None
            if not endpoint or endpoint.type != "MESH":
                endpoints.append({"kind": endpoint_kind, "object_name": endpoint_name, "bvh_contact_pairs": 0, "status": "BLOCKED"})
                continue
            endpoint_bbox = object_bbox.get(endpoint.name) or object_world_bbox(endpoint)
            if not aabb_overlap(link_bbox, endpoint_bbox):
                pairs = 0
            else:
                pairs = len(cache.get(link).overlap(cache.get(endpoint)))
            endpoints.append({
                "kind": endpoint_kind, "object_name": endpoint.name, "aabb_overlap": aabb_overlap(link_bbox, endpoint_bbox),
                "bvh_contact_pairs": pairs, "status": "PASS" if pairs >= build["audit_thresholds"]["load_link_minimum_bvh_pairs"] else "BLOCKED",
            })
        status = "PASS" if all(item["status"] == "PASS" for item in endpoints) else "BLOCKED"
        node_id = link.get("node_id", "GLOBAL")
        if status != "PASS":
            contact_fail_nodes.add(node_id)
        load_contact_audits.append({
            "link_object": link.name, "node_id": node_id,
            "provenance": link.get("provenance"), "official_thorlabs_claim": link.get("official_thorlabs_claim"),
            "endpoints": endpoints, "status": status,
        })
    if contact_fail_nodes:
        failures.append(f"load-link narrow-phase contact failures: {sorted(contact_fail_nodes)}")

    n24_stage = next(
        obj for obj in official_objects
        if obj.get("node_id") == "N24" and obj.get("assembly_subrole") == "GUIDED_PIEZO_STAGE"
    )
    n24_controller = next(
        obj for obj in official_objects
        if obj.get("node_id") == "N24" and obj.get("assembly_subrole") == "PAIRED_CONTROLLER"
    )
    n24_stage_links = [
        item for item in load_contact_audits
        if any(endpoint["object_name"] == n24_stage.name for endpoint in item["endpoints"])
    ]
    n24_stage_endpoint_contacts = [
        endpoint for item in n24_stage_links for endpoint in item["endpoints"]
        if endpoint["object_name"] == n24_stage.name
    ]
    controller_in_load_path = any(
        endpoint["object_name"] == n24_controller.name
        for item in load_contact_audits for endpoint in item["endpoints"]
    )
    n24_stage_load_path = {
        "stage_object": n24_stage.name,
        "stage_subrole": n24_stage.get("assembly_subrole"),
        "controller_object": n24_controller.name,
        "controller_subrole": n24_controller.get("assembly_subrole"),
        "stage_link_objects": [item["link_object"] for item in n24_stage_links],
        "stage_endpoint_contacts": n24_stage_endpoint_contacts,
        "stage_endpoint_contact_count": len(n24_stage_endpoint_contacts),
        "controller_in_load_path": controller_in_load_path,
        "status": "PASS" if (
            len(n24_stage_endpoint_contacts) >= 2
            and all(item["status"] == "PASS" for item in n24_stage_endpoint_contacts)
            and not controller_in_load_path
        ) else "BLOCKED",
        "claim_boundary": "GEOMETRIC_MODELED_LOAD_PATH_ONLY; LITERAL_TRAVEL_AND_DYNAMIC_PERFORMANCE_BLOCKED",
    }
    if n24_stage_load_path["status"] != "PASS":
        failures.append("N24 stage/controller split or stage narrow-phase load path")

    # Direct N04 official clamp/optic narrow-phase evidence, independently
    # recomputed from this full saved Blend.
    n04_clamp = next(obj for obj in official_objects if obj.get("node_id") == "N04" and obj.get("part_number") == "SM1RC/M")
    n04_optic = next(obj for obj in official_objects if obj.get("node_id") == "N04" and obj.get("part_number") == "AC254-045-A-ML")
    n04_direct_pairs = len(cache.get(n04_clamp).overlap(cache.get(n04_optic))) if aabb_overlap(object_bbox[n04_clamp.name], object_bbox[n04_optic.name]) else 0
    n04_contact = {
        "clamp_object": n04_clamp.name, "optic_object": n04_optic.name,
        "narrow_phase_bvh_contact_pairs": n04_direct_pairs,
        "status": "PASS" if n04_direct_pairs > 0 else "BLOCKED",
        "claim_boundary": "GEOMETRIC_RETENTION_ONLY; FORCE_TORQUE_AND_LITERAL_PERFORMANCE_BLOCKED",
    }
    if n04_contact["status"] != "PASS":
        failures.append("N04 direct official clamp/optic contact absent")

    node_by_id = {item["node_id"]: item for item in node_audits}
    family_audits = []
    for family in family_lock["families"]:
        node_ids = family["node_ids"]
        family_instance = [item for item in instance_audits if item["node_id"] in node_ids]
        family_load = [item for item in load_contact_audits if item["node_id"] in node_ids]
        if family["family_id"] == "EXPERIMENTAL_CHAMBER":
            # ponytail: this one literature-specific object is deliberately not
            # catalog CAD, so its evidence keys must never imply an official claim.
            chamber = bpy.data.objects.get("MODELED_NON_THORLABS__N15__EXPERIMENTAL_CHAMBER")
            expected_dimensions = Vector((0.085, 0.070, 0.070))
            checks = {
                "declared_modeled_non_thorlabs_identity": bool(
                    chamber
                    and chamber.get("official_thorlabs_claim") is False
                    and chamber.get("catalog_component_claim") is False
                    and chamber.get("provenance") == "MODELED_NON_THORLABS_LITERATURE_SPECIFIC_EXPERIMENTAL_CHAMBER"
                ),
                "declared_modeled_bbox_and_scale": bool(
                    chamber
                    and (Vector(chamber.dimensions) - expected_dimensions).length <= 1e-6
                    and node_by_id["N15"]["port_center_error_mm"] <= 0.05
                ),
                "modeled_semantic_port": node_by_id["N15"]["port_center_error_mm"] <= 0.05,
                "post_and_load_path": all(item["status"] == "PASS" for item in family_load) and bool(family_load),
                "reopen_modeled_mesh_cleanliness": bool(chamber and mesh_face_quality(chamber.data)["invalid_face_count"] == 0),
                "zero_radius_aperture_ray": node_by_id["N15"]["status"] == "PASS",
                "narrow_phase_bvh": all(item["status"] == "PASS" for item in family_load) and bool(family_load),
            }
            evidence_basis = "DECLARED_MODELED_NON_THORLABS_EXPERIMENTAL_OBJECT"
        else:
            checks = {
                "official_cad_bbox_and_scale": bool(family_instance) and all(item["status"] == "PASS" for item in family_instance),
                "cad_native_semantic_port": all(node_by_id[node_id]["port_center_error_mm"] <= 0.05 and node_by_id[node_id]["axis_angular_error_deg"] <= 0.05 for node_id in node_ids),
                "post_and_load_path": all(item["status"] == "PASS" for item in family_load) and bool(family_load),
                "reopen_mesh_cleanliness": bool(family_instance) and all(item["mesh_face_quality"]["invalid_face_count"] == 0 for item in family_instance),
                "zero_radius_aperture_ray": all(node_by_id[node_id]["status"] == "PASS" for node_id in node_ids),
                "narrow_phase_bvh": all(item["status"] == "PASS" for item in family_load) and bool(family_load),
            }
            evidence_basis = "EXACT_OFFICIAL_THORLABS_CAD_WITH_INDEPENDENT_FAMILY_GATE"
        status = "PASS" if all(checks.values()) else "BLOCKED"
        if status != "PASS":
            failures.append(f"family gate {family['family_id']}")
        family_audits.append({
            "family_id": family["family_id"], "node_ids": node_ids,
            "evidence_basis": evidence_basis,
            "inherited_n04_pass": False, "checks": checks, "status": status,
        })

    branch_ids = sorted(set(edge["branch_id"] for edge in topology["edges"]))
    branch_audits = []
    for branch_id in branch_ids:
        items = [item for item in edge_audits if item["branch_id"] == branch_id]
        status = "PASS" if items and all(item["status"] == "PASS" for item in items) else "BLOCKED"
        branch_audits.append({"branch_id": branch_id, "edge_count": len(items), "edge_ids": [item["edge_id"] for item in items], "status": status})
        if status != "PASS":
            failures.append(f"branch gate {branch_id}")

    status = "PASS" if not failures else "BLOCKED"
    report = {
        "schema": "opticalmodeler.full32.reopen-regression.v3",
        "status": status,
        "scope": "FULL_32_NODE_PROPAGATION_GATE_V3",
        "blender_version": bpy.app.version_string,
        "opened_blend": {"relative_path": str(current_path.relative_to(ROOT)).replace("\\", "/"), "bytes": current_path.stat().st_size, "sha256": sha256(current_path)},
        "scene_status_readback": scene_readback,
        "counts": {
            "nodes": len(node_audits), "directed_edges": len(edge_audits), "families": len(family_audits),
            "branch_ids": len(branch_audits), "official_instances": len(instance_audits),
            "used_mesh_objects": len(used_mesh_objects), "unique_serialized_meshes": len(mesh_quality),
            "physical_objects_in_zero_radius_scope": len(physical_objects),
            "modeled_physical_objects_in_zero_radius_scope": len(modeled_physical_objects),
            "modeled_load_links": len(load_contact_audits),
        },
        "mesh_reopen_audit": {
            "scope": "ALL_IN_USE_MESH_DATABLOCKS_WITHOUT_OFFICIAL_OR_PRESENTATION_EXCLUSION",
            "status": "PASS" if all(item["invalid_face_count"] == 0 for item in mesh_quality.values()) else "BLOCKED",
            "by_mesh": mesh_quality,
        },
        "official_instance_audits": instance_audits,
        "node_audits": node_audits,
        "edge_zero_radius_audits": edge_audits,
        "branch_audits": branch_audits,
        "load_contact_audits": load_contact_audits,
        "n24_stage_controller_load_path": n24_stage_load_path,
        "n04_direct_clamp_contact": n04_contact,
        "family_audits": family_audits,
        "status_boundaries": {
            "model_scope": "PARTIAL_SCOPED", "literal_paper_performance": "BLOCKED",
            "substitution_count": 17, "S4FC488_source_diagnostics": "PARTIAL_SCOPED",
            "S4FC637_source_diagnostics": "PARTIAL_SCOPED",
            "final_or_release": "BLOCKED",
            "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
        },
        "failures": failures,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status, "nodes": len(node_audits), "edges": len(edge_audits), "families": len(family_audits),
        "load_links": len(load_contact_audits), "load_fail_nodes": sorted(contact_fail_nodes),
        "node_failures": [item["node_id"] for item in node_audits if item["status"] != "PASS"],
        "edge_failures": [item["edge_id"] for item in edge_audits if item["status"] != "PASS"],
        "n04_contact_pairs": n04_direct_pairs, "failure_count": len(failures), "failures": failures[:30],
        "report": str(REPORT_PATH.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2), flush=True)
    if status != "PASS":
        raise RuntimeError("full reopened regression BLOCKED")

    bpy.context.scene["propagation_gate_status"] = "PASS"
    bpy.context.scene["propagation_gate_reason"] = "SAVED_BLEND_REOPEN_REGRESSION_PASSED"
    bpy.context.scene["full_32_node_propagation_gate"] = "PASS"
    bpy.context.scene["reopen_regression_sha256"] = sha256(REPORT_PATH)
    bpy.ops.wm.save_as_mainfile(filepath=str(AUDITED_BLEND), check_existing=False)
    print(json.dumps({
        "status": "PASS", "audited_blend": str(AUDITED_BLEND.relative_to(ROOT)).replace("\\", "/"),
        "bytes": AUDITED_BLEND.stat().st_size,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
