#!/usr/bin/env python3
"""Blender-side raw import, explicit cleanup, and saved-file reopen audits."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Vector


AREA_EPSILON_M2 = 1.0e-18
COLLINEAR_SINE_EPSILON = 1.0e-12
MERGE_DISTANCE_M = 1.0e-9
CHUNK_TRIANGLES = 250_000


def argv() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("raw", "clean", "reopen"), required=True)
    parser.add_argument("--sku", required=True)
    parser.add_argument("--obj", type=Path)
    parser.add_argument("--blend", type=Path)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--render", type=Path)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])


def sha256_text(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(set(values))).encode("utf-8")).hexdigest()


def source_obj_groups(path: Path) -> dict[str, object]:
    groups: list[str] = []
    material_libraries: list[str] = []
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for line in handle:
            if line.startswith("g "):
                groups.append(line[2:].strip())
            elif line.startswith("mtllib "):
                material_libraries.append(line[7:].strip())
    unique = sorted(set(groups))
    return {
        "group_statement_count": len(groups),
        "unique_group_count": len(unique),
        "group_name_set_sha256": sha256_text(unique),
        "group_name_max_length": max((len(name) for name in unique), default=0),
        "group_names": unique,
        "group_samples": unique[:16],
        "material_library_statement_count": len(material_libraries),
    }


def local_arrays(mesh: bpy.types.Mesh) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    coordinates = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", coordinates)
    coordinates.shape = (-1, 3)
    edge_vertices = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", edge_vertices)
    edge_vertices.shape = (-1, 2)
    loop_edges = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("edge_index", loop_edges)
    loop_vertices = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get("vertex_index", loop_vertices)
    polygon_starts = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_start", polygon_starts)
    polygon_totals = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", polygon_totals)
    return coordinates, edge_vertices, loop_edges, loop_vertices, np.column_stack((polygon_starts, polygon_totals))


def triangle_metrics(mesh: bpy.types.Mesh, coordinates: np.ndarray) -> dict[str, int]:
    mesh.calc_loop_triangles()
    triangle_count = len(mesh.loop_triangles)
    triangle_vertices = np.empty(triangle_count * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", triangle_vertices)
    triangle_vertices.shape = (-1, 3)
    exact_zero = 0
    collinear = 0
    tiny_area = 0
    for start in range(0, triangle_count, CHUNK_TRIANGLES):
        indices = triangle_vertices[start : start + CHUNK_TRIANGLES]
        point0 = coordinates[indices[:, 0]]
        point1 = coordinates[indices[:, 1]]
        point2 = coordinates[indices[:, 2]]
        e01 = point1 - point0
        e02 = point2 - point0
        e12 = point2 - point1
        cross = np.cross(e01, e02)
        cross_sq = np.einsum("ij,ij->i", cross, cross)
        edge_sq = np.maximum.reduce(
            (
                np.einsum("ij,ij->i", e01, e01),
                np.einsum("ij,ij->i", e02, e02),
                np.einsum("ij,ij->i", e12, e12),
            )
        )
        exact_zero += int(np.count_nonzero(cross_sq == 0.0))
        collinear += int(np.count_nonzero(cross_sq <= (edge_sq * edge_sq * COLLINEAR_SINE_EPSILON**2)))
        tiny_area += int(np.count_nonzero(cross_sq <= (2.0 * AREA_EPSILON_M2) ** 2))
    return {
        "evaluated_triangle_count": triangle_count,
        "zero_area_triangle_count_exact": exact_zero,
        "collinear_triangle_count_relative": collinear,
        "triangle_area_at_or_below_epsilon_count": tiny_area,
    }


def edge_and_normal_metrics(
    mesh: bpy.types.Mesh,
    edge_vertices: np.ndarray,
    loop_edges: np.ndarray,
    loop_vertices: np.ndarray,
    polygons: np.ndarray,
) -> dict[str, int]:
    edge_count = len(edge_vertices)
    if len(loop_edges):
        incidence = np.bincount(loop_edges, minlength=edge_count)
        next_loop = np.arange(len(loop_vertices), dtype=np.int32) + 1
        last = polygons[:, 0] + polygons[:, 1] - 1
        next_loop[last] = polygons[:, 0]
        next_vertices = loop_vertices[next_loop]
        stored = edge_vertices[loop_edges]
        forward = (loop_vertices == stored[:, 0]) & (next_vertices == stored[:, 1])
        direction = np.where(forward, 1, -1)
        direction_sum = np.bincount(loop_edges, weights=direction, minlength=edge_count)
    else:
        incidence = np.zeros(edge_count, dtype=np.int64)
        direction_sum = np.zeros(edge_count, dtype=np.float64)
    normals = np.empty(len(mesh.polygons) * 3, dtype=np.float64)
    mesh.polygons.foreach_get("normal", normals)
    normals.shape = (-1, 3)
    lengths = np.linalg.norm(normals, axis=1) if len(normals) else np.empty(0)
    return {
        "boundary_edge_count": int(np.count_nonzero(incidence == 1)),
        "open_boundary_edge_count": int(np.count_nonzero(incidence == 1)),
        "manifold_edge_count": int(np.count_nonzero(incidence == 2)),
        "nonmanifold_edge_count": int(np.count_nonzero(incidence > 2)),
        "loose_edge_count": int(np.count_nonzero(incidence == 0)),
        "orientation_conflict_edge_count": int(np.count_nonzero((incidence == 2) & (np.abs(direction_sum) == 2))),
        "zero_face_normal_count": int(np.count_nonzero(lengths <= 1.0e-12)),
        "nonunit_face_normal_count": int(np.count_nonzero(np.abs(lengths - 1.0) > 1.0e-5)),
        "ngon_face_count": int(np.count_nonzero(polygons[:, 1] != 3)),
    }


def evaluated_bbox(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> list[float] | None:
    evaluated = obj.evaluated_get(depsgraph)
    if not evaluated.bound_box:
        return None
    points = [evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box]
    return [
        min(point.x for point in points),
        min(point.y for point in points),
        min(point.z for point in points),
        max(point.x for point in points),
        max(point.y for point in points),
        max(point.z for point in points),
    ]


def one_mesh_metrics(obj: bpy.types.Object, depsgraph: bpy.types.Depsgraph) -> dict[str, object]:
    mesh = obj.data
    mesh.update(calc_edges=True, calc_edges_loose=True)
    coordinates, edge_vertices, loop_edges, loop_vertices, polygons = local_arrays(mesh)
    finite_rows = np.all(np.isfinite(coordinates), axis=1)
    finite_coordinates = coordinates[finite_rows]
    unique_count = len(np.unique(finite_coordinates, axis=0)) if len(finite_coordinates) else 0
    transform = obj.matrix_world
    scale = transform.to_scale()
    axes = transform.to_3x3().normalized()
    axis_dots = [[float(axes.col[column].dot(Vector(axis))) for axis in ((1, 0, 0), (0, 1, 0), (0, 0, 1))] for column in range(3)]
    material_names = [slot.material.name for slot in obj.material_slots if slot.material]
    metrics: dict[str, object] = {
        "name": obj.name,
        "name_length": len(obj.name),
        "vertex_count": len(mesh.vertices),
        "edge_count": len(mesh.edges),
        "polygon_count": len(mesh.polygons),
        "loop_count": len(mesh.loops),
        "nonfinite_vertex_count": int(len(coordinates) - np.count_nonzero(finite_rows)),
        "exact_duplicate_vertex_count_within_object": int(len(finite_coordinates) - unique_count),
        "evaluated_world_bbox_m": evaluated_bbox(obj, depsgraph),
        "world_scale": [float(scale.x), float(scale.y), float(scale.z)],
        "world_axis_dot_matrix": axis_dots,
        "material_slot_count": len(obj.material_slots),
        "material_names": material_names,
    }
    metrics.update(triangle_metrics(mesh, coordinates))
    metrics.update(edge_and_normal_metrics(mesh, edge_vertices, loop_edges, loop_vertices, polygons))
    return metrics


def aggregate_audit(stage: str, sku: str) -> dict[str, object]:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    objects = sorted((obj for obj in bpy.context.scene.objects if obj.type == "MESH"), key=lambda obj: obj.name)
    object_metrics = [one_mesh_metrics(obj, depsgraph) for obj in objects]
    bboxes = [item["evaluated_world_bbox_m"] for item in object_metrics if item["evaluated_world_bbox_m"]]
    names = [item["name"] for item in object_metrics]
    materials = sorted({name for item in object_metrics for name in item["material_names"]})
    sum_fields = (
        "vertex_count",
        "edge_count",
        "polygon_count",
        "loop_count",
        "evaluated_triangle_count",
        "nonfinite_vertex_count",
        "exact_duplicate_vertex_count_within_object",
        "zero_area_triangle_count_exact",
        "collinear_triangle_count_relative",
        "triangle_area_at_or_below_epsilon_count",
        "boundary_edge_count",
        "open_boundary_edge_count",
        "manifold_edge_count",
        "nonmanifold_edge_count",
        "loose_edge_count",
        "orientation_conflict_edge_count",
        "zero_face_normal_count",
        "nonunit_face_normal_count",
        "ngon_face_count",
        "material_slot_count",
    )
    totals = {field: sum(int(item[field]) for item in object_metrics) for field in sum_fields}
    world_bbox = (
        [
            min(box[0] for box in bboxes),
            min(box[1] for box in bboxes),
            min(box[2] for box in bboxes),
            max(box[3] for box in bboxes),
            max(box[4] for box in bboxes),
            max(box[5] for box in bboxes),
        ]
        if bboxes
        else None
    )
    max_scale_error = max((abs(value - 1.0) for item in object_metrics for value in item["world_scale"]), default=0.0)
    max_axis_error = max(
        (
            abs(item["world_axis_dot_matrix"][column][axis] - (1.0 if column == axis else 0.0))
            for item in object_metrics
            for column in range(3)
            for axis in range(3)
        ),
        default=0.0,
    )
    return {
        "stage": stage,
        "sku": sku,
        "blender_version": bpy.app.version_string,
        "scene_unit_system": bpy.context.scene.unit_settings.system,
        "scene_unit_scale_length": bpy.context.scene.unit_settings.scale_length,
        "mesh_object_count": len(objects),
        "object_name_set_sha256": sha256_text(names),
        "object_name_max_length": max((len(name) for name in names), default=0),
        "object_names": names,
        "object_name_samples": names[:16],
        "unique_material_count": len(materials),
        "material_name_set_sha256": sha256_text(materials),
        "totals": totals,
        "evaluated_world_bbox_m": world_bbox,
        "max_world_scale_abs_error_from_one": max_scale_error,
        "max_world_axis_abs_error_from_identity": max_axis_error,
        "object_metrics": object_metrics,
        "metric_policy": {
            "duplicate_scope": "exact coordinate duplicates within each object; cross-object merging is prohibited to preserve hierarchy",
            "merge_distance_m": MERGE_DISTANCE_M,
            "area_epsilon_m2": AREA_EPSILON_M2,
            "collinear_sine_epsilon": COLLINEAR_SINE_EPSILON,
            "boundary_definition": "mesh edge used by exactly one polygon",
            "nonmanifold_definition": "mesh edge used by more than two polygons",
            "orientation_conflict_definition": "two-face edge traversed in the same direction by both polygons",
        },
        "semantic_axis_and_ports": {
            "status": "UNVERIFIED",
            "reason": "Frozen Phase 1 contains no authoritative per-SKU optical/fiber/detector port coordinate frames; only the canonical Z-up transfer frame is tested.",
        },
    }


def configure_scene_units() -> None:
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = "METERS"


def import_raw(obj_path: Path) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    configure_scene_units()
    result = bpy.ops.wm.obj_import(
        filepath=str(obj_path.resolve(strict=True)),
        global_scale=1.0,
        clamp_size=0.0,
        forward_axis="Y",
        up_axis="Z",
        use_split_objects=True,
        use_split_groups=True,
        import_vertex_groups=False,
        validate_meshes=False,
        close_spline_loops=False,
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"OBJ import did not finish: {result}")


def face_is_degenerate(face: bmesh.types.BMFace) -> bool:
    area = face.calc_area()
    if area <= AREA_EPSILON_M2:
        return True
    if len(face.verts) == 3:
        a, b, c = (vert.co for vert in face.verts)
        e01 = b - a
        e02 = c - a
        e12 = c - b
        maximum_edge_sq = max(e01.length_squared, e02.length_squared, e12.length_squared)
        return e01.cross(e02).length_squared <= maximum_edge_sq**2 * COLLINEAR_SINE_EPSILON**2
    return False


def clean_meshes() -> list[dict[str, object]]:
    operations: list[dict[str, object]] = []
    for obj in sorted((item for item in bpy.context.scene.objects if item.type == "MESH"), key=lambda item: item.name):
        mesh = obj.data
        before = {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "polygons": len(mesh.polygons)}
        bm = bmesh.new()
        bm.from_mesh(mesh)
        merge_passes = []
        total_vertices_removed = 0
        total_edges_removed_by_merge = 0
        total_faces_removed_by_merge = 0
        total_vertices_removed_by_delete = 0
        total_edges_removed_by_delete = 0
        total_faces_removed_by_delete = 0
        deleted_degenerate_faces = 0
        merge_converged = False
        # ponytail: 16 deterministic passes bound pathological inputs; the audit
        # exposes the ceiling so a catalog-scale pipeline can replace it later.
        for pass_index in range(1, 17):
            vertices_before_pass = len(bm.verts)
            edges_before_pass = len(bm.edges)
            faces_before_pass = len(bm.faces)
            bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=MERGE_DISTANCE_M)
            vertices_removed = vertices_before_pass - len(bm.verts)
            edges_removed_by_merge = edges_before_pass - len(bm.edges)
            faces_removed_by_merge = faces_before_pass - len(bm.faces)
            vertices_after_merge = len(bm.verts)
            edges_after_merge = len(bm.edges)
            faces_after_merge = len(bm.faces)
            degenerate_faces = [face for face in bm.faces if face_is_degenerate(face)]
            faces_deleted = len(degenerate_faces)
            if degenerate_faces:
                bmesh.ops.delete(bm, geom=degenerate_faces, context="FACES")
            vertices_removed_by_delete = vertices_after_merge - len(bm.verts)
            edges_removed_by_delete = edges_after_merge - len(bm.edges)
            faces_removed_by_delete = faces_after_merge - len(bm.faces)
            total_vertices_removed += vertices_removed
            total_edges_removed_by_merge += edges_removed_by_merge
            total_faces_removed_by_merge += faces_removed_by_merge
            total_vertices_removed_by_delete += vertices_removed_by_delete
            total_edges_removed_by_delete += edges_removed_by_delete
            total_faces_removed_by_delete += faces_removed_by_delete
            deleted_degenerate_faces += faces_deleted
            merge_passes.append(
                {
                    "pass": pass_index,
                    "vertices_before": vertices_before_pass,
                    "vertices_removed": vertices_removed,
                    "edges_before": edges_before_pass,
                    "edges_removed_by_merge": edges_removed_by_merge,
                    "faces_before": faces_before_pass,
                    "faces_removed_by_merge": faces_removed_by_merge,
                    "degenerate_faces_selected_for_explicit_delete": faces_deleted,
                    "vertices_removed_by_explicit_delete_cascade": vertices_removed_by_delete,
                    "edges_removed_by_explicit_delete_cascade": edges_removed_by_delete,
                    "faces_removed_by_explicit_delete": faces_removed_by_delete,
                }
            )
            if vertices_removed == 0 and faces_deleted == 0:
                merge_converged = True
                break
        if bm.faces:
            bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update(calc_edges=True, calc_edges_loose=True)
        pre_validate = {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "polygons": len(mesh.polygons)}
        categorized_removed = {
            "vertices": total_vertices_removed + total_vertices_removed_by_delete,
            "edges": total_edges_removed_by_merge + total_edges_removed_by_delete,
            "polygons": total_faces_removed_by_merge + total_faces_removed_by_delete,
        }
        actual_bmesh_removed = {key: before[key] - pre_validate[key] for key in before}
        unattributed = {key: actual_bmesh_removed[key] - categorized_removed[key] for key in before}
        validate_changed = bool(mesh.validate(verbose=False, clean_customdata=True))
        mesh.update(calc_edges=True, calc_edges_loose=True)
        after = {"vertices": len(mesh.vertices), "edges": len(mesh.edges), "polygons": len(mesh.polygons)}
        operations.append(
            {
                "object_name": obj.name,
                "before": before,
                "merge_by_distance_m": MERGE_DISTANCE_M,
                "merge_passes": merge_passes,
                "merge_operator_fixed_point_reached": merge_converged,
                "merge_pass_limit": 16,
                "vertices_removed_by_merge": total_vertices_removed,
                "edges_removed_by_merge": total_edges_removed_by_merge,
                "faces_removed_implicitly_by_merge": total_faces_removed_by_merge,
                "degenerate_faces_selected_for_explicit_delete": deleted_degenerate_faces,
                "vertices_removed_by_explicit_delete_cascade": total_vertices_removed_by_delete,
                "edges_removed_by_explicit_delete_cascade": total_edges_removed_by_delete,
                "faces_removed_by_explicit_delete": total_faces_removed_by_delete,
                "categorized_bmesh_removed_counts": categorized_removed,
                "actual_bmesh_removed_counts": actual_bmesh_removed,
                "unattributed_bmesh_removed_counts": unattributed,
                "all_bmesh_count_changes_attributed": all(value == 0 for value in unattributed.values()),
                "normals_recalculated": True,
                "hole_filling_performed": False,
                "cross_object_merge_performed": False,
                "pre_validate": pre_validate,
                "mesh_validate_reported_change": validate_changed,
                "after_validate": after,
                "validate_count_delta": {key: after[key] - pre_validate[key] for key in pre_validate},
            }
        )
    return operations


def add_render_setup(world_bbox: list[float]) -> None:
    for obj in list(bpy.context.scene.objects):
        if obj.type in {"CAMERA", "LIGHT"}:
            bpy.data.objects.remove(obj, do_unlink=True)
    minimum = Vector(world_bbox[:3])
    maximum = Vector(world_bbox[3:])
    center = (minimum + maximum) * 0.5
    extent = maximum - minimum
    diameter = max(extent.length, 0.001)
    camera_data = bpy.data.cameras.new("AuditCamera")
    camera = bpy.data.objects.new("AuditCamera", camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = center + Vector((1.5, -1.7, 1.2)).normalized() * diameter * 2.5
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = max(extent.x, extent.y, extent.z, 0.001) * 1.65
    bpy.context.scene.camera = camera
    for name, location, energy_factor, size in (
        ("Key", center + Vector((1.2, -1.0, 1.8)) * diameter, 350.0, diameter),
        ("Fill", center + Vector((-1.3, 0.8, 0.9)) * diameter, 140.0, diameter),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = max(2.0, energy_factor * diameter * diameter)
        light_data.shape = "DISK"
        light_data.size = max(size, 0.01)
        light = bpy.data.objects.new(name, light_data)
        bpy.context.scene.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "None"
    if scene.world is None:
        scene.world = bpy.data.worlds.new("AuditWorld")
    scene.world.color = (0.025, 0.025, 0.025)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    args = argv()
    if args.mode == "raw":
        if not args.obj or not args.blend:
            raise SystemExit("raw mode requires --obj and --blend")
        source_groups = source_obj_groups(args.obj)
        import_raw(args.obj)
        audit = aggregate_audit("raw_import_before_cleanup", args.sku)
        imported_names = set(audit["object_names"])
        source_names = set(source_groups["group_names"])
        audit["source_obj_groups"] = source_groups
        audit["exact_source_group_to_blender_object_name_match_count"] = len(imported_names & source_names)
        audit["import_settings"] = {
            "global_scale": 1.0,
            "forward_axis": "Y",
            "up_axis": "Z",
            "use_split_objects": True,
            "use_split_groups": True,
            "validate_meshes": False,
            "close_spline_loops": False,
        }
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        audit["saved_private_blend"] = True
        write_json(args.audit, audit)
    elif args.mode == "clean":
        if not args.blend or not args.render:
            raise SystemExit("clean mode requires --blend and --render")
        configure_scene_units()
        before = aggregate_audit("raw_blend_reopened_before_cleanup", args.sku)
        operations = clean_meshes()
        after = aggregate_audit("after_explicit_cleanup", args.sku)
        add_render_setup(after["evaluated_world_bbox_m"])
        bpy.ops.wm.save_as_mainfile(filepath=str(args.blend.resolve()))
        bpy.context.scene.render.filepath = str(args.render.resolve())
        bpy.ops.render.render(write_still=True)
        write_json(
            args.audit,
            {
                "stage": "explicit_cleanup",
                "sku": args.sku,
                "before": before,
                "operations": operations,
                "after": after,
                "saved_private_blend": True,
                "public_render_candidate_created": True,
            },
        )
    else:
        audit = aggregate_audit("saved_clean_blend_reopen", args.sku)
        audit["saved_blend_reopen_completed"] = True
        write_json(args.audit, audit)


if __name__ == "__main__":
    main()
