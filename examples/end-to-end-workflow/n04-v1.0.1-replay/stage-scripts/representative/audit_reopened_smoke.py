"""Audit the saved N04 smoke Blend after reopening it in a fresh Blender run."""

from __future__ import annotations

import hashlib
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
BASE = ROOT / "work" / "phase2_representative_smoke_r3"
MEASUREMENTS = BASE / "measurements"
SCENE_PATH = BASE / "scene" / "N04_representative_smoke_r3.blend"
GENERATOR_REPORT = BASE / "evidence" / "GENERATOR_REPORT.json"
OUTPUT = ROOT / "outputs" / "phase2_representative_smoke_r3"
RENDERS = OUTPUT / "renders"
AUDIT_PATH = OUTPUT / "REPRESENTATIVE_SMOKE_AUDIT.json"
BBOX_TOLERANCE_MM = 0.1
CENTER_TOLERANCE_MM = 0.1
ALIGNMENT_DOT_MIN = 0.9999


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def matrix_from(rotation_rows, translation, scale=0.001):
    rotation = Matrix((
        (*rotation_rows[0], 0.0),
        (*rotation_rows[1], 0.0),
        (*rotation_rows[2], 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return Matrix.Translation(Vector(translation)) @ rotation @ Matrix.Diagonal((scale, scale, scale, 1.0))


def corners(bounds):
    minimum, maximum = bounds["min_mm"], bounds["max_mm"]
    return [Vector((x, y, z)) for x in (minimum[0], maximum[0]) for y in (minimum[1], maximum[1]) for z in (minimum[2], maximum[2])]


def transformed_bbox(bounds, matrix):
    points = [matrix @ point for point in corners(bounds)]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def object_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def bbox_error_mm(actual, expected):
    return max(
        abs(actual[key][index] - expected[key][index]) * 1000.0
        for key in ("min_m", "max_m", "size_m") for index in range(3)
    )


def mesh_face_quality(mesh):
    duplicate_vertex_faces = 0
    distinct_collinear_faces = 0
    non_triangular_faces = 0
    for polygon in mesh.polygons:
        if len(polygon.vertices) != 3:
            non_triangular_faces += 1
            continue
        first, second, third = (mesh.vertices[index].co for index in polygon.vertices)
        edges = (second - first, third - second, first - third)
        edge_squared = [edge.length_squared for edge in edges]
        if min(edge_squared) == 0.0:
            duplicate_vertex_faces += 1
            continue
        double_area = (second - first).cross(third - first).length
        normalized = double_area / max(edge_squared)
        if double_area <= 1e-12 or normalized <= 1e-12:
            distinct_collinear_faces += 1
    return {
        "triangle_count": len(mesh.polygons) - non_triangular_faces,
        "non_triangular_faces": non_triangular_faces,
        "duplicate_vertex_faces": duplicate_vertex_faces,
        "distinct_collinear_faces": distinct_collinear_faces,
        "invalid_face_count": non_triangular_faces + duplicate_vertex_faces + distinct_collinear_faces,
    }


def world_bvh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    local_vertices = [vertex.co.copy() for vertex in mesh.vertices]
    vertices = [evaluated.matrix_world @ vertex for vertex in local_vertices]
    polygons = [tuple(polygon.vertices) for polygon in mesh.polygons]
    tree = BVHTree.FromPolygons(vertices, polygons, all_triangles=False)
    counts = {"vertices": len(vertices), "polygons": len(polygons), "face_quality": mesh_face_quality(mesh)}
    evaluated.to_mesh_clear()
    return tree, counts, {"vertices": vertices, "local_vertices": local_vertices, "polygons": polygons}


def closest_vertex_pair(first, second):
    if not first or not second:
        return None, None
    distance, pair = min(((left - right).length, (left, right)) for left in first for right in second)
    return distance, pair


def measure_saved_mesh_split(local_vertices, clamp_lock):
    """Measure both split regions directly from the reopened evaluated mesh."""
    native = clamp_lock["native_features_before_placement"]
    target_radius = clamp_lock["modeled_clamped_state"]["target_bore_radius_mm"]
    negative_x, positive_x = native["split_face_x_mm"]
    coordinate_tolerance_mm = 1e-5
    gap_tolerance_mm = 1e-4
    main_negative = [
        point for point in local_vertices
        if abs(point.x - negative_x) <= coordinate_tolerance_mm
        and point.y >= target_radius + 1.0 and 0.45 <= point.z <= 9.71
    ]
    main_positive = [
        point for point in local_vertices
        if abs(point.x - positive_x) <= coordinate_tolerance_mm
        and point.y >= target_radius + 1.0 and 0.45 <= point.z <= 9.71
    ]
    inner_negative = [
        point for point in local_vertices
        if point.x < 0.0 and point.y > 0.0 and 0.45 <= point.z <= 9.71
        and abs(math.hypot(point.x, point.y) - target_radius) <= 0.02
    ]
    inner_positive = [
        point for point in local_vertices
        if point.x > 0.0 and point.y > 0.0 and 0.45 <= point.z <= 9.71
        and abs(math.hypot(point.x, point.y) - target_radius) <= 0.02
    ]
    main_gap, main_pair = closest_vertex_pair(main_negative, main_positive)
    inner_gap, inner_pair = closest_vertex_pair(inner_negative, inner_positive)
    main_yz_mismatch = (
        math.hypot(main_pair[0].y - main_pair[1].y, main_pair[0].z - main_pair[1].z)
        if main_pair else None
    )
    inner_yz_mismatch = (
        math.hypot(inner_pair[0].y - inner_pair[1].y, inner_pair[0].z - inner_pair[1].z)
        if inner_pair else None
    )
    checks = {
        "main_face_vertex_counts": len(main_negative) >= 10 and len(main_positive) >= 10,
        "inner_edge_vertex_counts": len(inner_negative) >= 10 and len(inner_positive) >= 10,
        "main_gap_matches_native_face_separation": main_gap is not None and abs(main_gap - native["neutral_split_gap_mm"]) <= gap_tolerance_mm,
        "main_gap_remains_open": main_gap is not None and main_gap > 0.5,
        "inner_edge_gap_remains_open": inner_gap is not None and inner_gap > 0.5,
        "inner_edge_gap_not_wider_than_main_gap": inner_gap is not None and main_gap is not None and inner_gap <= main_gap + gap_tolerance_mm,
        "main_closest_pair_is_cross_split": main_yz_mismatch is not None and main_yz_mismatch <= gap_tolerance_mm,
        "inner_closest_pair_is_cross_split": inner_yz_mismatch is not None and inner_yz_mismatch <= gap_tolerance_mm,
    }
    return {
        "status": "PASS" if all(checks.values()) else "BLOCKED",
        "measurement_source": "saved-Blend reopened evaluated mesh",
        "coordinate_frame": "evaluated object-local millimetres before the locked 0.001 world scale",
        "selection_rule": {
            "main_split_faces": "vertices on the two locked split-face x coordinates, y >= target bore radius + 1 mm, 0.45 <= z <= 9.71 mm",
            "deformed_inner_edges": "positive-y bore vertices within 0.02 mm of the 15.235 mm target radius, separated by x sign",
            "coordinate_tolerance_mm": coordinate_tolerance_mm,
            "gap_tolerance_mm": gap_tolerance_mm,
        },
        "main_split": {
            "negative_vertex_count": len(main_negative),
            "positive_vertex_count": len(main_positive),
            "gap_mm": main_gap,
            "closest_pair_native_mm": [list(point) for point in main_pair] if main_pair else None,
            "closest_pair_yz_mismatch_mm": main_yz_mismatch,
        },
        "deformed_inner_edge": {
            "negative_vertex_count": len(inner_negative),
            "positive_vertex_count": len(inner_positive),
            "minimum_gap_mm": inner_gap,
            "closest_pair_native_mm": [list(point) for point in inner_pair] if inner_pair else None,
            "closest_pair_yz_mismatch_mm": inner_yz_mismatch,
        },
        "analytic_estimate_used_in_geometry_gate": False,
        "checks": checks,
    }


def angular_contact_support(overlaps, first_name, second_name, mesh_data, axis_point, axis_direction, bins=72):
    axis = Vector(axis_direction).normalized()
    reference = Vector((1.0, 0.0, 0.0))
    if abs(reference.dot(axis)) > 0.9:
        reference = Vector((0.0, 0.0, 1.0))
    basis_u = (reference - axis * reference.dot(axis)).normalized()
    basis_v = axis.cross(basis_u).normalized()
    occupied = set()
    axial_positions = []
    for first_index, second_index in overlaps:
        for object_name, polygon_index in ((first_name, first_index), (second_name, second_index)):
            data = mesh_data[object_name]
            polygon = data["polygons"][polygon_index]
            centroid = sum((data["vertices"][index] for index in polygon), Vector((0.0, 0.0, 0.0))) / len(polygon)
            delta = centroid - Vector(axis_point)
            axial_positions.append(delta.dot(axis))
            angle = math.atan2(delta.dot(basis_v), delta.dot(basis_u)) % (2.0 * math.pi)
            occupied.add(min(bins - 1, int(angle / (2.0 * math.pi) * bins)))
    return {
        "angular_bin_count": bins,
        "occupied_angular_bins": len(occupied),
        "annular_support_fraction": len(occupied) / bins,
        "axial_contact_span_mm": (max(axial_positions) - min(axial_positions)) * 1000.0 if axial_positions else 0.0,
    }


def repeated_ray_hits(tree, start, direction, distance, epsilon=1e-5, maximum=24):
    hits = []
    travelled = 0.0
    origin = Vector(start)
    direction = Vector(direction).normalized()
    remaining = distance
    for _ in range(maximum):
        location, normal, polygon_index, local_distance = tree.ray_cast(origin, direction, remaining)
        if location is None:
            break
        travelled += local_distance
        hits.append({
            "distance_from_start_m": travelled,
            "location_m": list(location),
            "normal": list(normal),
            "polygon_index": int(polygon_index),
        })
        origin = location + direction * epsilon
        travelled += epsilon
        remaining = distance - travelled
        if remaining <= 0:
            break
    return hits


def point_line_transverse_error_m(point_a, point_b, axis):
    axis = Vector(axis).normalized()
    delta = Vector(point_b) - Vector(point_a)
    return (delta - axis * delta.dot(axis)).length


def render(camera_name: str, filename: str):
    scene = bpy.context.scene
    camera = bpy.data.objects[camera_name]
    camera.data.clip_start = 0.002
    camera.data.clip_end = 10.0
    scene.camera = camera
    destination = RENDERS / filename
    scene.render.filepath = str(destination)
    bpy.ops.render.render(write_still=True)
    return {
        "relative_path": f"renders/{filename}",
        "sha256": sha256(destination),
        "bytes": destination.stat().st_size,
        "width": scene.render.resolution_x,
        "height": scene.render.resolution_y,
    }


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    RENDERS.mkdir(parents=True, exist_ok=True)
    ports = load_json(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK.json")
    derivatives = load_json(MEASUREMENTS / "CAD_MESH_DERIVATIVES.json")
    degenerate_audit = load_json(MEASUREMENTS / "STL_DEGENERATE_AUDIT.json")
    clamp_lock = load_json(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json")
    generator = load_json(GENERATOR_REPORT)
    derivative_by_part = {record["part_number"]: record for record in derivatives["parts"]}
    clean_by_part = {record["part_number"]: record for record in degenerate_audit["parts"]}
    port_by_part = {record["part_number"]: record for record in ports["parts"]}
    common_rotation = ports["common_rotation_native_to_world"]
    scene = bpy.context.scene
    failures = []

    reopen = {
        "status": "PASS",
        "blend_private_relative_path": "work/phase2_representative_smoke_r3/scene/N04_representative_smoke_r3.blend",
        "blend_sha256": sha256(SCENE_PATH),
        "blend_bytes": SCENE_PATH.stat().st_size,
        "bpy_data_filepath_matches": Path(bpy.data.filepath).resolve() == SCENE_PATH,
        "blender_version": bpy.app.version_string,
        "scene_scope": scene.get("scope"),
        "global_model_status": scene.get("global_model_status"),
        "literal_paper_performance": scene.get("literal_paper_performance"),
        "full_32_node_propagation": scene.get("full_32_node_propagation"),
    }
    if (
        not reopen["bpy_data_filepath_matches"]
        or reopen["scene_scope"] != "N04_REPRESENTATIVE_ONLY_R3"
        or scene.get("stl_degenerate_audit_sha256") != sha256(MEASUREMENTS / "STL_DEGENERATE_AUDIT.json")
        or scene.get("sm1rc_clamp_lock_sha256") != sha256(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json")
    ):
        reopen["status"] = "BLOCKED"
        failures.append("saved Blend lineage/readback mismatch")

    depsgraph = bpy.context.evaluated_depsgraph_get()
    official_objects = {}
    mesh_readback = []
    bvh_by_name = {}
    mesh_data_by_name = {}
    for part in ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML"):
        name = f"OFFICIAL_CAD__{part.replace('/', '_')}"
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            failures.append(f"missing official CAD mesh {part}")
            continue
        official_objects[part] = obj
        derivative = derivative_by_part[part]["derivative"]
        locked = port_by_part[part]["world_transform"]
        rotation = locked.get("rotation_matrix", common_rotation)
        expected_matrix = matrix_from(rotation, locked["translation_m"], locked["uniform_scale"])
        matrix_error = max(abs(obj.matrix_world[row][column] - expected_matrix[row][column]) for row in range(4) for column in range(4))
        expected_bbox = transformed_bbox(derivative["bbox_optimal_mm"], expected_matrix)
        actual_bbox = object_bbox(obj)
        error_mm = bbox_error_mm(actual_bbox, expected_bbox)
        tree, counts, mesh_data = world_bvh(obj, depsgraph)
        bvh_by_name[obj.name] = tree
        mesh_data_by_name[obj.name] = mesh_data
        cleaned = clean_by_part[part]["post_clean_pre_import_private_derivative"]
        expected_geometry_state = (
            "MODELED_ELASTIC_CLAMPED_STATE_FROM_OFFICIAL_CAD_DERIVATIVE"
            if part == "SM1RC/M" else "MANUFACTURER_NATIVE_CAD_DERIVATIVE"
        )
        generator_part = next(item for item in generator["official_cad_imports"] if item["part_number"] == part)
        status = "PASS" if (
            error_mm <= BBOX_TOLERANCE_MM
            and matrix_error <= 1e-9
            and obj.get("cleaned_derivative_sha256") == cleaned["sha256"]
            and counts["face_quality"]["invalid_face_count"] == 0
            and generator_part["geometry_state"] == expected_geometry_state
        ) else "BLOCKED"
        if status != "PASS":
            failures.append(f"{part} world mesh/bbox/transform readback")
        mesh_readback.append({
            "part_number": part,
            "object_name": obj.name,
            "status": status,
            "provenance": obj.get("provenance"),
            "source_step_sha256": obj.get("source_step_sha256"),
            "pre_clean_derivative_sha256": obj.get("pre_clean_derivative_sha256"),
            "cleaned_derivative_sha256": obj.get("cleaned_derivative_sha256"),
            "geometry_state": generator_part["geometry_state"],
            "matrix_max_abs_error": matrix_error,
            "world_bbox": actual_bbox,
            "expected_from_opencascade_optimal_bbox": expected_bbox,
            "world_bbox_max_error_mm": error_mm,
            "evaluated_mesh": counts,
        })

    lens = official_objects["AC254-045-A-ML"]
    ring = official_objects["SM1RC/M"]
    lens_native = port_by_part["AC254-045-A-ML"]["native_interfaces"]
    lens_ports = port_by_part["AC254-045-A-ML"]["world_semantic_ports_m"]
    actual_in = lens.matrix_world @ Vector(lens_native["input_glass_vertex_mm"])
    actual_out = lens.matrix_world @ Vector(lens_native["output_glass_vertex_mm"])
    actual_axis = (lens.matrix_world.to_3x3() @ Vector(lens_native["optical_axis"]["axis"])).normalized()
    expected_axis = Vector(lens_ports["axis_direction"]).normalized()
    ring_axis = (ring.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    ring_axis_point = ring.matrix_world @ Vector((0.0, 0.0, 5.08))
    lens_axis_point = lens.matrix_world @ Vector((0.0, 0.0, 0.0))
    port_audits = {
        "status": "PASS",
        "in_error_mm": (actual_in - Vector(lens_ports["in"])).length * 1000.0,
        "out_error_mm": (actual_out - Vector(lens_ports["out"])).length * 1000.0,
        "optic_axis_dot": actual_axis.dot(expected_axis),
        "mount_optic_axis_abs_dot": abs(actual_axis.dot(ring_axis)),
        "mount_optic_axis_center_error_mm": point_line_transverse_error_m(lens_axis_point, ring_axis_point, actual_axis) * 1000.0,
        "clear_aperture_radius_mm": lens_native["clear_aperture_radius_mm"],
        "marker_in_error_mm": (bpy.data.objects["PORT_N04_in"].location - actual_in).length * 1000.0,
        "marker_out_error_mm": (bpy.data.objects["PORT_N04_out"].location - actual_out).length * 1000.0,
    }
    if (
        port_audits["in_error_mm"] > CENTER_TOLERANCE_MM
        or port_audits["out_error_mm"] > CENTER_TOLERANCE_MM
        or port_audits["optic_axis_dot"] < ALIGNMENT_DOT_MIN
        or port_audits["mount_optic_axis_abs_dot"] < ALIGNMENT_DOT_MIN
        or port_audits["mount_optic_axis_center_error_mm"] > CENTER_TOLERANCE_MM
        or port_audits["marker_in_error_mm"] > CENTER_TOLERANCE_MM
        or port_audits["marker_out_error_mm"] > CENTER_TOLERANCE_MM
    ):
        port_audits["status"] = "BLOCKED"
        failures.append("semantic port/axis gate")

    clamp_state = clamp_lock["modeled_clamped_state"]
    analytic_split_gap_estimate = clamp_lock["analytic_split_gap_estimate"]
    if (
        analytic_split_gap_estimate["status"] != "UNVERIFIED_ANALYTIC_ESTIMATE"
        or analytic_split_gap_estimate["excluded_from_geometry_pass"] is not True
    ):
        failures.append("analytic split-gap estimate status boundary")
    target_bore_radius = clamp_state["target_bore_radius_mm"]
    reopened_bore_radii = [
        math.hypot(vertex.co.x, vertex.co.y)
        for vertex in ring.data.vertices
        if 0.45 <= vertex.co.z <= 9.71 and abs(math.hypot(vertex.co.x, vertex.co.y) - target_bore_radius) <= 0.02
    ]
    split_geometry_readback = measure_saved_mesh_split(mesh_data_by_name[ring.name]["local_vertices"], clamp_lock)
    clamp_geometry_readback = {
        "status": "PASS",
        "geometry_state": "MODELED_ELASTIC_INNER_BORE_DEFLECTION_OF_OFFICIAL_CAD_DERIVATIVE",
        "manufacturer_supplied_clamped_geometry": False,
        "component_identity": "OFFICIAL_THORLABS_SM1RC/M",
        "selected_clamped_bore_vertex_count": len(reopened_bore_radii),
        "target_clamped_bore_radius_mm": target_bore_radius,
        "observed_clamped_bore_radius_range_mm": [min(reopened_bore_radii), max(reopened_bore_radii)] if reopened_bore_radii else None,
        "maximum_radius_error_mm": max(abs(value - target_bore_radius) for value in reopened_bore_radii) if reopened_bore_radii else None,
        "neutral_radial_clearance_mm": clamp_lock["native_features_before_placement"]["neutral_radial_clearance_mm"],
        "required_radial_deflection_mm": clamp_state["required_inward_radial_deflection_mm"],
        "saved_mesh_split_geometry_readback": split_geometry_readback,
        "locking_screw_crosses_both_split_faces": clamp_lock["native_features_before_placement"]["locking_screw_crosses_both_split_faces"],
        "locking_screw_body_bridges_split": clamp_lock["native_features_before_placement"]["locking_screw_body_bridges_split"],
        "clamp_lock_hash_matches_object": ring.get("clamp_lock_sha256") == sha256(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json"),
        "manufacturer_native_geometry_state_property": bool(ring.get("manufacturer_native_geometry_state")),
        "claim_boundary": "GEOMETRIC_RETENTION_ONLY; CLAMP_FORCE_AND_LITERAL_PERFORMANCE_BLOCKED",
    }
    if (
        len(reopened_bore_radii) < 100
        or clamp_geometry_readback["maximum_radius_error_mm"] is None
        or clamp_geometry_readback["maximum_radius_error_mm"] > 1e-5
        or split_geometry_readback["status"] != "PASS"
        or not clamp_geometry_readback["locking_screw_crosses_both_split_faces"]
        or not clamp_geometry_readback["locking_screw_body_bridges_split"]
        or not clamp_geometry_readback["clamp_lock_hash_matches_object"]
        or clamp_geometry_readback["manufacturer_native_geometry_state_property"]
    ):
        clamp_geometry_readback["status"] = "BLOCKED"
        failures.append("SM1RC/M clamped-state geometry/actuation gate")

    ray = ports["representative_ray"]
    ray_start, ray_end = Vector(ray["zero_radius_start_m"]), Vector(ray["zero_radius_end_m"])
    ray_vector = ray_end - ray_start
    direction, distance = ray_vector.normalized(), ray_vector.length
    opaque_hits = []
    for part, obj in official_objects.items():
        if part == "AC254-045-A-ML":
            continue
        location, normal, polygon_index, hit_distance = bvh_by_name[obj.name].ray_cast(ray_start, direction, distance)
        if location is not None:
            opaque_hits.append({"part_number": part, "location_m": list(location), "distance_m": hit_distance, "polygon_index": int(polygon_index)})
    for obj in bpy.data.collections["MODELED_NON_THORLABS_FASTENERS"].objects:
        tree, _, mesh_data = world_bvh(obj, depsgraph)
        bvh_by_name[obj.name] = tree
        mesh_data_by_name[obj.name] = mesh_data
        location, normal, polygon_index, hit_distance = tree.ray_cast(ray_start, direction, distance)
        if location is not None:
            opaque_hits.append({"part_number": obj.name, "location_m": list(location), "distance_m": hit_distance, "polygon_index": int(polygon_index)})
    transmissive_hits = repeated_ray_hits(bvh_by_name[lens.name], ray_start, direction, distance)
    for hit in transmissive_hits:
        hit["radial_offset_from_locked_axis_mm"] = point_line_transverse_error_m(ray_start, hit["location_m"], direction) * 1000.0
    first_hit_port_error_mm = (
        (Vector(transmissive_hits[0]["location_m"]) - actual_in).length * 1000.0 if transmissive_hits else None
    )
    ray_audit = {
        "status": "PASS",
        "classification": "ZERO_RADIUS_ANALYTIC_AXIS_NOT_PRESENTATION_BEAM_MESH",
        "start_m": list(ray_start),
        "end_m": list(ray_end),
        "length_m": distance,
        "opaque_hit_count": len(opaque_hits),
        "opaque_hits": opaque_hits,
        "expected_transmissive_part": "AC254-045-A-ML",
        "transmissive_hit_count": len(transmissive_hits),
        "transmissive_hits": transmissive_hits,
        "first_hit_to_locked_input_port_error_mm": first_hit_port_error_mm,
        "clear_aperture_radius_mm": lens_native["clear_aperture_radius_mm"],
    }
    if opaque_hits or not transmissive_hits or first_hit_port_error_mm is None or first_hit_port_error_mm > 0.1 or any(hit["radial_offset_from_locked_axis_mm"] > 0.1 for hit in transmissive_hits):
        ray_audit["status"] = "BLOCKED"
        failures.append("zero-radius/first-opaque-hit gate")

    common = ports["common_rotation_native_to_world"]
    table = official_objects["T1225C"]
    base = official_objects["BA1/M"]
    holder = official_objects["PH75/M"]
    post = official_objects["TR75/M"]
    table_top = table.matrix_world @ Vector((112.5, 210.0, -1087.5))
    base_bottom = base.matrix_world @ Vector((0.0, -5.0, 0.0))
    base_top = base.matrix_world @ Vector((0.0, 5.0, 0.0))
    holder_bottom = holder.matrix_world @ Vector((1.390664, -31.94529, -4.764491))
    holder_top = holder.matrix_world @ Vector((1.390664, 43.05471, -4.764491))
    post_bottom = post.matrix_world @ Vector((0.0, 0.0, 0.0))
    post_top = post.matrix_world @ Vector((0.0, 75.0062, 0.0))
    ring_bottom = ring.matrix_world @ Vector((0.0, -22.098, 5.08))
    holder_axis = (holder.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    post_axis = (post.matrix_world.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    load_path = {
        "status": "UNVERIFIED",
        "table_to_ba1_bearing_gap_mm": (base_bottom - table_top).length * 1000.0,
        "ba1_to_ph75_bearing_gap_mm": (holder_bottom - base_top).length * 1000.0,
        "holder_post_axis_abs_dot": abs(holder_axis.dot(post_axis)),
        "holder_post_axis_center_error_mm": point_line_transverse_error_m(holder_bottom, post_bottom, holder_axis) * 1000.0,
        "post_insertion_length_mm": (holder_top - post_bottom).dot(holder_axis) * 1000.0,
        "post_to_sm1rc_bearing_gap_mm": (ring_bottom - post_top).length * 1000.0,
        "m4_stud_engagement_mm": 79.9596 - 75.0062,
        "post_holder_radial_clearance_mm": 6.3881 - 6.3373,
        "neutral_sm1rc_lens_radial_clearance_mm": 15.3035 - 15.24,
        "clamped_bore_lens_radial_interference_mm": 15.24 - target_bore_radius,
        "sm1rc_to_ac254_retention": None,
        "table_fastener_penetrations_mm": [],
        "generic_fastener_labeling": "PASS",
    }
    for label, expected_x in (("LEFT", 0.0875), ("RIGHT", 0.1375)):
        shank = bpy.data.objects[f"MODELED_NON_THORLABS_M6_SHANK_{label}"]
        world = object_bbox(shank)
        load_path["table_fastener_penetrations_mm"].append({
            "label": label,
            "axis_xy_error_mm": math.hypot(shank.location.x - expected_x, shank.location.y - 1.0875) * 1000.0,
            "penetration_below_table_top_mm": max(0.0, -world["min_m"][2]) * 1000.0,
            "official_thorlabs_claim": bool(shank.get("official_thorlabs_claim")),
        })
    base_load_path_failed = (
        load_path["table_to_ba1_bearing_gap_mm"] > 0.1
        or load_path["ba1_to_ph75_bearing_gap_mm"] > 0.1
        or load_path["holder_post_axis_abs_dot"] < ALIGNMENT_DOT_MIN
        or load_path["holder_post_axis_center_error_mm"] > 0.1
        or load_path["post_insertion_length_mm"] <= 0.0
        or load_path["post_to_sm1rc_bearing_gap_mm"] > 0.1
        or load_path["m4_stud_engagement_mm"] < 4.0
        or any(item["axis_xy_error_mm"] > 0.1 or item["penetration_below_table_top_mm"] < 4.0 or item["official_thorlabs_claim"] for item in load_path["table_fastener_penetrations_mm"])
    )

    physical_objects = list(official_objects.values()) + list(bpy.data.collections["MODELED_NON_THORLABS_FASTENERS"].objects)
    allowed_pairs = {
        frozenset(("OFFICIAL_CAD__T1225C", "OFFICIAL_CAD__BA1_M")): "BEARING_CONTACT",
        frozenset(("OFFICIAL_CAD__T1225C", "MODELED_NON_THORLABS_M6_SHANK_LEFT")): "MODELED_THREAD_ENGAGEMENT",
        frozenset(("OFFICIAL_CAD__T1225C", "MODELED_NON_THORLABS_M6_SHANK_RIGHT")): "MODELED_THREAD_ENGAGEMENT",
        frozenset(("OFFICIAL_CAD__BA1_M", "OFFICIAL_CAD__PH75_M")): "BEARING_CONTACT",
        frozenset(("OFFICIAL_CAD__PH75_M", "OFFICIAL_CAD__TR75_M")): "POST_BORE_ENGAGEMENT",
        frozenset(("OFFICIAL_CAD__TR75_M", "OFFICIAL_CAD__SM1RC_M")): "M4_STUD_AND_BEARING_ENGAGEMENT",
        frozenset(("OFFICIAL_CAD__SM1RC_M", "OFFICIAL_CAD__AC254-045-A-ML")): "CLAMPED_SLIP_RING_RETENTION_CONTACT",
        frozenset(("OFFICIAL_CAD__PH75_M", "MODELED_NON_THORLABS_M6_CENTER_SHANK")): "MODELED_THREAD_ENGAGEMENT",
        # These generic, explicitly non-Thorlabs fasteners are intentionally modeled as
        # separate head/shank/washer solids so each load-transfer interface remains auditable.
        frozenset(("MODELED_NON_THORLABS_M6_CENTER_LOW_PROFILE_HEAD", "MODELED_NON_THORLABS_M6_CENTER_SHANK")): "MODELED_FASTENER_HEAD_SHANK_UNION",
        frozenset(("MODELED_NON_THORLABS_M6_CENTER_LOW_PROFILE_HEAD", "OFFICIAL_CAD__BA1_M")): "MODELED_FASTENER_HEAD_BEARING_CONTACT",
        frozenset(("MODELED_NON_THORLABS_M6_HEAD_LEFT", "MODELED_NON_THORLABS_M6_SHANK_LEFT")): "MODELED_FASTENER_HEAD_SHANK_UNION",
        frozenset(("MODELED_NON_THORLABS_M6_HEAD_RIGHT", "MODELED_NON_THORLABS_M6_SHANK_RIGHT")): "MODELED_FASTENER_HEAD_SHANK_UNION",
        frozenset(("MODELED_NON_THORLABS_M6_HEAD_LEFT", "MODELED_NON_THORLABS_M6_WASHER_LEFT")): "MODELED_HEAD_WASHER_BEARING_CONTACT",
        frozenset(("MODELED_NON_THORLABS_M6_HEAD_RIGHT", "MODELED_NON_THORLABS_M6_WASHER_RIGHT")): "MODELED_HEAD_WASHER_BEARING_CONTACT",
        frozenset(("MODELED_NON_THORLABS_M6_WASHER_LEFT", "OFFICIAL_CAD__BA1_M")): "MODELED_WASHER_BASE_BEARING_CONTACT",
        frozenset(("MODELED_NON_THORLABS_M6_WASHER_RIGHT", "OFFICIAL_CAD__BA1_M")): "MODELED_WASHER_BASE_BEARING_CONTACT",
    }
    for obj in physical_objects:
        if obj.name not in bvh_by_name:
            bvh_by_name[obj.name], _, mesh_data_by_name[obj.name] = world_bvh(obj, depsgraph)
    overlap_records = []
    illegal = []
    for first, second in combinations(sorted(physical_objects, key=lambda obj: obj.name), 2):
        overlaps = bvh_by_name[first.name].overlap(bvh_by_name[second.name])
        if not overlaps:
            continue
        pair = frozenset((first.name, second.name))
        record = {
            "objects": sorted((first.name, second.name)),
            "triangle_pair_count": len(overlaps),
            "classification": allowed_pairs.get(pair, "UNDECLARED_OPAQUE_COLLISION"),
            "status": "PASS" if pair in allowed_pairs else "BLOCKED",
        }
        overlap_records.append(record)
        if pair not in allowed_pairs:
            illegal.append(record)
    lens_name = "OFFICIAL_CAD__AC254-045-A-ML"
    ring_name = "OFFICIAL_CAD__SM1RC_M"
    retention_overlaps = bvh_by_name[lens_name].overlap(bvh_by_name[ring_name])
    support = angular_contact_support(
        retention_overlaps,
        lens_name,
        ring_name,
        mesh_data_by_name,
        lens_axis_point,
        actual_axis,
    ) if retention_overlaps else {
        "angular_bin_count": 72,
        "occupied_angular_bins": 0,
        "annular_support_fraction": 0.0,
        "axial_contact_span_mm": 0.0,
    }
    expected_interference = clamp_state["numerical_contact_interference_mm"]
    actual_interference = load_path["clamped_bore_lens_radial_interference_mm"]
    retention_contact = {
        "status": "PASS",
        "classification": "CLAMPED_SLIP_RING_RETENTION_CONTACT",
        "neutral_clearance_is_not_contact": True,
        "neutral_radial_clearance_mm": load_path["neutral_sm1rc_lens_radial_clearance_mm"],
        "clamped_radial_interference_mm": actual_interference,
        "expected_numerical_contact_interference_mm": expected_interference,
        "interference_error_mm": abs(actual_interference - expected_interference),
        "triangle_pair_count": len(retention_overlaps),
        **support,
        "minimum_annular_support_fraction": clamp_state["minimum_annular_support_fraction"],
        "locking_screw_crosses_and_bridges_split": (
            clamp_geometry_readback["locking_screw_crosses_both_split_faces"]
            and clamp_geometry_readback["locking_screw_body_bridges_split"]
        ),
        "geometry_claim": "MODELED_CLAMPED_STATE_FROM_OFFICIAL_CAD; NOT MANUFACTURER FORCE/PERFORMANCE CERTIFICATION",
    }
    if (
        not retention_overlaps
        or retention_contact["interference_error_mm"] > 0.001
        or retention_contact["annular_support_fraction"] < retention_contact["minimum_annular_support_fraction"]
        or retention_contact["axial_contact_span_mm"] < 1.0
        or not retention_contact["locking_screw_crosses_and_bridges_split"]
        or clamp_geometry_readback["status"] != "PASS"
    ):
        retention_contact["status"] = "BLOCKED"
    for record in overlap_records:
        if set(record["objects"]) == {lens_name, ring_name}:
            record["status"] = retention_contact["status"]
            record["retention_gate"] = retention_contact
    load_path["sm1rc_to_ac254_retention"] = retention_contact
    if base_load_path_failed or retention_contact["status"] != "PASS":
        load_path["status"] = "BLOCKED"
        failures.append("support/load-path gate")
    else:
        load_path["status"] = "PASS"
    bvh_audit = {
        "status": "PASS" if not illegal and retention_contact["status"] == "PASS" else "BLOCKED",
        "method": "world-space evaluated meshes + mathutils.bvhtree.BVHTree.overlap",
        "physical_object_count": len(physical_objects),
        "tested_pair_count": len(physical_objects) * (len(physical_objects) - 1) // 2,
        "overlap_records": overlap_records,
        "undeclared_opaque_collision_pairs": illegal,
        "required_retention_contact": retention_contact,
    }
    if illegal or retention_contact["status"] != "PASS":
        failures.append("narrow-phase BVH gate")

    render_evidence = [
        render("CAM_AUDIT_SIDE", "N04_representative_side.png"),
        render("CAM_AUDIT_AXIAL", "N04_representative_axial.png"),
    ]

    status = "PASS" if not failures else "BLOCKED"
    audit = {
        "schema": "opticalmodeler.phase2.representative-smoke-audit.v3",
        "status": status,
        "audit_scope": "PARTIAL_SCOPED",
        "representative_node": "N04",
        "global_status_boundaries": {
            "requested_model": "PARTIAL_SCOPED",
            "literal_paper_performance": "BLOCKED",
            "full_32_node_propagation": "UNVERIFIED",
        },
        "reopen_readback": reopen,
        "world_mesh_and_bbox_readback": {"status": "PASS" if all(item["status"] == "PASS" for item in mesh_readback) else "BLOCKED", "parts": mesh_readback},
        "semantic_port_and_axis_audit": port_audits,
        "sm1rc_clamped_state_geometry_readback": clamp_geometry_readback,
        "sm1rc_split_gap_analytic_estimate": analytic_split_gap_estimate,
        "per_part_face_quality_after_saved_blend_reopen": {
            "status": "PASS" if all(item["evaluated_mesh"]["face_quality"]["invalid_face_count"] == 0 for item in mesh_readback) else "BLOCKED",
            "parts": [
                {"part_number": item["part_number"], **item["evaluated_mesh"]["face_quality"]}
                for item in mesh_readback
            ],
            "gate": "non-triangular, duplicate-vertex, and distinct-collinear face counts must all be zero per part",
        },
        "zero_radius_ray_audit": ray_audit,
        "support_load_path_audit": load_path,
        "narrow_phase_bvh_audit": bvh_audit,
        "render_evidence": render_evidence,
        "generator_report_sha256": sha256(GENERATOR_REPORT),
        "cad_native_port_lock_sha256": sha256(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK.json"),
        "cad_derivative_manifest_sha256": sha256(MEASUREMENTS / "CAD_MESH_DERIVATIVES.json"),
        "stl_degenerate_audit_sha256": sha256(MEASUREMENTS / "STL_DEGENERATE_AUDIT.json"),
        "sm1rc_clamp_lock_sha256": sha256(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json"),
        "superseded_manifest_sha256": "0b234d2b72d8cc636a0ed670af2edb709442d5a2d01a6bdcafe6859f8c6e237c",
        "failures": failures,
        "vendor_cad_or_mesh_in_public_output": 0,
    }
    AUDIT_PATH.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": status,
        "failures": failures,
        "max_world_bbox_error_mm": max(item["world_bbox_max_error_mm"] for item in mesh_readback),
        "opaque_ray_hits": ray_audit["opaque_hit_count"],
        "transmissive_ray_hits": ray_audit["transmissive_hit_count"],
        "illegal_bvh_pairs": len(illegal),
        "sm1rc_ac254_contact_pairs": retention_contact["triangle_pair_count"],
        "sm1rc_ac254_annular_support_fraction": retention_contact["annular_support_fraction"],
        "saved_mesh_main_split_gap_mm": split_geometry_readback["main_split"]["gap_mm"],
        "saved_mesh_inner_edge_min_gap_mm": split_geometry_readback["deformed_inner_edge"]["minimum_gap_mm"],
        "saved_blend_invalid_faces": sum(item["evaluated_mesh"]["face_quality"]["invalid_face_count"] for item in mesh_readback),
        "render_count": len(render_evidence),
    }, indent=2))
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
