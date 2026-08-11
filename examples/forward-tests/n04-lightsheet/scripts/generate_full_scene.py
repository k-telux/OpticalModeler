"""Generate the deterministic full 32-node optical-table scene in Blender.

The scene uses linked instances of private, cleaned derivatives of every frozen
official STEP file.  Generic joining fasteners, load-link witnesses, labels,
presentation beams, and the literature-specific chamber are explicitly marked
non-Thorlabs/modeled.  This generator does not issue the propagation verdict;
the saved Blend must be reopened by ``audit_reopened_full.py``.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
BASE = ROOT / "work" / "full_32_node_propagation_v3"
MEASUREMENTS = BASE / "measurements"
DERIVATIVES = BASE / "vendor_derivatives_clean"
SCENE_DIR = BASE / "scene"
EVIDENCE = BASE / "evidence"
BLEND_PATH = SCENE_DIR / "FULL_32_NODE_PROPAGATION_v3.blend"
GENERATOR_REPORT = EVIDENCE / "GENERATOR_REPORT.json"
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
R3_META = ROOT / "outputs" / "phase2_representative_smoke_r3" / "metadata"

COMMON_ROTATION = Matrix(((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0)))
WORLD_UP = Vector((0.0, 0.0, 1.0))


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
    if emission:
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
        elif "Emission" in bsdf.inputs:
            bsdf.inputs["Emission"].default_value = emission[0]
            bsdf.inputs["Emission Strength"].default_value = emission[1]
    return value


def add_box(name, center, size, mat, collection, provenance, official=False):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"MESH__{name}"
    obj.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    obj.data.materials.append(mat)
    obj["provenance"] = provenance
    obj["official_thorlabs_claim"] = official
    obj["optical_clearance_class"] = "PHYSICAL_OPAQUE" if not official else "OFFICIAL_PHYSICAL"
    move_to_collection(obj, collection)
    return obj


def add_cylinder(name, start, end, radius, mat, collection, provenance, vertices=20):
    start, end = Vector(start), Vector(end)
    direction = end - start
    if direction.length <= 1e-9:
        direction = Vector((0.0, 0.0, 1e-6))
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=direction.length, location=(start + end) / 2.0)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"MESH__{name}"
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(direction.normalized())
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    bmesh.ops.triangulate(mesh, faces=list(mesh.faces))
    mesh.to_mesh(obj.data)
    mesh.free()
    obj.data.update()
    obj.data.materials.append(mat)
    obj["provenance"] = provenance
    obj["official_thorlabs_claim"] = False
    obj["optical_clearance_class"] = (
        "PRESENTATION_ONLY"
        if provenance == "PRESENTATION_BEAM_NOT_ZERO_RADIUS_CLEARANCE_GEOMETRY"
        else "PHYSICAL_OPAQUE"
    )
    move_to_collection(obj, collection)
    return obj


def add_sphere(name, center, radius, mat, collection, provenance):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2, radius=radius, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.data.name = f"MESH__{name}"
    obj.data.materials.append(mat)
    obj["provenance"] = provenance
    obj["official_thorlabs_claim"] = False
    obj["optical_clearance_class"] = "AUDIT_ONLY"
    move_to_collection(obj, collection)
    return obj


def add_text(name, body, location, mat, collection, size=0.025):
    data = bpy.data.curves.new(f"DATA__{name}", "FONT")
    data.body = body
    data.align_x = "CENTER"
    data.align_y = "CENTER"
    data.size = size
    data.extrude = 0.0004
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0.0, 0.0, 0.0)
    data.materials.append(mat)
    obj["provenance"] = "MODELED_NON_THORLABS_AUDIT_LABEL"
    obj["official_thorlabs_claim"] = False
    return obj


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def add_camera(name, location, target, lens, collection, ortho_scale=None):
    data = bpy.data.cameras.new(f"DATA__{name}")
    data.lens = lens
    data.sensor_width = 36.0
    if ortho_scale:
        data.type = "ORTHO"
        data.ortho_scale = ortho_scale
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def add_area_light(name, location, target, energy, size, color, collection):
    data = bpy.data.lights.new(f"DATA__{name}", "AREA")
    data.energy = energy
    data.shape = "DISK"
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = location
    look_at(obj, target)
    return obj


def bbox_corners(bounds):
    minimum, maximum = bounds["min_mm"], bounds["max_mm"]
    return [Vector((x, y, z)) for x in (minimum[0], maximum[0]) for y in (minimum[1], maximum[1]) for z in (minimum[2], maximum[2])]


def object_world_bbox(obj):
    points = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def expected_world_bbox(bounds, transform):
    points = [transform @ point for point in bbox_corners(bounds)]
    minimum = [min(point[index] for point in points) for index in range(3)]
    maximum = [max(point[index] for point in points) for index in range(3)]
    return {"min_m": minimum, "max_m": maximum, "size_m": [maximum[index] - minimum[index] for index in range(3)]}


def max_bbox_error_mm(first, second):
    return max(abs(first[key][axis] - second[key][axis]) * 1000.0 for key in ("min_m", "max_m", "size_m") for axis in range(3))


def raw_bbox_error_mm(obj, bounds):
    actual = object_world_bbox(obj)
    expected = {"min_m": bounds["min_mm"], "max_m": bounds["max_mm"], "size_m": bounds["size_mm"]}
    # Raw STL coordinates are numerically millimetres in Blender units here.
    return max(abs(actual[key][axis] - expected[key][axis]) for key in ("min_m", "max_m", "size_m") for axis in range(3))


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


def mesh_vertex_bbox(mesh):
    coordinates = [vertex.co.copy() for vertex in mesh.vertices]
    minimum = [min(value[index] for value in coordinates) for index in range(3)]
    maximum = [max(value[index] for value in coordinates) for index in range(3)]
    return {
        "min_mm": minimum,
        "max_mm": maximum,
        "size_mm": [maximum[index] - minimum[index] for index in range(3)],
    }


def max_native_bbox_error_mm(first, second):
    return max(abs(first[key][axis] - second[key][axis]) for key in ("min_mm", "max_mm", "size_mm") for axis in range(3))


def clean_blender_import_mesh(mesh):
    """Remove any invalid triangles produced/retained by Blender validation."""
    before_quality = mesh_face_quality(mesh)
    before_bbox = mesh_vertex_bbox(mesh)
    removed = []
    kept_faces = []
    for polygon in mesh.polygons:
        if len(polygon.vertices) != 3:
            removed.append((polygon.index, "non_triangular"))
            continue
        indices = tuple(polygon.vertices)
        a, b, c = (mesh.vertices[index].co for index in indices)
        edges = (b - a, c - b, a - c)
        edge_squared = [edge.length_squared for edge in edges]
        if min(edge_squared) == 0.0:
            removed.append((polygon.index, "duplicate_vertex"))
            continue
        double_area = (b - a).cross(c - a).length
        if double_area <= 1e-12 or double_area / max(edge_squared) <= 1e-12:
            removed.append((polygon.index, "distinct_collinear"))
            continue
        kept_faces.append(indices)
    if removed:
        vertices = [tuple(vertex.co) for vertex in mesh.vertices]
        mesh.clear_geometry()
        mesh.from_pydata(vertices, [], kept_faces)
        mesh.update(calc_edges=True)
    after_quality = mesh_face_quality(mesh)
    after_bbox = mesh_vertex_bbox(mesh)
    return {
        "before": before_quality,
        "after": after_quality,
        "removed_face_count": len(removed),
        "removed_by_class": {
            "non_triangular": sum(kind == "non_triangular" for _, kind in removed),
            "duplicate_vertex": sum(kind == "duplicate_vertex" for _, kind in removed),
            "distinct_collinear": sum(kind == "distinct_collinear" for _, kind in removed),
        },
        "bbox_before_mm": before_bbox,
        "bbox_after_mm": after_bbox,
        "bbox_error_after_cleanup_mm": max_native_bbox_error_mm(before_bbox, after_bbox),
    }


def native_center(bounds):
    return Vector(tuple((bounds["min_mm"][index] + bounds["max_mm"][index]) / 2.0 for index in range(3)))


def rotation_align(native_axis, desired_axis, native_up):
    axis_n = Vector(native_axis).normalized()
    up_n = Vector(native_up).normalized()
    up_n = (up_n - axis_n * up_n.dot(axis_n)).normalized()
    side_n = up_n.cross(axis_n).normalized()
    desired = Vector(desired_axis).normalized()
    up_w = WORLD_UP
    side_w = up_w.cross(desired).normalized()
    native_basis = Matrix((axis_n, side_n, up_n)).transposed()
    world_basis = Matrix((desired, side_w, up_w)).transposed()
    return world_basis @ native_basis.transposed()


def transform_centered(bounds, world_center, rotation):
    return Matrix.Translation(Vector(world_center)) @ rotation.to_4x4() @ Matrix.Diagonal((0.001, 0.001, 0.001, 1.0)) @ Matrix.Translation(-native_center(bounds))


def transform_from_native_origin(world_center, rotation, native_origin_mm):
    return Matrix.Translation(Vector(world_center)) @ rotation.to_4x4() @ Matrix.Diagonal((0.001, 0.001, 0.001, 1.0)) @ Matrix.Translation(-Vector(native_origin_mm))


def matrix_from_rows(rotation_rows, translation, scale=0.001):
    rotation = Matrix((
        (*rotation_rows[0], 0.0), (*rotation_rows[1], 0.0), (*rotation_rows[2], 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    return Matrix.Translation(Vector(translation)) @ rotation @ Matrix.Diagonal((scale, scale, scale, 1.0))


def matrix_rows(matrix):
    return [[float(matrix[row][column]) for column in range(4)] for row in range(4)]


def unit(vector):
    value = Vector(vector)
    return value.normalized() if value.length else Vector((1.0, 0.0, 0.0))


def apply_sm1rc_clamped_state(mesh, clamp_lock):
    neutral = clamp_lock["native_features_before_placement"]["sm1rc_bore_radius_mm"]
    target = clamp_lock["modeled_clamped_state"]["target_bore_radius_mm"]
    selected = []
    before = []
    for vertex in mesh.vertices:
        radius = math.hypot(vertex.co.x, vertex.co.y)
        if 0.40 <= vertex.co.z <= 9.75 and abs(radius - neutral) <= 0.16:
            selected.append(vertex)
            before.append(radius)
    if len(selected) < 40:
        raise RuntimeError(f"SM1RC/M clamped-state selection too small: {len(selected)}")
    for vertex, radius in zip(selected, before):
        scale = target / radius
        vertex.co.x *= scale
        vertex.co.y *= scale
    mesh.update()
    after = [math.hypot(vertex.co.x, vertex.co.y) for vertex in selected]
    return {
        "status": "PASS" if max(abs(value - target) for value in after) <= 1e-5 else "BLOCKED",
        "selected_vertex_count": len(selected),
        "neutral_radius_range_mm": [min(before), max(before)],
        "target_radius_mm": target,
        "after_radius_range_mm": [min(after), max(after)],
        "maximum_vertex_displacement_mm": max(abs(a - b) for a, b in zip(before, after)),
        "geometry_state": "MODELED_ELASTIC_INNER_BORE_DEFLECTION_OF_OFFICIAL_CAD_DERIVATIVE",
        "manufacturer_supplied_clamped_geometry": False,
        "claim_boundary": "GEOMETRIC_RETENTION_ONLY; FORCE_TORQUE_AND_LITERAL_PERFORMANCE_BLOCKED",
    }


MOUNT_AXIS = {
    "SM1RC/M": ([0, 0, 1], [0, 1, 0]), "SM2RC/M": ([0, 0, 1], [0, 1, 0]),
    "SM1TC": ([0, 0, 1], [0, 1, 0]), "SM1ZM": ([0, 0, 1], [0, 1, 0]),
    "KM2536": ([1, 0, 0], [0, 0, 1]), "LMR1/M": ([0, 0, 1], [0, 1, 0]),
    "CLR1/M": ([0, 0, 1], [0, 1, 0]), "GHS003/M": ([1, 0, 0], [0, 1, 0]),
    "QSM5/M": ([1, 0, 0], [0, 1, 0]), "M2M25S": ([0, 1, 0], [0, 0, 1]),
    "POLARIS-K1T2": ([1, 0, 0], [0, 0, 1]), "RSP1/M": ([0, 1, 0], [0, 0, 1]),
    "LPSA5/M": ([0, 0, 1], [0, 1, 0]), "SM1A9": ([1, 0, 0], [0, 0, 1]),
}

# Manufacturer-native optical centers that are explicit construction datums in
# these mount CAD families. Other parts use the measured optimal-bbox symmetry
# center recorded in the native-port/family lock.
MOUNT_ORIGIN_OVERRIDE_MM = {
    "SM2RC/M": [0.0, 0.0, 0.0],
    "POLARIS-K1T2": [0.0, 0.0, 0.0],
}

VERTICAL_CENTER = {
    "BA1/M": 0.005, "PH75/M": 0.0475, "TR75/M": 0.0679,
    "PH50/M": 0.0350, "TR50/M": 0.0475, "PLS-P373/M": 0.050,
    "POLARIS-CA1/M": 0.024, "ST1XY-D/M": 0.0565, "QSM5/M": 0.065,
    "LPS710E/M": 0.025,
}

LOAD_OFFSET = {
    "SOURCE_LAUNCH": 0.010, "DICHROIC_KM2536": 0.010, "SM1RC_LENS": 0.0152,
    "PINHOLE_STAGE": 0.010, "CYL_LENS_CLR1": 0.010, "RESONANT_SCANNER": 0.010,
    "GALVO_GHS": 0.010, "SM2RC_LENS": 0.027, "OBJECTIVE_SM2RC": 0.010,
    "EXPERIMENTAL_CHAMBER": 0.0, "PBS_CUBE": 0.012, "POLARIS_MIRROR": 0.010,
    "WAVEPLATE_RSP1": 0.010, "LPS_REMOTE_MIRROR": 0.0025, "FILTER_LMR1": 0.010,
    "CAMERA": 0.010,
}


def main() -> None:
    SCENE_DIR.mkdir(parents=True, exist_ok=True)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    build = load_json(BASE / "BUILD_PARAMS.json")
    topology = load_json(PHASE1 / "TOPOLOGY_MAP.json")
    manifest = load_json(PHASE1 / "CAD_MANIFEST.json")
    cad_audit = load_json(MEASUREMENTS / "FULL_CAD_MESH_AUDIT.json")
    port_lock = load_json(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK_FULL.json")
    family_lock = load_json(MEASUREMENTS / "FAMILY_LOCK.json")
    input_lock = load_json(MEASUREMENTS / "FULL_INPUT_LOCK.json")
    r3_ports = load_json(R3_META / "CAD_NATIVE_PORT_LOCK.json")
    r3_clamp = load_json(R3_META / "SM1RC_CLAMP_LOCK.json")
    if any(item["status"] != "PASS" for item in (cad_audit, port_lock, input_lock)):
        raise RuntimeError("pre-Blender full locks are not PASS")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    try:
        scene.render.engine = build["render"]["engine"]
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = build["render"]["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new("WORLD_FULL32_BRIGHT_AUDIT")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.055, 0.075, 0.105, 1.0)
    background.inputs["Strength"].default_value = 0.38
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 0.7

    collections = {
        "official": make_collection("OFFICIAL_THORLABS_CAD_PRIVATE"),
        "offscene": make_collection("OFFSCENE_OFFICIAL_ELECTRICAL_ENDPOINTS_PRIVATE"),
        "modeled": make_collection("MODELED_NON_THORLABS_MECHANICS"),
        "overlays": make_collection("AUDIT_OVERLAYS_AND_PRESENTATION_BEAMS"),
        "labels": make_collection("NODE_LABELS"),
        "lights": make_collection("LIGHTING"),
        "cameras": make_collection("CAMERAS"),
    }
    mats = {
        "table": material("MAT_TABLE_STEEL", (0.16, 0.22, 0.31, 1), 0.78, 0.24),
        "frame": material("MAT_FRAME", (0.055, 0.075, 0.10, 1), 0.70, 0.28),
        "black": material("MAT_BLACK_ANODIZED", (0.018, 0.026, 0.040, 1), 0.52, 0.24),
        "steel": material("MAT_STAINLESS", (0.42, 0.50, 0.58, 1), 0.90, 0.20),
        "optic": material("MAT_OPTICAL_GLASS", (0.02, 0.28, 0.38, 1), 0.02, 0.10, 0.48),
        "mirror": material("MAT_MIRROR", (0.62, 0.72, 0.82, 1), 0.96, 0.09),
        "source": material("MAT_SOURCE", (0.10, 0.16, 0.29, 1), 0.55, 0.22),
        "camera": material("MAT_CAMERA", (0.08, 0.10, 0.14, 1), 0.48, 0.25),
        "generic": material("MAT_MODELED_NON_THORLABS", (0.90, 0.20, 0.035, 1), 0.64, 0.22),
        "chamber": material("MAT_EXPERIMENTAL_CHAMBER", (0.24, 0.12, 0.34, 1), 0.35, 0.20, 0.20),
        "label": material("MAT_LABEL", (0.95, 0.98, 1.0, 1), 0.0, 0.25, emission=((0.8, 0.9, 1.0, 1), 2.0)),
        "port": material("MAT_PORT", (0.03, 0.90, 0.32, 1), emission=((0.02, 1.0, 0.20, 1), 4.0)),
    }
    beam_colors = {
        "SRC_488": ((0.02, 0.40, 1.0, 1), 7.0), "SRC_637": ((1.0, 0.025, 0.01, 1), 7.0),
        "ILL_COMMON": ((0.55, 0.15, 1.0, 1), 6.0), "FLUORESCENCE": ((0.02, 1.0, 0.25, 1), 7.0),
        "PBS_S": ((1.0, 0.30, 0.95, 1), 6.0), "PBS_P": ((0.2, 0.9, 1.0, 1), 6.0),
        "GREEN": ((0.01, 1.0, 0.08, 1), 7.0), "RED": ((1.0, 0.02, 0.01, 1), 7.0),
    }

    part_records = {record["requested_part_number"]: record for record in manifest["records"]}
    derivative_by_key = {item["derivative_key"]: item for item in cad_audit["parts"]}
    derivatives_by_part = {}
    for item in cad_audit["parts"]:
        derivatives_by_part.setdefault(item["part_number"], []).append(item)
    ports_by_node = {item["node_id"]: item for item in port_lock["nodes"]}
    nodes = {item["node_id"]: item for item in build["nodes"]}
    centers = {node_id: Vector(item["world_port_center_m"]) for node_id, item in nodes.items()}
    topology_nodes = {item["id"]: item for item in topology["nodes"]}

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

    def desired_axis(node_id, part):
        return surface_normal(node_id) if node_id in mirror_nodes or part in {"DMLP505R", "DMLP605R", "BB1-E02", "PF03-03-P01"} else through_direction(node_id)

    def native_up_for_axis(axis):
        vector = Vector(axis)
        return [0, 0, 1] if abs(vector.dot(Vector((0, 0, 1)))) < 0.8 else [0, 1, 0]

    def material_for_part(part):
        if part == "T1225C": return mats["table"]
        if part == "TF1225R7": return mats["frame"]
        if part.startswith("S4FC"): return mats["source"]
        if part in {"DMLP505R", "DMLP605R", "BB1-E02", "PF03-03-P01"}: return mats["mirror"]
        if part in {"CS165MU1/M"}: return mats["camera"]
        if part in {item["primary_part_number"] for item in build["nodes"]}: return mats["optic"]
        if part.startswith("TR"): return mats["steel"]
        return mats["black"]

    # Import every unique cleaned derivative at numeric millimetre scale.
    templates = {}
    import_records = []
    failures = []
    clamp_state = None
    for index, item in enumerate(cad_audit["parts"], start=1):
        key = item["derivative_key"]
        clean = item["post_clean_private_derivative"]
        path = BASE / clean["relative_private_path"]
        if sha256(path) != clean["sha256"] or path.stat().st_size != clean["bytes"]:
            raise RuntimeError(f"{key}: cleaned derivative hash/size drift")
        before = set(bpy.data.objects)
        bpy.ops.wm.stl_import(filepath=str(path), global_scale=1.0, use_scene_unit=False, forward_axis="Y", up_axis="Z", use_mesh_validate=True)
        created = [obj for obj in bpy.data.objects if obj not in before]
        if len(created) != 1:
            raise RuntimeError(f"{key}: expected one STL object, got {len(created)}")
        obj = created[0]
        pre_cleanup_polygon_count = len(obj.data.polygons)
        cleanup = clean_blender_import_mesh(obj.data)
        quality = cleanup["after"]
        raw_error = raw_bbox_error_mm(obj, clean["bbox_mm"])
        if quality["invalid_face_count"] or cleanup["bbox_error_after_cleanup_mm"] > 1e-6 or raw_error > item["mesh_bbox_tolerance_mm"]:
            failures.append({
                "stage": "UNIQUE_CAD_IMPORT", "derivative_key": key, "quality": quality,
                "blender_native_cleanup": cleanup, "raw_bbox_error_mm": raw_error,
            })
        mesh = obj.data
        mesh.name = f"MESH_OFFICIAL_PRIVATE__{key.replace('/', '_')}"
        mesh.materials.clear()
        mesh.materials.append(material_for_part(item["part_number"]))
        mesh.use_fake_user = True
        if item["part_number"] == "SM1RC/M":
            clamp_state = apply_sm1rc_clamped_state(mesh, r3_clamp)
            if clamp_state["status"] != "PASS" or mesh_face_quality(mesh)["invalid_face_count"]:
                failures.append({"stage": "SM1RC_CLAMP_STATE", "details": clamp_state, "quality": mesh_face_quality(mesh)})
        templates[key] = mesh
        bpy.data.objects.remove(obj, do_unlink=True)
        import_records.append({
            "derivative_key": key, "part_number": item["part_number"], "cad_file_index": item["cad_file_index"],
            "source_step_sha256": item["official_source"]["sha256"], "cleaned_derivative_sha256": clean["sha256"],
            "cleaned_derivative_bytes": clean["bytes"], "cleaned_bbox_mm": clean["bbox_mm"],
            "pre_clean_invalid_faces": item["removed"], "post_clean_invalid_faces": clean["duplicate_vertex_faces"] + clean["distinct_collinear_faces"],
            "blender_import_face_quality_before_native_cleanup": cleanup["before"],
            "blender_native_cleanup": cleanup,
            "blender_import_face_quality": quality, "raw_import_bbox_error_mm": raw_error,
            "blender_importer_removed_duplicate_triangle_count": max(0, clean["triangle_count"] - pre_cleanup_polygon_count),
            "raw_import_bbox_tolerance_mm": item["mesh_bbox_tolerance_mm"],
            "status": "PASS" if not quality["invalid_face_count"] and cleanup["bbox_error_after_cleanup_mm"] <= 1e-6 and raw_error <= item["mesh_bbox_tolerance_mm"] else "BLOCKED",
        })
        print(f"IMPORT {index:02d}/{len(cad_audit['parts']):02d} {key} {import_records[-1]['status']}", flush=True)

    official_instances = []
    instance_objects = {}
    node_objects = {node_id: [] for node_id in nodes}

    def create_instance(
        part, cad_item, name, node_id, role, transform, collection=None,
        geometry_state="MANUFACTURER_NATIVE_CAD_DERIVATIVE", assembly_subrole=None,
    ):
        key = cad_item["derivative_key"]
        obj = bpy.data.objects.new(name, templates[key])
        (collection or collections["official"]).objects.link(obj)
        obj.matrix_world = transform
        obj["part_number"] = part
        obj["derivative_key"] = key
        obj["node_id"] = node_id
        obj["role"] = role
        obj["assembly_subrole"] = assembly_subrole or role
        obj["provenance"] = "OFFICIAL_THORLABS_CAD_DERIVATIVE_PRIVATE"
        obj["optical_clearance_class"] = "OFFICIAL_PHYSICAL"
        obj["official_thorlabs_component_identity"] = True
        obj["official_thorlabs_claim"] = True
        obj["manufacturer_native_geometry_state"] = geometry_state == "MANUFACTURER_NATIVE_CAD_DERIVATIVE"
        obj["geometry_state"] = geometry_state
        obj["source_step_sha256"] = cad_item["official_source"]["sha256"]
        obj["cleaned_derivative_sha256"] = cad_item["post_clean_private_derivative"]["sha256"]
        obj["redistribution_decision"] = "EXCLUDE_FROM_PUBLIC_CANDIDATE"
        obj["native_mm_to_world_matrix"] = json.dumps(matrix_rows(transform), separators=(",", ":"))
        bpy.context.view_layer.update()
        expected = expected_world_bbox(cad_item["post_clean_private_derivative"]["bbox_mm"], transform)
        actual = object_world_bbox(obj)
        error = max_bbox_error_mm(actual, expected)
        status = "PASS" if error <= build["audit_thresholds"]["blender_bbox_error_mm"] else "BLOCKED"
        if status != "PASS":
            failures.append({"stage": "INSTANCE_WORLD_BBOX", "object": name, "error_mm": error})
        record = {
            "object_name": name, "node_id": node_id, "role": role,
            "assembly_subrole": assembly_subrole or role, "part_number": part,
            "derivative_key": key, "source_step_sha256": cad_item["official_source"]["sha256"],
            "native_mm_to_world_matrix": matrix_rows(transform), "actual_world_bbox": actual,
            "expected_world_bbox": expected, "world_bbox_error_mm": error,
            "mesh_vertices": len(obj.data.vertices), "mesh_polygons": len(obj.data.polygons),
            "geometry_state": geometry_state, "status": status,
        }
        official_instances.append(record)
        instance_objects[name] = obj
        if node_id in node_objects:
            node_objects[node_id].append({
                "object": obj, "part": part, "role": role,
                "assembly_subrole": assembly_subrole or role, "record": record,
            })
        return obj

    # Full table and matching rigid frame in the frozen world frame.
    table_item = derivatives_by_part["T1225C"][0]
    table_transform = Matrix.Translation(Vector((-1.25, -0.6, -0.21))) @ COMMON_ROTATION.to_4x4() @ Matrix.Diagonal((0.001, 0.001, 0.001, 1.0))
    table = create_instance("T1225C", table_item, "OFFICIAL_GLOBAL__T1225C", "GLOBAL", "optical table", table_transform)
    frame_item = derivatives_by_part["TF1225R7"][0]
    fb = frame_item["post_clean_private_derivative"]["bbox_mm"]
    frame_center_native = native_center(fb)
    frame_top_native_y = fb["max_mm"][1]
    # Center X/Y under the table and set frame top to table underside at -210 mm.
    base_frame_transform = COMMON_ROTATION.to_4x4() @ Matrix.Diagonal((0.001, 0.001, 0.001, 1.0))
    top_world_untranslated = (base_frame_transform @ Vector((frame_center_native.x, frame_top_native_y, frame_center_native.z))).to_3d()
    frame_translation = Vector((0.0, 0.0, -0.21)) - top_world_untranslated
    frame_transform = Matrix.Translation(frame_translation) @ base_frame_transform
    frame = create_instance("TF1225R7", frame_item, "OFFICIAL_GLOBAL__TF1225R7", "GLOBAL", "rigid table frame", frame_transform)

    # Accepted N04 r3 transforms are preserved as one translated assembly root.
    r3_part = {item["part_number"]: item for item in r3_ports["parts"]}
    n04_target = centers["N04"]
    n04_reference = Vector(r3_part["AC254-045-A-ML"]["world_transform"]["translation_m"])
    n04_delta = n04_target - n04_reference
    r3_lens_rows = r3_part["AC254-045-A-ML"]["world_transform"]["rotation_matrix"]
    r3_lens_rotation = Matrix(tuple(tuple(row) for row in r3_lens_rows))
    r3_axis_world = (r3_lens_rotation @ Vector(r3_part["AC254-045-A-ML"]["native_interfaces"]["optical_axis"]["axis"])).normalized()
    n04_axis_target = through_direction("N04")
    n04_root_yaw_rad = math.atan2(r3_axis_world.cross(n04_axis_target).z, r3_axis_world.dot(n04_axis_target))
    n04_root_rotation = Matrix.Rotation(n04_root_yaw_rad, 4, "Z")

    def r3_transform(part):
        locked = r3_part[part]["world_transform"]
        rows = locked.get("rotation_matrix", r3_ports["common_rotation_native_to_world"])
        original = matrix_from_rows(rows, locked["translation_m"], locked["uniform_scale"])
        return Matrix.Translation(n04_target) @ n04_root_rotation @ Matrix.Translation(-n04_reference) @ original

    # Create all node component and support instances.
    role_rank = {
        "table base": 10, "table clamp arm": 10, "XY translation stage": 12, "guided piezo stage and paired controller": 12,
        "post holder": 20, "post": 30, "low-profile pedestal": 32, "rectangular optic mount": 40,
        "collimator clamp": 40, "SM1 clamp": 40, "SM2 clamp": 40, "camera-support clamp": 40,
        "housing clamp": 40, "pinhole Z mount": 40, "filter mount": 40, "cylindrical lens mount": 40,
        "resonant scanner mount": 40, "galvo holder": 40, "mirror mount": 40, "rotation mount": 40,
        "M25-to-SM2 adapter": 45, "mirror adapter": 45, "C-mount-to-SM1 adapter": 45,
    }

    def placement_center(node_id, part, role, cad_index):
        center = centers[node_id].copy()
        is_primary = part == nodes[node_id]["primary_part_number"]
        if is_primary:
            center = centers[node_id].copy()
        elif part in VERTICAL_CENTER:
            center.z = VERTICAL_CENTER[part]
        elif part in MOUNT_AXIS or "mount" in role.lower() or "clamp" in role.lower() or "holder" in role.lower():
            center.z = 0.125
        if part.startswith("S4FC"):
            center = centers[node_id] + Vector((-0.36, 0.0, -0.070))
            center.z = 0.055
        elif part.startswith("P1-"):
            center = centers[node_id] + Vector((-0.24, 0.0, -0.045))
            center.z = 0.080
        elif part == "LPS710E/M" and cad_index == 2:
            center = Vector((0.0, -0.74, -0.38))
        # Reflective/dichroic mounts sit behind the optical surface. Offsets are
        # locked from the official CAD-drawing seat/recess depths plus the
        # untouched CAD body envelope; the primary optic remains at the frozen
        # node port and no vendor mesh is rescaled or relabeled.
        if part == "KM2536":
            center += surface_normal(node_id) * 0.018
        elif part == "GHS003/M":
            center += surface_normal(node_id) * 0.020
        elif part == "LPSA5/M":
            center += surface_normal(node_id) * 0.0035
        return center

    def part_rotation(node_id, part, role):
        desired = desired_axis(node_id, nodes[node_id]["primary_part_number"])
        if part.startswith("S4FC"):
            return rotation_align([0, 1, 0], [0, 1, 0], [0, 0, 1])
        if part.startswith("P1-"):
            return rotation_align([0, 0, 1], [1, 0, 0], [0, 1, 0])
        if part in {"BA1/M", "PH75/M", "TR75/M", "PH50/M", "TR50/M", "PLS-P373/M", "POLARIS-CA1/M", "ST1XY-D/M", "LPS710E/M"}:
            return COMMON_ROTATION
        if part in MOUNT_AXIS:
            axis, up = MOUNT_AXIS[part]
            return rotation_align(axis, desired, up)
        primary_rule = ports_by_node[node_id]
        if part == primary_rule["part_number"]:
            axis = primary_rule["native_axis"]
            return rotation_align(axis, desired, native_up_for_axis(axis))
        return COMMON_ROTATION

    for node_id in sorted(nodes):
        node = topology_nodes[node_id]
        assets = [(item, "catalog") for item in node["catalog_assets"]] + [(item, "support") for item in node["support_assets"]]
        occurrence = {}
        for asset, asset_class in assets:
            part = asset["part_number"]
            role = asset["role"]
            occurrence[part] = occurrence.get(part, 0) + 1
            if part not in derivatives_by_part:
                raise RuntimeError(f"{node_id}/{part}: no frozen derivative")
            for cad_item in derivatives_by_part[part]:
                cad_index = cad_item["cad_file_index"]
                if node_id == "N04" and part in r3_part and cad_index == 1:
                    transform = r3_transform(part)
                    state = "MODELED_ELASTIC_CLAMPED_STATE_FROM_ACCEPTED_R3" if part == "SM1RC/M" else "MANUFACTURER_NATIVE_CAD_DERIVATIVE"
                else:
                    center = placement_center(node_id, part, role, cad_index)
                    rotation = part_rotation(node_id, part, role)
                    if part in MOUNT_ORIGIN_OVERRIDE_MM:
                        transform = transform_from_native_origin(center, rotation, MOUNT_ORIGIN_OVERRIDE_MM[part])
                    else:
                        transform = transform_centered(cad_item["post_clean_private_derivative"]["bbox_mm"], center, rotation)
                    state = "MODELED_ELASTIC_CLAMPED_STATE_REAUDIT_REQUIRED" if part == "SM1RC/M" else "MANUFACTURER_NATIVE_CAD_DERIVATIVE"
                suffix = f"__CAD{cad_index}" if len(derivatives_by_part[part]) > 1 else ""
                name = f"OFFICIAL__{node_id}__{part.replace('/', '_')}__{occurrence[part]}{suffix}"
                assembly_subrole = role
                if part == "LPS710E/M":
                    assembly_subrole = "GUIDED_PIEZO_STAGE" if cad_index == 1 else "PAIRED_CONTROLLER"
                collection = collections["offscene"] if assembly_subrole == "PAIRED_CONTROLLER" else collections["official"]
                obj = create_instance(
                    part, cad_item, name, node_id, role, transform, collection, state,
                    assembly_subrole=assembly_subrole,
                )
                if collection == collections["offscene"]:
                    obj.hide_render = True

        add_sphere(f"PORT_MARKER__{node_id}", centers[node_id], 0.0022, mats["port"], collections["overlays"], "AUDIT_SEMANTIC_PORT_MARKER")
        add_text(f"LABEL__{node_id}", node_id, centers[node_id] + Vector((0.0, 0.0, 0.085)), mats["label"], collections["labels"], 0.026)

    # Literature-specific chamber/sample: modeled and explicitly not Thorlabs.
    chamber = add_box("MODELED_NON_THORLABS__N15__EXPERIMENTAL_CHAMBER", centers["N15"], (0.085, 0.070, 0.070), mats["chamber"], collections["modeled"], "MODELED_NON_THORLABS_LITERATURE_SPECIFIC_EXPERIMENTAL_CHAMBER", False)
    chamber["node_id"] = "N15"
    chamber["literature_role"] = topology_nodes["N15"]["literature_role"]
    chamber["catalog_component_claim"] = False
    chamber["optical_clearance_class"] = "PHYSICAL_OPAQUE"
    node_objects["N15"].append({"object": chamber, "part": "MODELED_EXPERIMENTAL_CHAMBER", "role": "sample/media chamber", "record": None})

    # Deterministic generic load links. Each link is anchored to actual saved
    # CAD mesh vertices nearest the adjacent component, then extended 2 mm
    # through each surface. This makes the narrow-phase contact an actual mesh
    # intersection rather than an AABB or assumed centerline claim. The links
    # remain explicit modeled non-Thorlabs fasteners/witnesses.
    modeled_load_links = []
    load_chains = []

    def nearest_world_vertex(obj, target):
        target = Vector(target)
        matrix = obj.matrix_world
        best = None
        best_distance = float("inf")
        for vertex in obj.data.vertices:
            point = matrix @ vertex.co
            distance = (point - target).length_squared
            if distance < best_distance:
                best_distance = distance
                best = point
        if best is None:
            raise RuntimeError(f"{obj.name}: no mesh vertices for load anchor")
        return best

    for node_id in sorted(nodes):
        family = nodes[node_id]["family_id"]
        entries = node_objects[node_id]
        primary_part = nodes[node_id]["primary_part_number"]
        primary = [item for item in entries if item["part"] == primary_part]
        support = [
            item for item in entries
            if item["part"] != primary_part and item.get("assembly_subrole") != "PAIRED_CONTROLLER"
        ]
        support.sort(key=lambda item: role_rank.get(item["role"], 35))
        ordered = support + primary
        if node_id == "N15":
            ordered = entries
        chain_objects = [table] + [item["object"] for item in ordered]
        chain_names = [obj.name for obj in chain_objects]
        for link_index, (previous, obj) in enumerate(zip(chain_objects, chain_objects[1:]), start=1):
            if primary and obj == primary[0]["object"]:
                # Retain the primary at a real peripheral mesh vertex. A center
                # anchor can geometrically contact the optic while blocking its
                # declared clear aperture, so the final retention witness is
                # deterministically routed to the lowest saved-mesh edge.
                primary_bbox = object_world_bbox(obj)
                anchor_hint = obj.matrix_world.translation.copy()
                anchor_hint.z = primary_bbox["min_m"][2]
                from_surface = nearest_world_vertex(previous, anchor_hint)
                to_surface = nearest_world_vertex(obj, anchor_hint)
            else:
                from_surface = nearest_world_vertex(previous, obj.matrix_world.translation)
                to_surface = nearest_world_vertex(obj, previous.matrix_world.translation)
            direction = to_surface - from_surface
            if direction.length <= 1e-6:
                direction = Vector((0.0, 0.0, 1.0))
            else:
                direction.normalize()
            start = from_surface - direction * 0.002
            target = to_surface + direction * 0.002
            link = add_cylinder(
                f"MODELED_LOAD_LINK__{node_id}__{link_index:02d}", start, target, 0.0018,
                mats["generic"], collections["modeled"], "MODELED_NON_THORLABS_GENERIC_FASTENER_OR_RETENTION_WITNESS", 20,
            )
            link["node_id"] = node_id
            link["from_object"] = previous.name
            link["to_object"] = obj.name
            link["from_surface_vertex_world_m"] = json.dumps(list(from_surface), separators=(",", ":"))
            link["to_surface_vertex_world_m"] = json.dumps(list(to_surface), separators=(",", ":"))
            link["surface_penetration_each_end_m"] = 0.002
            link["optical_clearance_class"] = "PHYSICAL_OPAQUE"
            modeled_load_links.append(link)
        load_chains.append({
            "node_id": node_id, "family_id": family, "ordered_load_path": chain_names,
            "modeled_link_count": sum(link.get("node_id") == node_id for link in modeled_load_links),
            "generic_fastener_identity": "MODELED_NON_THORLABS",
            "narrow_phase_contact_status": "REQUIRED_AFTER_SAVED_BLEND_REOPEN",
        })

    # Frame-to-table modeled floor load witnesses use the same actual-vertex
    # anchoring and controlled endpoint penetration.
    for index, (x, y) in enumerate(((-1.0, -0.45), (-1.0, 0.45), (1.0, -0.45), (1.0, 0.45)), start=1):
        target_hint = Vector((x, y, -0.21))
        from_surface = nearest_world_vertex(frame, target_hint)
        to_surface = nearest_world_vertex(table, from_surface)
        direction = unit(to_surface - from_surface)
        link = add_cylinder(
            f"MODELED_FRAME_TABLE_LOAD_LINK__{index}", from_surface - direction * 0.003, to_surface + direction * 0.003, 0.006,
            mats["generic"], collections["modeled"], "MODELED_NON_THORLABS_TABLE_FRAME_JOINING_WITNESS", 24,
        )
        link["from_object"] = frame.name
        link["to_object"] = table.name
        link["from_surface_vertex_world_m"] = json.dumps(list(from_surface), separators=(",", ":"))
        link["to_surface_vertex_world_m"] = json.dumps(list(to_surface), separators=(",", ":"))
        link["surface_penetration_each_end_m"] = 0.003
        modeled_load_links.append(link)

    # Presentation beams are not clearance geometry; zero-radius truth is
    # recomputed numerically from the frozen edge endpoints after reopen.
    for edge in topology["edges"]:
        branch = edge["branch_id"]
        color, strength = beam_colors.get(branch, ((0.8, 0.8, 1.0, 1), 5.0))
        mat_name = f"MAT_BEAM__{branch}"
        beam_mat = bpy.data.materials.get(mat_name) or material(mat_name, color, 0.0, 0.18, 0.0, (color, strength))
        obj = add_cylinder(
            f"PRESENTATION_BEAM__{edge['id']}__{branch}", centers[edge["from_node"]], centers[edge["to_node"]],
            0.00085, beam_mat, collections["overlays"], "PRESENTATION_BEAM_NOT_ZERO_RADIUS_CLEARANCE_GEOMETRY", 16,
        )
        obj["edge_id"] = edge["id"]
        obj["branch_id"] = branch
        obj["from_node"] = edge["from_node"]
        obj["to_node"] = edge["to_node"]
        obj["direction"] = edge["direction"]
        obj["optical_clearance_class"] = "PRESENTATION_ONLY"

    # Bright overall and family audit cameras.
    add_camera("CAM_FULL_PERSPECTIVE", (2.9, -2.7, 2.65), (0.0, 0.0, 0.05), 51.0, collections["cameras"])
    add_camera("CAM_FULL_TOP", (0.0, 0.0, 3.1), (0.0, 0.0, 0.0), 52.0, collections["cameras"], 2.85)
    add_camera("CAM_FAMILY_SOURCE", (-1.75, -0.25, 1.10), (-0.88, 0.28, 0.08), 58.0, collections["cameras"])
    add_camera("CAM_FAMILY_SCANNERS", (0.35, -0.55, 0.85), (0.58, 0.30, 0.10), 66.0, collections["cameras"])
    add_camera("CAM_FAMILY_BRANCH_RELAY", (-0.15, -1.05, 0.85), (0.05, -0.35, 0.10), 60.0, collections["cameras"])
    add_camera("CAM_FAMILY_DETECTOR", (1.85, -1.05, 0.85), (0.92, -0.24, 0.10), 60.0, collections["cameras"])
    add_camera("CAM_N04_REAUDIT", (-0.70, -0.25, 0.52), centers["N04"], 72.0, collections["cameras"])
    scene.camera = bpy.data.objects["CAM_FULL_PERSPECTIVE"]
    add_area_light("KEY_FULL", (0.2, -0.2, 3.4), (0.0, 0.0, 0.0), 2400, 3.0, (1.0, 0.96, 0.90), collections["lights"])
    add_area_light("FILL_LEFT", (-2.0, 0.7, 1.6), (-0.2, 0.0, 0.0), 1400, 2.0, (0.62, 0.78, 1.0), collections["lights"])
    add_area_light("FILL_RIGHT", (2.0, -0.8, 1.4), (0.4, -0.1, 0.0), 1500, 2.0, (1.0, 0.72, 0.55), collections["lights"])

    scene["scope"] = "FULL_32_NODE_PROPAGATION_GATE_V3"
    scene["phase1_immutable"] = True
    scene["n04_r3_immutable"] = True
    scene["node_count"] = 32
    scene["directed_edge_traversal_count"] = 44
    scene["family_count"] = 16
    scene["model_scope_status"] = "PARTIAL_SCOPED"
    scene["literal_paper_performance"] = "BLOCKED"
    scene["final_or_release_status"] = "BLOCKED"
    scene["final_or_release_reason"] = "AWAITING_SUPERVISOR_APPROVAL"
    scene["propagation_gate_status"] = "UNVERIFIED"
    scene["propagation_gate_reason"] = "PENDING_SAVED_BLEND_REOPEN"
    scene["substitution_count"] = 17
    scene["S4FC488_source_diagnostics"] = "PARTIAL_SCOPED"
    scene["S4FC637_source_diagnostics"] = "PARTIAL_SCOPED"
    scene["vendor_cad_public_redistribution"] = "BLOCKED"
    scene["modeled_generic_fasteners"] = "MODELED_NON_THORLABS"
    scene["experimental_chamber"] = "MODELED_NON_THORLABS"
    scene["full_input_lock_sha256"] = sha256(MEASUREMENTS / "FULL_INPUT_LOCK.json")
    scene["build_params_sha256"] = sha256(BASE / "BUILD_PARAMS.json")
    scene["cad_mesh_audit_sha256"] = sha256(MEASUREMENTS / "FULL_CAD_MESH_AUDIT.json")
    scene["native_port_lock_sha256"] = sha256(MEASUREMENTS / "CAD_NATIVE_PORT_LOCK_FULL.json")
    scene["family_lock_sha256"] = sha256(MEASUREMENTS / "FAMILY_LOCK.json")
    scene["accepted_n04_r3_manifest_sha256"] = input_lock["accepted_n04_r3_manifest_sha256"]

    # Every serialized mesh is in scope, including modeled fasteners, frame
    # links, chamber geometry, audit markers, and presentation beams.
    used_mesh_quality = {}
    for mesh in sorted((item for item in bpy.data.meshes if item.users > 0), key=lambda item: item.name):
        quality = mesh_face_quality(mesh)
        used_mesh_quality[mesh.name] = quality
        if quality["invalid_face_count"]:
            failures.append({
                "stage": "ALL_USED_MESH_TRIANGLE_GATE",
                "mesh_name": mesh.name,
                "quality": quality,
            })

    n24_stage = next(
        item for item in official_instances
        if item["node_id"] == "N24" and item["assembly_subrole"] == "GUIDED_PIEZO_STAGE"
    )
    n24_controller = next(
        item for item in official_instances
        if item["node_id"] == "N24" and item["assembly_subrole"] == "PAIRED_CONTROLLER"
    )
    n24_chain = next(item for item in load_chains if item["node_id"] == "N24")
    n24_stage_endpoint_links = [
        link.name for link in modeled_load_links
        if link.get("from_object") == n24_stage["object_name"] or link.get("to_object") == n24_stage["object_name"]
    ]
    if len(n24_stage_endpoint_links) < 2 or n24_stage["object_name"] not in n24_chain["ordered_load_path"]:
        failures.append({
            "stage": "N24_STAGE_LOAD_PATH_GENERATOR_GATE",
            "stage_object": n24_stage["object_name"],
            "endpoint_links": n24_stage_endpoint_links,
            "ordered_load_path": n24_chain["ordered_load_path"],
        })

    report = {
        "schema": "opticalmodeler.full32.generator-report.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "FULL_32_NODE_PROPAGATION_GATE_V3_PRE_REOPEN",
        "blender_version": bpy.app.version_string,
        "scene_units": "metre",
        "cad_numeric_import_unit": "millimetre before explicit 0.001 matrix scale",
        "unique_official_cad_import_count": len(import_records),
        "official_instance_count": len(official_instances),
        "node_count": len(nodes), "edge_count": len(topology["edges"]), "family_count": len(family_lock["families"]),
        "unique_cad_imports": import_records,
        "official_instances": official_instances,
        "n04_r3_root_propagation": {
            "status": "PASS", "reference_native_origin_world_m": list(n04_reference),
            "target_node_center_m": list(n04_target), "assembly_root_translation_delta_m": list(n04_delta),
            "accepted_axis_world_before_root_rotation": list(r3_axis_world),
            "target_axis_world": list(n04_axis_target),
            "assembly_root_yaw_deg": math.degrees(n04_root_yaw_rad),
            "accepted_r3_manifest_sha256": input_lock["accepted_n04_r3_manifest_sha256"],
            "inherited_pass_for_other_families": False,
        },
        "sm1rc_modeled_clamped_state": clamp_state,
        "all_used_mesh_generator_gate": {
            "used_mesh_datablock_count": len(used_mesh_quality),
            "status": "PASS" if all(item["invalid_face_count"] == 0 for item in used_mesh_quality.values()) else "BLOCKED",
            "by_mesh": used_mesh_quality,
        },
        "n24_stage_controller_split": {
            "stage_object": n24_stage["object_name"],
            "stage_subrole": n24_stage["assembly_subrole"],
            "controller_object": n24_controller["object_name"],
            "controller_subrole": n24_controller["assembly_subrole"],
            "controller_offscene": True,
            "stage_in_ordered_load_path": n24_stage["object_name"] in n24_chain["ordered_load_path"],
            "stage_endpoint_links": n24_stage_endpoint_links,
            "status": "PASS" if len(n24_stage_endpoint_links) >= 2 else "BLOCKED",
        },
        "load_chains": load_chains,
        "modeled_load_link_count": len(modeled_load_links),
        "modeled_non_thorlabs_object_count": len(collections["modeled"].objects),
        "presentation_beam_count": len(topology["edges"]),
        "failures": failures,
        "status_boundaries": build["status_boundaries"],
    }
    GENERATOR_REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError(f"generator gates failed: {failures[:5]}")

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_PATH), check_existing=False)
    print(json.dumps({
        "status": "PASS", "blend": str(BLEND_PATH.relative_to(ROOT)).replace("\\", "/"),
        "blender_version": bpy.app.version_string, "unique_cad_imports": len(import_records),
        "official_instances": len(official_instances), "modeled_load_links": len(modeled_load_links),
        "blend_bytes": BLEND_PATH.stat().st_size,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
