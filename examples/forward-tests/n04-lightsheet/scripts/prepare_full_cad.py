"""Prepare and fail-closed audit private CAD mesh derivatives for the 32-node build.

Only manufacturer STEP files locked by Phase 1 are accepted.  Every STEP is
read in its native millimetre coordinate frame with OpenCascade, checked
against the frozen Phase-1 bounds, tessellated deterministically, stripped of
zero-area/collinear triangles, and checked again before Blender import.

The STL derivatives are vendor-derived geometry.  They remain under ``work``
and are explicitly excluded from the public-candidate package.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parents[2]
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
CACHE = ROOT / "work" / "vendor_cad_cache"
BASE = ROOT / "work" / "full_32_node_propagation_v3"
RAW_DIR = BASE / "vendor_derivatives"
CLEAN_DIR = BASE / "vendor_derivatives_clean"
MEASUREMENTS = BASE / "measurements"
REPORT = MEASUREMENTS / "FULL_CAD_MESH_AUDIT.json"

RECORD = struct.Struct("<12fH")
ABSOLUTE_DOUBLE_AREA_EPSILON_MM2 = 1e-12
NORMALIZED_COLLINEAR_EPSILON = 1e-12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounds(shape, optimal: bool) -> dict:
    box = Bnd_Box()
    if optimal:
        BRepBndLib.AddOptimal_s(shape, box, False, False)
        method = "OpenCascade BRepBndLib.AddOptimal_s(useTriangulation=false,useShapeTolerance=false)"
    else:
        BRepBndLib.Add_s(shape, box)
        method = "OpenCascade BRepBndLib.Add_s"
    values = [float(value) for value in box.Get()]
    minimum, maximum = values[:3], values[3:]
    return {
        "min_mm": minimum,
        "max_mm": maximum,
        "size_mm": [maximum[index] - minimum[index] for index in range(3)],
        "method": method,
    }


def max_bbox_error(first: dict, second: dict) -> float:
    aliases = (("min_mm", "min"), ("max_mm", "max"), ("size_mm", "size"))
    values = []
    for left, right in aliases:
        if left in first and left in second:
            values.extend(abs(first[left][axis] - second[left][axis]) for axis in range(3))
        elif left in first and right in second:
            values.extend(abs(first[left][axis] - second[right][axis]) for axis in range(3))
        else:
            raise KeyError((left, right, first.keys(), second.keys()))
    return max(values)


def cache_path(part: str, original: str) -> Path:
    expected = f"{part.replace('/', '_')}__{original}".casefold()
    matches = [path for path in CACHE.iterdir() if path.name.casefold() == expected]
    if len(matches) != 1:
        raise RuntimeError(f"cache lookup for {part}/{original} returned {len(matches)} files")
    return matches[0]


def read_step(path: Path):
    reader = STEPControl_Reader()
    read_status = reader.ReadFile(str(path))
    transferred = reader.TransferRoots() if read_status == IFSelect_RetDone else 0
    if read_status != IFSelect_RetDone or transferred < 1:
        raise RuntimeError(f"OpenCascade failed to read {path.name}: status={read_status}, roots={transferred}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"OpenCascade returned a null shape for {path.name}")
    return shape, transferred


def tessellation_settings(part: str, maximum_size_mm: float) -> tuple[float, float]:
    if part in {"T1225C", "TF1225R7"}:
        return 1.5, 0.35
    if part in {"S4FC488", "S4FC637"}:
        return 0.8, 0.30
    if part.startswith("P1-"):
        return 0.35, 0.28
    if maximum_size_mm >= 200.0:
        return 0.35, 0.25
    if maximum_size_mm >= 90.0:
        return 0.20, 0.22
    optical = {
        "DMLP505R", "DMLP605R", "AC254-045-A-ML", "AC254-100-A-ML",
        "AC254-150-A-ML", "AC508-100-A-ML", "ACT508-200-A-ML",
        "ACT508-300-A-ML", "ACY254-050-A", "AQWP10M-580", "BB1-E02",
        "CCM1-PBS251/M", "DL20X-PA", "FELH0650", "GBE03-A", "MF525-39",
        "N40X-NIR", "P50K", "PF03-03-P01", "RCF15P-P01", "TTL200-A",
    }
    if part in optical:
        return 0.04, 0.12
    return 0.12, 0.20


def derivative_filename(part: str, index: int, original: str) -> str:
    safe = part.replace("/", "_")
    suffix = Path(original).stem.replace("/", "_")
    return f"{safe}__{index:02d}__{suffix}.stl"


def vector_subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def squared_length(vector) -> float:
    return sum(value * value for value in vector)


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def triangle_class(vertices) -> str:
    edges = (
        vector_subtract(vertices[1], vertices[0]),
        vector_subtract(vertices[2], vertices[1]),
        vector_subtract(vertices[0], vertices[2]),
    )
    edge_squared = [squared_length(edge) for edge in edges]
    if min(edge_squared) == 0.0:
        return "duplicate_vertex"
    area_vector = cross(vector_subtract(vertices[1], vertices[0]), vector_subtract(vertices[2], vertices[0]))
    double_area = math.sqrt(squared_length(area_vector))
    normalized = double_area / max(edge_squared)
    if double_area <= ABSOLUTE_DOUBLE_AREA_EPSILON_MM2 or normalized <= NORMALIZED_COLLINEAR_EPSILON:
        return "distinct_collinear"
    return "valid"


def read_binary_stl(path: Path):
    data = path.read_bytes()
    if len(data) < 84:
        raise ValueError(f"STL too short: {path}")
    count = struct.unpack_from("<I", data, 80)[0]
    expected_bytes = 84 + 50 * count
    if len(data) != expected_bytes:
        raise ValueError(f"not a canonical binary STL: {path} bytes={len(data)} expected={expected_bytes}")
    records = []
    for index in range(count):
        offset = 84 + 50 * index
        unpacked = RECORD.unpack_from(data, offset)
        vertices = (
            tuple(float(value) for value in unpacked[3:6]),
            tuple(float(value) for value in unpacked[6:9]),
            tuple(float(value) for value in unpacked[9:12]),
        )
        records.append({"raw": data[offset:offset + 50], "vertices": vertices, "classification": triangle_class(vertices)})
    return records


def stl_counts(records) -> dict:
    return {
        "triangle_count": len(records),
        "duplicate_vertex_faces": sum(item["classification"] == "duplicate_vertex" for item in records),
        "distinct_collinear_faces": sum(item["classification"] == "distinct_collinear" for item in records),
        "valid_faces": sum(item["classification"] == "valid" for item in records),
    }


def stl_bbox(records) -> dict:
    coordinates = [vertex for item in records for vertex in item["vertices"]]
    minimum = [min(vertex[axis] for vertex in coordinates) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in coordinates) for axis in range(3)]
    return {
        "min_mm": minimum,
        "max_mm": maximum,
        "size_mm": [maximum[index] - minimum[index] for index in range(3)],
        "method": "binary STL float32 vertex envelope",
    }


def write_clean_stl(path: Path, records) -> None:
    header = b"OpticalModeler full32 clean; invalid triangles removed"
    with path.open("wb") as stream:
        stream.write(header[:80].ljust(80, b" "))
        stream.write(struct.pack("<I", len(records)))
        for item in records:
            stream.write(item["raw"])


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    MEASUREMENTS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((PHASE1 / "CAD_MANIFEST.json").read_text(encoding="utf-8"))
    failures = []
    outputs = []
    started = time.time()
    expected_file_count = sum(len(record["cad_files"]) for record in manifest["records"])

    for record_index, record in enumerate(manifest["records"], start=1):
        part = record["requested_part_number"]
        for cad_index, cad in enumerate(record["cad_files"], start=1):
            source = cache_path(part, cad["original_filename"])
            key = f"{part}#{cad_index}"
            print(f"[{len(outputs)+1:02d}/{expected_file_count:02d}] {key}: verify/read", flush=True)
            source_hash = sha256(source)
            if source_hash != cad["sha256"] or source.stat().st_size != cad["bytes"]:
                raise RuntimeError(f"{key}: frozen source bytes/hash changed")
            t0 = time.time()
            shape, transferred_roots = read_step(source)
            conservative = bounds(shape, False)
            optimal = bounds(shape, True)
            phase1_bbox_error_mm = max_bbox_error(conservative, cad["bbox"])
            if phase1_bbox_error_mm > 0.003:
                failures.append(f"{key}: OpenCascade conservative bbox drift {phase1_bbox_error_mm:.9f} mm")

            linear, angular = tessellation_settings(part, max(optimal["size_mm"]))
            mesher = BRepMesh_IncrementalMesh(shape, linear, False, angular, True)
            mesher.Perform()
            if not mesher.IsDone():
                raise RuntimeError(f"{key}: deterministic tessellation failed")

            filename = derivative_filename(part, cad_index, cad["original_filename"])
            raw_path = RAW_DIR / filename
            clean_path = CLEAN_DIR / filename
            writer = StlAPI_Writer()
            writer.ASCIIMode = False
            if not writer.Write(shape, str(raw_path)):
                raise RuntimeError(f"{key}: STL write failed")

            raw_records = read_binary_stl(raw_path)
            raw_counts = stl_counts(raw_records)
            raw_bbox = stl_bbox(raw_records)
            valid_records = [item for item in raw_records if item["classification"] == "valid"]
            write_clean_stl(clean_path, valid_records)
            clean_records = read_binary_stl(clean_path)
            clean_counts = stl_counts(clean_records)
            clean_bbox = stl_bbox(clean_records)
            cleanup_bbox_error_mm = max_bbox_error(clean_bbox, raw_bbox)
            mesh_bbox_error_mm = max_bbox_error(clean_bbox, optimal)
            mesh_bbox_tolerance_mm = max(0.05, min(0.50, max(optimal["size_mm"]) * 0.001))

            local_failures = []
            if clean_counts["duplicate_vertex_faces"] or clean_counts["distinct_collinear_faces"]:
                local_failures.append("cleaned derivative retains invalid triangles")
            if cleanup_bbox_error_mm > 1e-6:
                local_failures.append(f"cleanup changed bbox by {cleanup_bbox_error_mm:.9f} mm")
            if mesh_bbox_error_mm > mesh_bbox_tolerance_mm:
                local_failures.append(
                    f"tessellated bbox error {mesh_bbox_error_mm:.9f} mm > tolerance {mesh_bbox_tolerance_mm:.9f} mm"
                )
            if clean_counts["triangle_count"] != raw_counts["valid_faces"]:
                local_failures.append("triangle count conservation failed")
            failures.extend(f"{key}: {item}" for item in local_failures)

            output = {
                "derivative_key": key,
                "part_number": part,
                "record_index": record_index,
                "cad_file_index": cad_index,
                "status": "PASS" if not local_failures and phase1_bbox_error_mm <= 0.003 else "BLOCKED",
                "official_source": {
                    "original_filename": cad["original_filename"],
                    "source_url": cad["source_url"],
                    "sha256": source_hash,
                    "bytes": source.stat().st_size,
                    "declared_unit": cad["declared_unit"],
                    "scale_to_metre": cad["scale_to_metre"],
                    "source_load_diagnostics": cad.get("source_load_diagnostics"),
                    "redistribution_decision": "EXCLUDE_FROM_PUBLIC_CANDIDATE",
                },
                "opencascade_readback": {
                    "status": "PASS",
                    "transferred_roots": transferred_roots,
                    "conservative_bbox_mm": conservative,
                    "optimal_bbox_mm": optimal,
                    "phase1_conservative_bbox_error_mm": phase1_bbox_error_mm,
                    "coordinate_unit": "millimetre",
                },
                "tessellation": {
                    "linear_deflection_mm": linear,
                    "angular_deflection_rad": angular,
                    "parallel": True,
                },
                "pre_clean_private_derivative": {
                    "relative_private_path": str(raw_path.relative_to(BASE)).replace("\\", "/"),
                    "sha256": sha256(raw_path),
                    "bytes": raw_path.stat().st_size,
                    "bbox_mm": raw_bbox,
                    **raw_counts,
                },
                "post_clean_private_derivative": {
                    "relative_private_path": str(clean_path.relative_to(BASE)).replace("\\", "/"),
                    "sha256": sha256(clean_path),
                    "bytes": clean_path.stat().st_size,
                    "bbox_mm": clean_bbox,
                    **clean_counts,
                },
                "removed": {
                    "duplicate_vertex_faces": raw_counts["duplicate_vertex_faces"],
                    "distinct_collinear_faces": raw_counts["distinct_collinear_faces"],
                    "total": raw_counts["duplicate_vertex_faces"] + raw_counts["distinct_collinear_faces"],
                },
                "cleanup_bbox_error_mm": cleanup_bbox_error_mm,
                "mesh_vs_opencascade_optimal_bbox_error_mm": mesh_bbox_error_mm,
                "mesh_bbox_tolerance_mm": mesh_bbox_tolerance_mm,
                "processing_seconds": time.time() - t0,
                "failures": local_failures,
            }
            outputs.append(output)
            print(
                f"[{len(outputs):02d}/{expected_file_count:02d}] {key}: {output['status']} "
                f"tri={clean_counts['triangle_count']} removed={output['removed']['total']} "
                f"bbox_err={mesh_bbox_error_mm:.6f}mm time={output['processing_seconds']:.1f}s",
                flush=True,
            )

    report = {
        "schema": "opticalmodeler.full32.cad-mesh-audit.v1",
        "status": "PASS" if not failures and len(outputs) == expected_file_count else "BLOCKED",
        "scope": "FULL_32_NODE_PROPAGATION_PRIVATE_VENDOR_DERIVATIVES",
        "phase1_immutable": True,
        "coordinate_unit": "millimetre",
        "scene_scale_to_metre": 0.001,
        "expected_cad_file_count": expected_file_count,
        "processed_cad_file_count": len(outputs),
        "unique_catalog_record_count": len(manifest["records"]),
        "vendor_geometry_public_output_count": 0,
        "source_diagnostic_boundaries": {
            "S4FC488": "PARTIAL_SCOPED; frozen source diagnostics preserved; no closed-solid claim",
            "S4FC637": "PARTIAL_SCOPED; frozen source diagnostics preserved; no closed-solid claim",
        },
        "parts": outputs,
        "totals": {
            "clean_triangle_count": sum(item["post_clean_private_derivative"]["triangle_count"] for item in outputs),
            "clean_mesh_bytes": sum(item["post_clean_private_derivative"]["bytes"] for item in outputs),
            "removed_duplicate_vertex_faces": sum(item["removed"]["duplicate_vertex_faces"] for item in outputs),
            "removed_distinct_collinear_faces": sum(item["removed"]["distinct_collinear_faces"] for item in outputs),
            "post_clean_invalid_faces": sum(
                item["post_clean_private_derivative"]["duplicate_vertex_faces"]
                + item["post_clean_private_derivative"]["distinct_collinear_faces"] for item in outputs
            ),
            "processing_seconds": time.time() - started,
        },
        "failures": failures,
        "redistribution_decision": "EXCLUDE_ALL_STL_DERIVATIVES_FROM_PUBLIC_CANDIDATE",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "cad_files": len(outputs),
        "triangles": report["totals"]["clean_triangle_count"],
        "mesh_bytes": report["totals"]["clean_mesh_bytes"],
        "post_clean_invalid_faces": report["totals"]["post_clean_invalid_faces"],
        "failures": failures,
        "report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2), flush=True)
    raise SystemExit(0 if report["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
