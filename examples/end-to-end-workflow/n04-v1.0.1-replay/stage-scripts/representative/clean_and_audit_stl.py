"""Remove and gate zero-area/collinear triangles per representative CAD part.

Both source and cleaned STL files remain private vendor-CAD derivatives. Only the
counts, hashes, and bounding boxes are eligible for the public evidence package.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from pathlib import Path


PART_FILES = {
    "T1225C": "T1225C.stl",
    "BA1/M": "BA1_M.stl",
    "PH75/M": "PH75_M.stl",
    "TR75/M": "TR75_M.stl",
    "SM1RC/M": "SM1RC_M.stl",
    "AC254-045-A-ML": "AC254-045-A-ML.stl",
}

# Independent blocker attribution that this revision must reproduce exactly.
EXPECTED_IMPORTER_REMOVED_DUPLICATE_VERTEX_FACES = {
    "T1225C": 0,
    "BA1/M": 0,
    "PH75/M": 2,
    "TR75/M": 8,
    "SM1RC/M": 2,
    "AC254-045-A-ML": 0,
}
EXPECTED_KNOWN_RETAINED_COLLINEAR_MINIMUM = {"SM1RC/M": 1}

RECORD = struct.Struct("<12fH")
ABSOLUTE_DOUBLE_AREA_EPSILON_MM2 = 1e-12
NORMALIZED_COLLINEAR_EPSILON = 1e-12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        records.append({"raw": data[offset : offset + 50], "vertices": vertices, "classification": triangle_class(vertices)})
    return data[:80], records


def bbox(records) -> dict:
    coordinates = [vertex for item in records for vertex in item["vertices"]]
    minimum = [min(vertex[axis] for vertex in coordinates) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in coordinates) for axis in range(3)]
    return {"min_mm": minimum, "max_mm": maximum, "size_mm": [maximum[i] - minimum[i] for i in range(3)]}


def counts(records) -> dict:
    return {
        "triangle_count": len(records),
        "duplicate_vertex_faces": sum(item["classification"] == "duplicate_vertex" for item in records),
        "distinct_collinear_faces": sum(item["classification"] == "distinct_collinear" for item in records),
        "valid_faces": sum(item["classification"] == "valid" for item in records),
    }


def write_binary_stl(path: Path, records) -> None:
    header = b"OpticalModeler N04 r2 cleaned: zero-area and collinear faces removed"
    header = header[:80].ljust(80, b" ")
    with path.open("wb") as stream:
        stream.write(header)
        stream.write(struct.pack("<I", len(records)))
        for item in records:
            stream.write(item["raw"])


def max_bbox_error(first: dict, second: dict) -> float:
    return max(abs(first[key][axis] - second[key][axis]) for key in ("min_mm", "max_mm", "size_mm") for axis in range(3))


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: clean_and_audit_stl.py ROOT")
    root = Path(sys.argv[1]).resolve()
    work = root / "work" / "phase2_representative_smoke_r3"
    source_dir = work / "vendor_derivatives"
    clean_dir = work / "vendor_derivatives_clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    report_path = work / "measurements" / "STL_DEGENERATE_AUDIT.json"

    failures = []
    parts = []
    for part, filename in PART_FILES.items():
        source = source_dir / filename
        cleaned = clean_dir / filename
        _, source_records = read_binary_stl(source)
        before = counts(source_records)
        before_bbox = bbox(source_records)
        expected_duplicates = EXPECTED_IMPORTER_REMOVED_DUPLICATE_VERTEX_FACES[part]
        if before["duplicate_vertex_faces"] != expected_duplicates:
            failures.append(f"{part}: duplicate-vertex attribution mismatch")
        expected_collinear_minimum = EXPECTED_KNOWN_RETAINED_COLLINEAR_MINIMUM.get(part, 0)
        if before["distinct_collinear_faces"] < expected_collinear_minimum:
            failures.append(f"{part}: known retained collinear face was not reproduced")

        kept = [item for item in source_records if item["classification"] == "valid"]
        write_binary_stl(cleaned, kept)
        _, clean_records = read_binary_stl(cleaned)
        after = counts(clean_records)
        after_bbox = bbox(clean_records)
        bbox_error = max_bbox_error(before_bbox, after_bbox)
        if after["duplicate_vertex_faces"] or after["distinct_collinear_faces"]:
            failures.append(f"{part}: cleaned STL retains invalid faces")
        if bbox_error > 1e-6:
            failures.append(f"{part}: cleanup changed bbox by {bbox_error} mm")
        if after["triangle_count"] != before["triangle_count"] - before["duplicate_vertex_faces"] - before["distinct_collinear_faces"]:
            failures.append(f"{part}: triangle-count conservation failed")

        parts.append({
            "part_number": part,
            "status": "PASS" if not any(item.startswith(f"{part}:") for item in failures) else "BLOCKED",
            "pre_clean_private_derivative": {
                "relative_private_path": f"vendor_derivatives/{filename}",
                "sha256": sha256(source),
                "bytes": source.stat().st_size,
                "bbox": before_bbox,
                **before,
            },
            "post_clean_pre_import_private_derivative": {
                "relative_private_path": f"vendor_derivatives_clean/{filename}",
                "sha256": sha256(cleaned),
                "bytes": cleaned.stat().st_size,
                "bbox": after_bbox,
                **after,
            },
            "removed": {
                "duplicate_vertex_faces": before["duplicate_vertex_faces"],
                "distinct_collinear_faces": before["distinct_collinear_faces"],
                "total": before["duplicate_vertex_faces"] + before["distinct_collinear_faces"],
            },
            "bbox_max_error_after_cleanup_mm": bbox_error,
            "redistribution_decision": "EXCLUDE_FROM_PUBLIC_CANDIDATE",
        })

    report = {
        "schema": "opticalmodeler.phase2.representative-stl-degenerate-audit.v2",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "classification": {
            "duplicate_vertex_face": "at least one exactly zero-length edge in float32 STL coordinates",
            "distinct_collinear_face": "three distinct vertices with double-area <= 1e-12 mm^2 or normalized double-area <= 1e-12",
            "gate": "both counts must be zero after cleanup and again after saved-Blend reopen",
        },
        "expected_importer_removed_duplicate_vertex_faces": EXPECTED_IMPORTER_REMOVED_DUPLICATE_VERTEX_FACES,
        "known_retained_collinear_minimum": EXPECTED_KNOWN_RETAINED_COLLINEAR_MINIMUM,
        "parts": parts,
        "failures": failures,
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "removed_by_part": {item["part_number"]: item["removed"] for item in parts},
        "post_clean_invalid_faces": sum(item["post_clean_pre_import_private_derivative"]["duplicate_vertex_faces"] + item["post_clean_pre_import_private_derivative"]["distinct_collinear_faces"] for item in parts),
        "failures": failures,
    }, indent=2))
    raise SystemExit(0 if not failures else 2)


if __name__ == "__main__":
    main()
