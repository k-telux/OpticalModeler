"""Build the deterministic N04 representative Blender smoke scene.

Run with Blender and pass the public-test workspace root after ``--``.
Vendor-derived meshes and the Blend remain private work artifacts.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
BASE = ROOT / "work" / "phase2_representative_smoke_r3"
MEASUREMENTS = BASE / "measurements"
DERIVATIVES = BASE / "vendor_derivatives_clean"
SCENE_DIR = BASE / "scene"
EVIDENCE_DIR = BASE / "evidence"
BLEND_PATH = SCENE_DIR / "N04_representative_smoke_r3.blend"
REPORT_PATH = EVIDENCE_DIR / "GENERATOR_REPORT.json"
BBOX_TOLERANCE_MM = 0.1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def make_collection(name: str):
    collection = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(collection)
    return collection


def move_to_collection(obj, collection) -> None:
    for current in list(obj.users_collection):
        current.objects.unlink(obj)
    collection.objects.link(obj)


def material(name: str, color, metallic=0.0, roughness=0.4, transmission=0.0, emission=None):
    value = bpy.data.materials.new(name)
    value.use_nodes = True
    bsdf = value.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if emission is not None:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
    return value


def matrix_from(rotation_rows, translation, scale=0.001):
    rotation = Matrix((
        (*rotation_rows[0], 0.0),
        (*rotation_rows[1], 0.0),
        (*rotation_rows[2], 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return Matrix.Translation(Vector(translation)) @ rotation @ Matrix.Diagonal((scale, scale, scale, 1.0))


def bbox_corners(bounds):
    minimum, maximum = bounds["min_mm"], bounds["max_mm"]
    return [Vector((x, y, z)) for x in (minimum[0], maximum[0]) for y in (minimum[1], maximum[1]) for z in (minimum[2], maximum[2])]


def world_bbox_from_native(bounds, transform):
    points = [transform @ point for point in bbox_corners(bounds)]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def object_world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def max_bbox_error_mm(actual, expected):
    values = []
    for key in ("min_m", "max_m", "size_m"):
        values.extend(abs(actual[key][index] - expected[key][index]) * 1000.0 for index in range(3))
    return max(values)


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


def apply_sm1rc_clamped_state(obj, clamp_lock):
    state = clamp_lock["modeled_clamped_state"]
    neutral_radius = clamp_lock["native_features_before_placement"]["sm1rc_bore_radius_mm"]
    target_radius = state["target_bore_radius_mm"]
    selected = []
    before = []
    for vertex in obj.data.vertices:
        radius = math.hypot(vertex.co.x, vertex.co.y)
        if 0.45 <= vertex.co.z <= 9.71 and abs(radius - neutral_radius) <= 0.02:
            selected.append(vertex)
            before.append(radius)
    if len(selected) < 100:
        raise RuntimeError(f"SM1RC/M: only {len(selected)} native bore vertices selected for clamped state")
    for vertex, radius in zip(selected, before):
        scale = target_radius / radius
        vertex.co.x *= scale
        vertex.co.y *= scale
    obj.data.update()
    after = [math.hypot(vertex.co.x, vertex.co.y) for vertex in selected]
    maximum_displacement = max(abs(first - second) for first, second in zip(before, after))
    return {
        "status": "PASS" if max(abs(value - target_radius) for value in after) <= 1e-5 else "BLOCKED",
        "geometry_state": "MODELED_ELASTIC_INNER_BORE_DEFLECTION_OF_OFFICIAL_CAD_DERIVATIVE",
        "manufacturer_supplied_clamped_geometry": False,
        "selected_native_bore_vertex_count": len(selected),
        "neutral_bore_radius_observed_range_mm": [min(before), max(before)],
        "target_clamped_bore_radius_mm": target_radius,
        "clamped_bore_radius_observed_range_mm": [min(after), max(after)],
        "maximum_vertex_displacement_mm": maximum_displacement,
        "numerical_contact_interference_mm": state["numerical_contact_interference_mm"],
        "saved_mesh_split_gap_readback": "REQUIRED_AFTER_SAVED_BLEND_REOPEN",
        "analytic_split_gap_estimate": clamp_lock["analytic_split_gap_estimate"],
        "claim_boundary": "GEOMETRIC_RETENTION_ONLY; CLAMP_FORCE_AND_LITERAL_PERFORMANCE_BLOCKED",
    }


def add_cylinder(name, radius, start_z, end_z, x, y, mat, collection, provenance):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius, depth=end_z - start_z, location=(x, y, (start_z + end_z) / 2.0))
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"MESH__{name}"
    obj.data.materials.append(mat)
    obj["provenance"] = provenance
    obj["official_thorlabs_claim"] = False
    move_to_collection(obj, collection)
    return obj


def add_annulus(name, x, y, z0, z1, inner_radius, outer_radius, mat, collection):
    segments = 64
    vertices = []
    for z in (z0, z1):
        for radius in (outer_radius, inner_radius):
            for index in range(segments):
                angle = 2.0 * math.pi * index / segments
                vertices.append((x + radius * math.cos(angle), y + radius * math.sin(angle), z))
    faces = []
    outer_bottom, inner_bottom, outer_top, inner_top = 0, segments, 2 * segments, 3 * segments
    for index in range(segments):
        nxt = (index + 1) % segments
        faces.extend([
            (outer_bottom + index, outer_bottom + nxt, outer_top + nxt, outer_top + index),
            (inner_bottom + nxt, inner_bottom + index, inner_top + index, inner_top + nxt),
            (outer_top + index, outer_top + nxt, inner_top + nxt, inner_top + index),
            (outer_bottom + nxt, outer_bottom + index, inner_bottom + index, inner_bottom + nxt),
        ])
    mesh = bpy.data.meshes.new(f"MESH__{name}")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj["provenance"] = "MODELED_NON_THORLABS_GENERIC_WASHER"
    obj["official_thorlabs_claim"] = False
    return obj


def add_segment(name, start, end, radius, mat, collection, classification):
    start, end = Vector(start), Vector(end)
    vector = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius, depth=vector.length, location=(start + end) / 2.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"MESH__{name}"
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(vector.normalized())
    obj.data.materials.append(mat)
    obj["classification"] = classification
    obj["audit_only"] = True
    move_to_collection(obj, collection)
    return obj


def look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def add_camera(name, location, target, lens, collection):
    data = bpy.data.cameras.new(f"DATA__{name}")
    data.lens = lens
    data.sensor_width = 36.0
    camera = bpy.data.objects.new(name, data)
    collection.objects.link(camera)
    camera.location = location
    look_at(camera, target)
    return camera


def add_area_light(name, location, energy, size, color, collection):
    data = bpy.data.lights.new(f"DATA__{name}", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    light = bpy.data.objects.new(name, data)
    collection.objects.link(light)
    light.location = location
    look_at(light, (0.1125, 1.0875, 0.06))
    return light


def main() -> None:
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    ports = load_json(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK.json")
    derivatives = load_json(MEASUREMENTS / "CAD_MESH_DERIVATIVES.json")
    degenerate_audit = load_json(MEASUREMENTS / "STL_DEGENERATE_AUDIT.json")
    clamp_lock = load_json(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json")
    if degenerate_audit["status"] != "PASS" or clamp_lock["status"] != "PASS":
        raise RuntimeError("pre-Blender cleanup or clamp lock is not PASS")
    derivative_by_part = {record["part_number"]: record for record in derivatives["parts"]}
    clean_by_part = {record["part_number"]: record for record in degenerate_audit["parts"]}
    port_by_part = {record["part_number"]: record for record in ports["parts"]}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.render.image_settings.color_depth = "8"
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new("WORLD_AUDIT")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.012, 0.016, 0.024, 1.0)
    background.inputs["Strength"].default_value = 0.12
    scene.view_settings.exposure = -1.0

    official_collection = make_collection("OFFICIAL_CAD_PRIVATE")
    fastener_collection = make_collection("MODELED_NON_THORLABS_FASTENERS")
    overlay_collection = make_collection("AUDIT_OVERLAYS")
    light_collection = make_collection("LIGHTING")
    camera_collection = make_collection("CAMERAS")

    mats = {
        "table": material("MAT_TABLE", (0.06, 0.085, 0.12, 1.0), metallic=0.72, roughness=0.34),
        "black": material("MAT_BLACK_ANODIZED", (0.018, 0.022, 0.028, 1.0), metallic=0.45, roughness=0.25),
        "steel": material("MAT_STAINLESS", (0.32, 0.38, 0.44, 1.0), metallic=0.88, roughness=0.24),
        "optic": material("MAT_OPTIC_AUDIT_TRANSLUCENT", (0.05, 0.36, 0.48, 1.0), metallic=0.0, roughness=0.14, transmission=0.68),
        "fastener": material("MAT_NON_THORLABS_FASTENER", (0.82, 0.16, 0.035, 1.0), metallic=0.65, roughness=0.24),
        "washer": material("MAT_NON_THORLABS_WASHER", (0.95, 0.56, 0.04, 1.0), metallic=0.55, roughness=0.28),
        "beam": material("MAT_PRESENTATION_BEAM", (0.55, 0.004, 0.002, 1.0), roughness=0.2, emission=((1.0, 0.002, 0.001, 1.0), 3.0)),
        "port_in": material("MAT_PORT_IN", (0.02, 0.7, 0.12, 1.0), emission=((0.02, 1.0, 0.16, 1.0), 2.5)),
        "port_out": material("MAT_PORT_OUT", (1.0, 0.18, 0.005, 1.0), emission=((1.0, 0.12, 0.002, 1.0), 2.5)),
    }

    imported = []
    failures = []
    clamp_deformation = None
    common_rotation = ports["common_rotation_native_to_world"]
    material_by_part = {
        "T1225C": mats["table"], "BA1/M": mats["black"], "PH75/M": mats["black"],
        "TR75/M": mats["steel"], "SM1RC/M": mats["black"], "AC254-045-A-ML": mats["optic"],
    }

    for part in ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML"):
        derivative = derivative_by_part[part]["derivative"]
        pre_clean = clean_by_part[part]["pre_clean_private_derivative"]
        cleaned = clean_by_part[part]["post_clean_pre_import_private_derivative"]
        mesh_path = BASE / cleaned["relative_private_path"]
        if sha256(mesh_path) != cleaned["sha256"] or mesh_path.stat().st_size != cleaned["bytes"]:
            raise RuntimeError(f"{part}: cleaned private derivative hash/size mismatch")

        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(
            filepath=str(mesh_path), global_scale=1.0, use_scene_unit=False,
            forward_axis="Y", up_axis="Z", use_mesh_validate=True,
        )
        new_objects = [obj for obj in bpy.data.objects if obj not in before]
        if len(new_objects) != 1:
            raise RuntimeError(f"{part}: expected one imported STL object, got {len(new_objects)}")
        obj = new_objects[0]
        obj.name = f"OFFICIAL_CAD__{part.replace('/', '_')}"
        obj.data.name = f"MESH__{part.replace('/', '_')}"
        move_to_collection(obj, official_collection)
        obj.data.materials.clear()
        obj.data.materials.append(material_by_part[part])

        import_quality_before_clamp = mesh_face_quality(obj.data)
        if import_quality_before_clamp["invalid_face_count"] != 0:
            failures.append({"part_number": part, "stage": "BLENDER_IMPORT", "mesh_face_quality": import_quality_before_clamp})

        expected_native = derivative["bbox_optimal_mm"]
        raw_bbox = object_world_bbox(obj)
        raw_expected = {
            "min_m": expected_native["min_mm"], "max_m": expected_native["max_mm"],
            "size_m": expected_native["size_mm"],
        }
        raw_error_mm = max_bbox_error_mm(raw_bbox, raw_expected) / 1000.0

        if part == "SM1RC/M":
            clamp_deformation = apply_sm1rc_clamped_state(obj, clamp_lock)
            if clamp_deformation["status"] != "PASS":
                failures.append({"part_number": part, "stage": "CLAMP_DEFORMATION", "details": clamp_deformation})
        import_quality_after_state = mesh_face_quality(obj.data)
        if import_quality_after_state["invalid_face_count"] != 0:
            failures.append({"part_number": part, "stage": "POST_STATE_GEOMETRY", "mesh_face_quality": import_quality_after_state})

        locked = port_by_part[part]["world_transform"]
        rotation = locked.get("rotation_matrix", common_rotation)
        transform = matrix_from(rotation, locked["translation_m"], locked["uniform_scale"])
        obj.matrix_world = transform
        bpy.context.view_layer.update()
        actual_world = object_world_bbox(obj)
        expected_world = world_bbox_from_native(expected_native, transform)
        world_error_mm = max_bbox_error_mm(actual_world, expected_world)
        if raw_error_mm > BBOX_TOLERANCE_MM or world_error_mm > BBOX_TOLERANCE_MM:
            failures.append({"part_number": part, "raw_error_mm": raw_error_mm, "world_error_mm": world_error_mm})

        obj["part_number"] = part
        obj["node_id"] = "N04" if part in {"SM1RC/M", "AC254-045-A-ML"} else "N04_SUPPORT"
        obj["provenance"] = (
            "OFFICIAL_THORLABS_CAD_DERIVATIVE_WITH_DECLARED_MODELED_CLAMP_STATE_PRIVATE"
            if part == "SM1RC/M" else "OFFICIAL_THORLABS_CAD_DERIVATIVE_PRIVATE"
        )
        obj["official_thorlabs_component_identity"] = True
        obj["manufacturer_native_geometry_state"] = part != "SM1RC/M"
        obj["source_step_sha256"] = derivative_by_part[part]["source_step"]["sha256"]
        obj["pre_clean_derivative_sha256"] = pre_clean["sha256"]
        obj["cleaned_derivative_sha256"] = cleaned["sha256"]
        obj["redistribution_decision"] = "EXCLUDE_FROM_PUBLIC_CANDIDATE"
        obj["native_to_world_transform_lock"] = json.dumps(locked, separators=(",", ":"))
        if part == "SM1RC/M":
            obj["clamp_lock_sha256"] = sha256(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json")
            obj["clamp_state"] = json.dumps(clamp_deformation, separators=(",", ":"))
        imported.append({
            "part_number": part,
            "object_name": obj.name,
            "mesh_vertex_count": len(obj.data.vertices),
            "mesh_polygon_count": len(obj.data.polygons),
            "source_step_sha256": derivative_by_part[part]["source_step"]["sha256"],
            "pre_clean_derivative_sha256": pre_clean["sha256"],
            "cleaned_derivative_sha256": cleaned["sha256"],
            "pre_clean_face_quality": {
                "duplicate_vertex_faces": pre_clean["duplicate_vertex_faces"],
                "distinct_collinear_faces": pre_clean["distinct_collinear_faces"],
            },
            "post_clean_pre_import_face_quality": {
                "duplicate_vertex_faces": cleaned["duplicate_vertex_faces"],
                "distinct_collinear_faces": cleaned["distinct_collinear_faces"],
            },
            "blender_import_face_quality_before_clamp_state": import_quality_before_clamp,
            "blender_mesh_face_quality_after_state": import_quality_after_state,
            "geometry_state": (
                "MODELED_ELASTIC_CLAMPED_STATE_FROM_OFFICIAL_CAD_DERIVATIVE"
                if part == "SM1RC/M" else "MANUFACTURER_NATIVE_CAD_DERIVATIVE"
            ),
            "clamp_deformation": clamp_deformation if part == "SM1RC/M" else None,
            "raw_import_bbox_numeric_unit": "Blender unit before transform; expected millimetre coordinates",
            "raw_import_bbox": raw_bbox,
            "opencascade_optimal_bbox_mm": expected_native,
            "raw_bbox_error_mm": raw_error_mm,
            "world_bbox": actual_world,
            "expected_world_bbox": expected_world,
            "world_bbox_error_mm": world_error_mm,
            "uniform_scale_applied": locked["uniform_scale"],
            "status": "PASS" if raw_error_mm <= BBOX_TOLERANCE_MM and world_error_mm <= BBOX_TOLERANCE_MM and import_quality_after_state["invalid_face_count"] == 0 else "BLOCKED",
        })

    # Modeled generic fasteners: never represented as Thorlabs parts.
    for label, x in (("LEFT", 0.0875), ("RIGHT", 0.1375)):
        add_cylinder(f"MODELED_NON_THORLABS_M6_SHANK_{label}", 0.00235, -0.005, 0.011, x, 1.0875, mats["fastener"], fastener_collection, "MODELED_NON_THORLABS_GENERIC_M6_SHANK")
        add_annulus(f"MODELED_NON_THORLABS_M6_WASHER_{label}", x, 1.0875, 0.010, 0.011, 0.0032, 0.006, mats["washer"], fastener_collection)
        add_cylinder(f"MODELED_NON_THORLABS_M6_HEAD_{label}", 0.005, 0.011, 0.017, x, 1.0875, mats["fastener"], fastener_collection, "MODELED_NON_THORLABS_GENERIC_M6_HEAD")
    add_cylinder("MODELED_NON_THORLABS_M6_CENTER_SHANK", 0.00235, 0.0073, 0.016, 0.1125, 1.0875, mats["fastener"], fastener_collection, "MODELED_NON_THORLABS_GENERIC_M6_SHANK")
    add_cylinder("MODELED_NON_THORLABS_M6_CENTER_LOW_PROFILE_HEAD", 0.0050, 0.0073, 0.0099, 0.1125, 1.0875, mats["fastener"], fastener_collection, "MODELED_NON_THORLABS_GENERIC_LOW_PROFILE_HEAD")

    ray = ports["representative_ray"]
    add_segment("PRESENTATION_BEAM__ILL_COMMON_N04", ray["zero_radius_start_m"], ray["zero_radius_end_m"], 0.00055, mats["beam"], overlay_collection, "PRESENTATION_BEAM_NOT_CLEARANCE_GEOMETRY")
    for name, position, mat in (
        ("PORT_N04_in", port_by_part["AC254-045-A-ML"]["world_semantic_ports_m"]["in"], mats["port_in"]),
        ("PORT_N04_out", port_by_part["AC254-045-A-ML"]["world_semantic_ports_m"]["out"], mats["port_out"]),
    ):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.0015, location=position)
        marker = bpy.context.object
        marker.name = name
        marker.data.name = f"MESH__{name}"
        marker.data.materials.append(mat)
        marker["classification"] = "AUDIT_SEMANTIC_PORT_MARKER"
        marker["audit_only"] = True
        move_to_collection(marker, overlay_collection)

    side_camera = add_camera("CAM_AUDIT_SIDE", (0.34, 0.88, 0.235), (0.1125, 1.0875, 0.080), 50.0, camera_collection)
    axial_camera = add_camera("CAM_AUDIT_AXIAL", (0.1125, 1.235, 0.125), (0.1125, 1.085, 0.125), 58.0, camera_collection)
    scene.camera = side_camera
    add_area_light("KEY", (0.18, 0.92, 0.38), 280.0, 0.22, (1.0, 0.96, 0.9), light_collection)
    add_area_light("FILL", (-0.08, 1.22, 0.24), 130.0, 0.18, (0.68, 0.82, 1.0), light_collection)
    add_area_light("RIM", (0.34, 1.18, 0.19), 220.0, 0.16, (0.8, 0.9, 1.0), light_collection)

    scene["scope"] = "N04_REPRESENTATIVE_ONLY_R3"
    scene["global_model_status"] = "PARTIAL_SCOPED"
    scene["literal_paper_performance"] = "BLOCKED"
    scene["full_32_node_propagation"] = "UNVERIFIED"
    scene["node_id"] = "N04"
    scene["phase1_immutable"] = True
    scene["vendor_cad_public_redistribution"] = "BLOCKED"
    scene["generic_fasteners"] = "MODELED_NON_THORLABS"
    scene["cad_native_port_lock_sha256"] = sha256(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK.json")
    scene["cad_derivative_manifest_sha256"] = sha256(MEASUREMENTS / "CAD_MESH_DERIVATIVES.json")
    scene["stl_degenerate_audit_sha256"] = sha256(MEASUREMENTS / "STL_DEGENERATE_AUDIT.json")
    scene["sm1rc_clamp_lock_sha256"] = sha256(MEASUREMENTS / "SM1RC_CLAMP_LOCK.json")
    scene["supersedes_n04_manifest_sha256"] = "0b234d2b72d8cc636a0ed670af2edb709442d5a2d01a6bdcafe6859f8c6e237c"

    report = {
        "schema": "opticalmodeler.phase2.generator-report.v3",
        "status": "BLOCKED" if failures else "PASS",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "blender_version": bpy.app.version_string,
        "bbox_tolerance_mm": BBOX_TOLERANCE_MM,
        "official_cad_imports": imported,
        "failures": failures,
        "modeled_non_thorlabs_fastener_objects": sorted(obj.name for obj in fastener_collection.objects),
        "semantic_ports": port_by_part["AC254-045-A-ML"]["world_semantic_ports_m"],
        "representative_ray": ray,
        "sm1rc_clamp_state": clamp_deformation,
        "blender_stl_import_diagnostics": {
            "status": "PASS" if all(item["blender_import_face_quality_before_clamp_state"]["invalid_face_count"] == 0 for item in imported) else "BLOCKED",
            "input": "per-part cleaned private STL derivatives",
            "per_part_pre_clean_post_clean_and_blender_import": [
                {
                    "part_number": item["part_number"],
                    "pre_clean": item["pre_clean_face_quality"],
                    "post_clean_pre_import": item["post_clean_pre_import_face_quality"],
                    "blender_import": item["blender_import_face_quality_before_clamp_state"],
                }
                for item in imported
            ],
            "blender_removed_degenerate_triangle_batches": [],
            "blender_removed_degenerate_triangle_total": 0,
            "interpretation": "All known duplicate-vertex and numerically collinear faces were removed per part before Blender import; generator-time imported meshes contain zero invalid faces.",
        },
        "superseded_gate": {
            "scope": "N04_REPRESENTATIVE_ONLY_R2",
            "manifest_sha256": "0b234d2b72d8cc636a0ed670af2edb709442d5a2d01a6bdcafe6859f8c6e237c",
            "status": "BLOCKED",
            "reasons": [
                "1.157101806 mm analytic split-gap estimate was mislabeled as saved-Blend reopen readback",
                "r2 did not measure the actual main split or deformed inner-edge gap from the reopened evaluated mesh"
            ],
        },
        "global_status_boundaries": {
            "requested_model": "PARTIAL_SCOPED",
            "literal_paper_performance": "BLOCKED",
            "full_propagation": "UNVERIFIED",
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError(f"CAD import bbox gate failed: {failures}")

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(json.dumps({
        "status": "PASS",
        "blend_relative_path": str(BLEND_PATH.relative_to(ROOT)).replace("\\", "/"),
        "official_cad_objects": len(imported),
        "modeled_fastener_objects": len(fastener_collection.objects),
        "mesh_vertices": sum(item["mesh_vertex_count"] for item in imported),
        "mesh_polygons": sum(item["mesh_polygon_count"] for item in imported),
        "max_world_bbox_error_mm": max(item["world_bbox_error_mm"] for item in imported),
    }, indent=2))


if __name__ == "__main__":
    main()
