#!/usr/bin/env python3
"""Run and audit the locked representative STEP conversions with OCCT/XCAF."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

from lock_runtime import OCCT_STAGE, occt_environment, sha256, utc_now


ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "work" / "phase2"
PRIVATE = PHASE2 / "private" / "occt_r2"
AUDIT = PHASE2 / "audit"
SCRIPT = PHASE2 / "scripts" / "occt_audit_one.tcl"
PHASE1_PUBLIC = ROOT / "outputs" / "thorlabs_cad_phase1_public"
CAD_CACHE = ROOT / "work" / "cad-cache" / "selected"

MARKER = re.compile(
    r"^__PHASE2_BEGIN__:(?P<name>[^\r\n]+)\r?\n(?P<value>.*?)^__PHASE2_END__:(?P=name)\s*$",
    re.MULTILINE | re.DOTALL,
)
TOPOLOGY_NAMES = ("VERTEX", "EDGE", "WIRE", "FACE", "SHELL", "SOLID", "COMPSOLID", "COMPOUND", "SHAPE")


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_blocks(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in MARKER.finditer(text):
        name = match.group("name").strip()
        if name in result:
            raise RuntimeError(f"duplicate OCCT marker: {name}")
        result[name] = match.group("value").strip()
    return result


def parse_topology(value: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for name in TOPOLOGY_NAMES:
        match = re.search(rf"^\s*{name}\s*:\s*(\d+)\s*$", value, re.MULTILINE)
        if not match:
            raise RuntimeError(f"missing topology count {name}")
        counts[name.casefold()] = int(match.group(1))
    return counts


def parse_file_unit(value: str) -> str:
    match = re.search(r"LENGTH Unit\s*\r?\n([^\r\n]+)", value, re.IGNORECASE)
    if not match:
        raise RuntimeError("STEP length unit missing")
    return match.group(1).strip().casefold()


def parse_mesh_policy(value: str) -> dict[str, object]:
    result: dict[str, object] = {}
    for token in value.split():
        key, raw = token.split("=", 1)
        if re.fullmatch(r"[-+]?\d+", raw):
            result[key] = int(raw)
        elif re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?", raw):
            result[key] = float(raw)
        else:
            result[key] = raw
    return result


def first_int(patterns: tuple[str, ...], value: str) -> int | None:
    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE | re.MULTILINE)
        if match:
            return int(match.group(1))
    return None


def parse_xcaf(blocks: dict[str, str]) -> dict[str, object]:
    stat = blocks.get("XCAF_STAT", "")
    graph = blocks.get("XCAF_ASSEMBLY_GRAPH", "")
    tree = blocks.get("XCAF_ASSEMBLY_TREE", "")
    nomen = blocks.get("XCAF_NOMENCLATURE", "")
    names = first_int(
        (
            r"labels?\s+with\s+name\s*(?:[:=])\s*(\d+)",
            r"names?\s*:?\s*(\d+)",
        ),
        stat,
    )
    shape_labels = first_int(
        (
            r"total\s+number\s+of\s+labels?\s+for\s+shapes?[^\r\n]*?=\s*(\d+)",
            r"shape\s+labels?\s*:?\s*(\d+)",
        ),
        stat,
    )
    color_links = first_int((r"labels?\s+with\s+color\s+link\s*(?:[:=])\s*(\d+)",), stat)
    layer_links = first_int((r"labels?\s+with\s+layer\s+link\s*(?:[:=])\s*(\d+)",), stat)
    material_links = first_int((r"labels?\s+with\s+vis\s+material\s+link\s*(?:[:=])\s*(\d+)",), stat)
    colors = first_int((r"^\s*Number\s+of\s+colors\s*=\s*(\d+)",), stat)
    layers = first_int((r"^\s*Number\s+of\s+layers\s*=\s*(\d+)",), stat)
    materials = first_int((r"^\s*Number\s+of\s+vis\s+materials\s*=\s*(\d+)",), stat)
    graph_nodes = len(re.findall(r"^\s*\d+\s+[ROAP]\b", graph, re.MULTILINE))
    definition_names = re.findall(r"^\s*\d+\s+[RAP]\s+'([^']*)'", graph, re.MULTILINE)
    tree_nonempty_lines = sum(1 for line in tree.splitlines() if line.strip())
    nomen_nonempty_lines = sum(1 for line in nomen.splitlines() if line.strip())
    return {
        "shape_label_count": shape_labels,
        "labels_with_name_count": names,
        "labels_with_color_link_count": color_links,
        "labels_with_layer_link_count": layer_links,
        "labels_with_visual_material_link_count": material_links,
        "color_definition_count": colors,
        "layer_definition_count": layers,
        "visual_material_definition_count": materials,
        "assembly_graph_node_syntax_count": graph_nodes,
        "definition_name_count": len(definition_names),
        "definition_name_set_sha256": hashlib.sha256("\n".join(sorted(set(definition_names))).encode("utf-8")).hexdigest(),
        "assembly_tree_nonempty_line_count": tree_nonempty_lines,
        "nomenclature_nonempty_line_count": nomen_nonempty_lines,
        "private_full_tree_log_retained": True,
    }


def inspect_obj(path: Path) -> dict[str, object]:
    counters = {"vertex": 0, "normal": 0, "texture_coordinate": 0, "face": 0, "group": 0, "material_use": 0}
    groups: list[str] = []
    nonfinite_vertices = 0
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    with path.open("r", encoding="utf-8", errors="strict", newline="") as handle:
        for line in handle:
            if line.startswith("v "):
                counters["vertex"] += 1
                xyz = [float(value) for value in line.split()[1:4]]
                if not all(math.isfinite(value) for value in xyz):
                    nonfinite_vertices += 1
                    continue
                for axis, value in enumerate(xyz):
                    minimum[axis] = min(minimum[axis], value)
                    maximum[axis] = max(maximum[axis], value)
            elif line.startswith("vn "):
                counters["normal"] += 1
            elif line.startswith("vt "):
                counters["texture_coordinate"] += 1
            elif line.startswith("f "):
                counters["face"] += 1
            elif line.startswith("g "):
                counters["group"] += 1
                groups.append(line[2:].strip())
            elif line.startswith("usemtl "):
                counters["material_use"] += 1
    material_library = path.with_suffix(".mtl")
    return {
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "counts": counters,
        "unique_group_count": len(set(groups)),
        "all_groups_nonempty": all(groups),
        "root_group_samples": sorted(set(group.split("/", 1)[0] for group in groups))[:12],
        "group_samples": sorted(set(groups))[:16],
        "group_name_max_length": max((len(group) for group in groups), default=0),
        "vertex_bbox_m": minimum + maximum if counters["vertex"] else None,
        "nonfinite_vertex_count": nonfinite_vertices,
        "material_library": (
            {"bytes": material_library.stat().st_size, "sha256": sha256(material_library)}
            if material_library.is_file()
            else None
        ),
    }


def parse_mesh_info(value: str) -> dict[str, int | float | None]:
    def number(pattern: str, cast):
        match = re.search(pattern, value, re.IGNORECASE | re.MULTILINE)
        return cast(match.group(1)) if match else None

    face_count = number(r"shape\s+contains\s+(\d+)\s+faces", int)
    empty_face_match = re.search(r"^\s*(\d+)\s+empty\s+faces", value, re.IGNORECASE | re.MULTILINE)
    triangle_count = number(r"^\s*(\d+)\s+triangles", int)
    empty_face_count = int(empty_face_match.group(1)) if empty_face_match else (0 if face_count is not None and triangle_count is not None else None)
    return {
        "face_count": face_count,
        "empty_face_count": empty_face_count,
        "empty_face_line_present": empty_face_match is not None,
        "triangle_count": triangle_count,
        "node_count": number(r"^\s*(\d+)\s+nodes", int),
        "polygon_on_triangulation_count": number(r"^\s*(\d+)\s+polygons\s+on\s+triangulation", int),
        "maximal_deflection": number(r"Maximal\s+deflection\s+([-+0-9.eE]+)", float),
    }


def run_one(sku: str, source: Path, run_dir: Path, timeout: int) -> dict[str, object]:
    obj = run_dir / "model.obj"
    log = run_dir / "occt.log"
    if run_dir.exists():
        if not obj.is_file() or not log.is_file():
            raise RuntimeError(f"incomplete existing OCCT run; fail closed: {relative(run_dir)}")
        stdout = log.read_text(encoding="utf-8")
        returncode = 0
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
        env = occt_environment()
        env.update(
            {
                "PHASE2_STEP": relative(source),
                "PHASE2_OBJ": relative(obj),
                "PHASE2_SKU": sku,
                "OMP_NUM_THREADS": "1",
                "TBB_NUM_THREADS": "1",
            }
        )
        result = subprocess.run(
            [str(OCCT_STAGE / "DRAWEXE.exe"), "-b", "-f", str(SCRIPT)],
            cwd=ROOT,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        stdout = result.stdout
        returncode = result.returncode
        log.write_text(stdout, encoding="utf-8", newline="\n")
    blocks = parse_blocks(stdout)
    if returncode != 0 or blocks.get("RUN_COMPLETE") != "PASS" or not obj.is_file():
        raise RuntimeError(f"OCCT conversion failed for {sku}; exit={returncode}; log={relative(log)}")
    required = {
        "STEP_UNITS",
        "DOCUMENT_LENGTH_UNIT",
        "DOCUMENT_LENGTH_SCALE_TO_M",
        "XCAF_ASSEMBLY_TREE",
        "XCAF_ASSEMBLY_GRAPH",
        "XCAF_NOMENCLATURE",
        "XCAF_STAT",
        "AGGREGATE_TOPOLOGY",
        "NATIVE_BBOX_MM",
        "AGGREGATE_BREP_VALIDITY",
        "MESH_POLICY",
        "PRE_MESH_INFO",
        "POST_MESH_INFO",
        "WRITE_OBJ",
    }
    missing = sorted(required - blocks.keys())
    if missing:
        raise RuntimeError(f"OCCT audit blocks missing for {sku}: {missing}")
    bbox = [float(item) for item in blocks["NATIVE_BBOX_MM"].split()]
    if len(bbox) != 6 or not all(math.isfinite(item) for item in bbox):
        raise RuntimeError(f"invalid native bbox for {sku}")
    bbox_bounded = blocks["NATIVE_BBOX_STATUS"] == "BOUNDED" and all(abs(item) < 1e50 for item in bbox)
    mesh_status = blocks["SERIAL_MESH"]
    post_mesh = parse_mesh_info(blocks["POST_MESH_INFO"])
    obj_info = inspect_obj(obj)
    definition_names = re.findall(r"^\s*\d+\s+[RAP]\s+'([^']*)'", blocks["XCAF_ASSEMBLY_GRAPH"], re.MULTILINE)
    group_components = {component for group in obj_info["group_samples"] for component in group.split("/")}
    matched_definition_names = sum(1 for name in set(definition_names) if name in group_components)
    top_count = int(blocks["TOP_LEVEL_COUNT"])
    top_audits = []
    for index in range(1, top_count + 1):
        top_audits.append(
            {
                "label": blocks[f"TOP_LABEL_{index}_ENTRY"],
                "topology": parse_topology(blocks[f"TOP_LABEL_{index}_TOPOLOGY"]),
                "brep_validity": blocks[f"TOP_LABEL_{index}_BREP_VALIDITY"],
                "brep_valid": "seems to be valid" in blocks[f"TOP_LABEL_{index}_BREP_VALIDITY"].casefold(),
                "location_summary": blocks[f"TOP_LABEL_{index}_LOCATION"],
            }
        )
    return {
        "exit_code": returncode,
        "step_file_unit": parse_file_unit(blocks["STEP_UNITS"]),
        "document_length_unit": blocks["DOCUMENT_LENGTH_UNIT"].casefold(),
        "document_length_scale_to_m": float(blocks["DOCUMENT_LENGTH_SCALE_TO_M"]),
        "native_bbox_mm": bbox,
        "native_bbox_status": blocks["NATIVE_BBOX_STATUS"],
        "native_bbox_bounded": bbox_bounded,
        "native_bbox_diagonal_mm": float(blocks["NATIVE_BBOX_DIAGONAL_MM"]) if bbox_bounded else None,
        "aggregate_topology": parse_topology(blocks["AGGREGATE_TOPOLOGY"]),
        "aggregate_brep_validity": blocks["AGGREGATE_BREP_VALIDITY"],
        "aggregate_brep_valid": "seems to be valid" in blocks["AGGREGATE_BREP_VALIDITY"].casefold(),
        "aggregate_tolerance_report": blocks.get("AGGREGATE_TOLERANCE"),
        "top_level_shape_count": top_count,
        "top_level_shapes": top_audits,
        "xcaf": parse_xcaf(blocks),
        "xcaf_to_obj_definition_name_match_count": matched_definition_names,
        "mesh_policy": parse_mesh_policy(blocks["MESH_POLICY"]),
        "pre_mesh_info": blocks["PRE_MESH_INFO"],
        "serial_mesh_result": blocks["SERIAL_MESH"],
        "post_mesh_info": blocks["POST_MESH_INFO"],
        "post_mesh_counts": post_mesh,
        "serial_mesh_no_error": "noerror" in mesh_status.casefold() and "failure" not in mesh_status.casefold(),
        "all_faces_triangulated": post_mesh["empty_face_count"] == 0,
        "obj": obj_info,
        "private_log_sha256": sha256(log),
        "private_log_bytes": log.stat().st_size,
        "private_log_retained": True,
    }


def semantic_signature(run: dict[str, object]) -> dict[str, object]:
    return {
        "step_file_unit": run["step_file_unit"],
        "document_length_unit": run["document_length_unit"],
        "document_length_scale_to_m": run["document_length_scale_to_m"],
        "native_bbox_mm": run["native_bbox_mm"],
        "native_bbox_status": run["native_bbox_status"],
        "aggregate_topology": run["aggregate_topology"],
        "aggregate_brep_valid": run["aggregate_brep_valid"],
        "top_level_shape_count": run["top_level_shape_count"],
        "top_level_shapes": run["top_level_shapes"],
        "xcaf": run["xcaf"],
        "xcaf_to_obj_definition_name_match_count": run["xcaf_to_obj_definition_name_match_count"],
        "mesh_policy": run["mesh_policy"],
        "post_mesh_info": run["post_mesh_info"],
        "post_mesh_counts": run["post_mesh_counts"],
        "serial_mesh_no_error": run["serial_mesh_no_error"],
        "all_faces_triangulated": run["all_faces_triangulated"],
        "obj_counts": run["obj"]["counts"],
        "obj_unique_group_count": run["obj"]["unique_group_count"],
        "obj_vertex_bbox_m": run["obj"]["vertex_bbox_m"],
        "obj_nonfinite_vertex_count": run["obj"]["nonfinite_vertex_count"],
        "obj_material_library": run["obj"]["material_library"],
    }


def verify_locks() -> tuple[dict, dict]:
    representatives = load_json(PHASE2 / "REPRESENTATIVE_LOCK.json")
    runtime = load_json(PHASE2 / "RUNTIME_LOCK.json")
    if representatives.get("status") != "PASS" or runtime.get("status") != "PASS":
        raise RuntimeError("representative or runtime lock is not PASS")
    freeze = representatives["phase1_freeze"]
    frozen_files = {
        "cad_manifest_sha256": PHASE1_PUBLIC / "CAD_MANIFEST.json",
        "source_lock_sha256": PHASE1_PUBLIC / "SOURCE_LOCK.json",
        "gate_decision_sha256": PHASE1_PUBLIC / "GATE_DECISION.json",
        "manifest_sha256_file_sha256": PHASE1_PUBLIC / "MANIFEST.sha256",
    }
    for key, path in frozen_files.items():
        if sha256(path) != freeze[key]:
            raise RuntimeError(f"Phase 1 freeze mismatch: {path.name}")
    if sha256(PHASE2 / "RUNTIME_BINARY_MANIFEST.sha256") != runtime["binary_manifest"]["sha256"]:
        raise RuntimeError("runtime binary manifest changed")
    return representatives, runtime


def main() -> int:
    representatives, runtime = verify_locks()
    AUDIT.mkdir(parents=True, exist_ok=True)
    PRIVATE.mkdir(parents=True, exist_ok=True)
    results = []
    for representative in representatives["representatives"]:
        sku = representative["sku"]
        slug = re.sub(r"[^A-Za-z0-9]+", "_", sku).strip("_")
        source = CAD_CACHE / representative["cache_filename"]
        if source.stat().st_size != representative["raw_bytes"] or sha256(source) != representative["raw_sha256"]:
            raise RuntimeError(f"locked STEP mismatch: {sku}")
        sku_root = PRIVATE / slug
        first = run_one(sku, source, sku_root / "run1", timeout=3600)
        second = run_one(sku, source, sku_root / "run2", timeout=3600)
        exact_obj_repeat = first["obj"]["sha256"] == second["obj"]["sha256"]
        exact_mtl_repeat = first["obj"]["material_library"] == second["obj"]["material_library"]
        semantic_repeat = semantic_signature(first) == semantic_signature(second)
        topology = first["aggregate_topology"]
        is_surface_only = topology["solid"] == 0 and topology["face"] > 0
        input_is_inch = first["step_file_unit"] == "inch"
        unit_gate = (
            first["document_length_unit"] == "mm"
            and math.isclose(first["document_length_scale_to_m"], 0.001, rel_tol=0.0, abs_tol=1e-15)
            and (not input_is_inch or representative["phase1_text_unit"] == "inch")
        )
        def mesh_run_pass(run: dict[str, object]) -> bool:
            counts = run["post_mesh_counts"]
            return bool(
                run["serial_mesh_no_error"]
                and run["all_faces_triangulated"]
                and counts["face_count"] == run["aggregate_topology"]["face"]
                and (counts["triangle_count"] or 0) > 0
                and (counts["node_count"] or 0) > 0
                and run["obj"]["nonfinite_vertex_count"] == 0
            )

        mesh_gate = mesh_run_pass(first) and mesh_run_pass(second)
        assembly_like = first["xcaf"]["assembly_graph_node_syntax_count"] > 1
        nomenclature_count = first["xcaf"]["nomenclature_nonempty_line_count"]
        obj_group_count = first["obj"]["unique_group_count"]
        definition_count = first["xcaf"]["definition_name_count"]
        matched_definition_count = first["xcaf_to_obj_definition_name_match_count"]
        name_retention_gate = (
            "PARTIAL_SCOPED"
            if assembly_like
            else ("PASS" if matched_definition_count == definition_count and definition_count > 0 else "UNVERIFIED")
        )
        partial_reasons = []
        if is_surface_only:
            partial_reasons.append("surface_only_no_manifold_solid")
        if not first["native_bbox_bounded"]:
            partial_reasons.append("native_exact_bbox_unbounded_sentinel")
        if name_retention_gate != "PASS":
            partial_reasons.append("name_retention_not_complete")
        brep_gate_pass = first["aggregate_brep_valid"] and all(shape["brep_valid"] for shape in first["top_level_shapes"])
        determinism_gate_pass = exact_obj_repeat and exact_mtl_repeat and semantic_repeat
        hard_item_gate_pass = unit_gate and determinism_gate_pass and brep_gate_pass and mesh_gate
        status = "BLOCKED" if not hard_item_gate_pass else ("PARTIAL_SCOPED" if partial_reasons else "PASS")
        results.append(
            {
                "sku": sku,
                "status": status,
                "locked_input": {
                    "bytes": representative["raw_bytes"],
                    "sha256": representative["raw_sha256"],
                },
                "unit_gate": {
                    "status": "PASS" if unit_gate else "BLOCKED",
                    "step_file_unit": first["step_file_unit"],
                    "document_length_unit": first["document_length_unit"],
                    "document_length_scale_to_m": first["document_length_scale_to_m"],
                    "inch_to_mm_conversion_exercised": input_is_inch,
                },
                "surface_classification": "surface_only_partial" if is_surface_only else "manifold_solid_present",
                "native_bbox_gate": "PASS" if first["native_bbox_bounded"] else "UNVERIFIED",
                "name_retention_gate": {
                    "status": name_retention_gate,
                    "xcaf_assembly_like": assembly_like,
                    "xcaf_named_shape_label_count": first["xcaf"]["labels_with_name_count"],
                    "xcaf_nomenclature_nonempty_line_count": nomenclature_count,
                    "xcaf_definition_name_count": definition_count,
                    "xcaf_definition_names_matched_in_obj_groups": matched_definition_count,
                    "obj_unique_group_count": obj_group_count,
                    "claim_limit": "Counts prove syntax retention only; they do not prove one-to-one assembly hierarchy retention.",
                },
                "partial_reasons": partial_reasons,
                "run1": first,
                "run2_repeat_evidence": {
                    "native_bbox_mm": second["native_bbox_mm"],
                    "native_bbox_status": second["native_bbox_status"],
                    "aggregate_topology": second["aggregate_topology"],
                    "aggregate_brep_valid": second["aggregate_brep_valid"],
                    "post_mesh_info": second["post_mesh_info"],
                    "post_mesh_counts": second["post_mesh_counts"],
                    "serial_mesh_no_error": second["serial_mesh_no_error"],
                    "all_faces_triangulated": second["all_faces_triangulated"],
                    "obj": second["obj"],
                    "private_log_sha256": second["private_log_sha256"],
                    "private_log_bytes": second["private_log_bytes"],
                },
                "determinism_gate": {
                    "status": "PASS" if determinism_gate_pass else "BLOCKED",
                    "exact_obj_sha256_repeat": exact_obj_repeat,
                    "exact_material_library_repeat": exact_mtl_repeat,
                    "semantic_signature_repeat": semantic_repeat,
                },
                "brep_gate": "PASS" if brep_gate_pass else "BLOCKED",
                "serial_mesh_gate": "PASS" if mesh_gate else "BLOCKED",
                "vendor_and_derived_geometry_publication": "PROHIBITED",
            }
        )
        print(json.dumps({"sku": sku, "status": status, "obj_repeat": exact_obj_repeat, "semantic_repeat": semantic_repeat}, sort_keys=True), flush=True)
    hard_gate_pass = all(
        item["unit_gate"]["status"] == "PASS"
        and item["determinism_gate"]["status"] == "PASS"
        and item["brep_gate"] == "PASS"
        and item["run1"]["serial_mesh_no_error"]
        and item["run1"]["all_faces_triangulated"]
        for item in results
    )
    has_scoped_partial = any(item["status"] == "PARTIAL_SCOPED" for item in results)
    overall_status = "BLOCKED" if not hard_gate_pass else ("PARTIAL_SCOPED" if has_scoped_partial else "PASS")
    payload = {
        "schema": "opticalmodeler.phase2_occt_xcaf_audit.v1",
        "status": overall_status,
        "generated_at_utc": utc_now(),
        "runtime_lock": {
            "occt_version": runtime["occt"]["version"],
            "drawexe_sha256": next(
                item["sha256"] for item in runtime["occt"]["core_binaries"] if item["path"].endswith("/DRAWEXE.exe")
            ),
        },
        "execution_policy": "Four locked representatives only; rejected preflight retained; canonical r2 uses finite-part exact-geometry bbox, two sequential OCCT processes per item, incmesh parallel=0 and watson, no OCCT task overlaps, no GLB.",
        "rejected_preflight": {
            "status": "REJECTED",
            "reason": "PDA100A2 exact-geometry bbox included unbounded surface extents (+/-1e100), producing an invalid mesh policy and explicit OCCT Meshing statuses: Failure. Evidence remains in the private occt revision; no preflight geometry is public.",
            "private_revision_retained": True,
        },
        "result_count": len(results),
        "results": results,
        "script_hashes": {
            "occt_audit_one_tcl_sha256": sha256(SCRIPT),
            "run_occt_conversion_py_sha256": sha256(Path(__file__)),
        },
        "private_geometry_retained_outside_public_package": True,
    }
    output = AUDIT / "OCCT_XCAF_AUDIT.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": payload["status"], "audit_sha256": sha256(output), "representatives": len(results)}, sort_keys=True))
    return 0 if hard_gate_pass else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        raise
