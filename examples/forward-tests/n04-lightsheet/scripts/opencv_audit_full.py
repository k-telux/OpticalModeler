"""Deterministic OpenCV quality audit for the full-32 propagation renders."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(sys.argv[1]).resolve()
BASE = ROOT / "work" / "full_32_node_propagation_v3"
RENDERS = BASE / "renders"
AUDITS = BASE / "audits"
EVIDENCE = BASE / "evidence"
SECOND_REOPEN = EVIDENCE / "GATE_BLEND_SECOND_REOPEN.json"
REPORT = EVIDENCE / "OPENCV_RENDER_AUDIT.json"

EXPECTED = {
    "FULL_32_overall_perspective.png": {
        "role": "bright overall perspective; table, frame, all major node groups",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 3000,
        "min_orange_pixels": 150,
    },
    "FULL_32_overall_top.png": {
        "role": "axial topology overview; node labels, table grid, branches",
        "max_overexposed_fraction": 0.52,
        "min_cyan_pixels": 8000,
        "min_orange_pixels": 200,
    },
    "FAMILY_source_launch.png": {
        "role": "S4FC488/S4FC637 launch and N01-N03 source conditioning",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 8000,
        "min_orange_pixels": 500,
    },
    "FAMILY_scanners_relay.png": {
        "role": "scanner and relay family N08-N11",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 15000,
        "min_orange_pixels": 150,
    },
    "FAMILY_branch_remote_relay.png": {
        "role": "branch and remote-relay family N19-N24",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 15000,
        "min_orange_pixels": 500,
    },
    "FAMILY_spectral_detector.png": {
        "role": "spectral split and detector family N27-N32",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 10000,
        "min_orange_pixels": 500,
    },
    "FAMILY_N04_reaudit.png": {
        "role": "N04 accepted-r3 root-transform propagation close-up",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 10000,
        "min_orange_pixels": 500,
    },
    "CRITICAL_N24_stage_load_path.png": {
        "role": "N24 LPS710E/M stage, modeled load links, LPSA5/M, and PF03 close-up",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 8000,
        "min_orange_pixels": 500,
    },
    "CRITICAL_E042_N31_first_hit.png": {
        "role": "E042 red-arm traversal and N31 BB1-E02/POLARIS target close-up",
        "max_overexposed_fraction": 0.35,
        "min_cyan_pixels": 500,
        "min_orange_pixels": 300,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def metric_record(path: Path, expected: dict) -> tuple[dict, np.ndarray]:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"OpenCV could not decode {path.name}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    edges = cv2.Canny(gray, 50, 150)
    cyan = cv2.inRange(hsv, np.array([75, 45, 60]), np.array([105, 255, 255]))
    orange = cv2.bitwise_or(
        cv2.inRange(hsv, np.array([0, 60, 70]), np.array([20, 255, 255])),
        cv2.inRange(hsv, np.array([170, 60, 70]), np.array([179, 255, 255])),
    )
    metrics = {
        "width_px": int(image.shape[1]),
        "height_px": int(image.shape[0]),
        "channels": int(image.shape[2]),
        "gray_mean": float(gray.mean()),
        "gray_stddev": float(gray.std()),
        "gray_p05": float(np.percentile(gray, 5)),
        "gray_p95": float(np.percentile(gray, 95)),
        "dynamic_range_p95_minus_p05": float(np.percentile(gray, 95) - np.percentile(gray, 5)),
        "overexposed_fraction_ge_250": float(np.mean(gray >= 250)),
        "dark_fraction_le_20": float(np.mean(gray <= 20)),
        "canny_edge_fraction": float(np.mean(edges > 0)),
        "cyan_component_pixels": int(np.count_nonzero(cyan)),
        "orange_modeled_support_pixels": int(np.count_nonzero(orange)),
    }
    checks = {
        "dimensions_1600x1000x3": metrics["width_px"] == 1600 and metrics["height_px"] == 1000 and metrics["channels"] == 3,
        "brightness_mean_70_to_235": 70.0 <= metrics["gray_mean"] <= 235.0,
        "contrast_stddev_at_least_30": metrics["gray_stddev"] >= 30.0,
        "dynamic_range_at_least_80": metrics["dynamic_range_p95_minus_p05"] >= 80.0,
        "edge_fraction_at_least_0_015": metrics["canny_edge_fraction"] >= 0.015,
        "overexposure_below_view_limit": metrics["overexposed_fraction_ge_250"] <= expected["max_overexposed_fraction"],
        "cyan_family_pixels_present": metrics["cyan_component_pixels"] >= expected["min_cyan_pixels"],
        "orange_modeled_support_pixels_present": metrics["orange_modeled_support_pixels"] >= expected["min_orange_pixels"],
    }
    status = "PASS" if all(checks.values()) else "BLOCKED"
    record = {
        "filename": path.name,
        "role": expected["role"],
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "metrics": metrics,
        "limits": {
            "max_overexposed_fraction": expected["max_overexposed_fraction"],
            "min_cyan_pixels": expected["min_cyan_pixels"],
            "min_orange_pixels": expected["min_orange_pixels"],
        },
        "checks": checks,
        "status": status,
    }
    return record, image


def annotated_image(image: np.ndarray, record: dict) -> np.ndarray:
    output = image.copy()
    color = (40, 200, 40) if record["status"] == "PASS" else (20, 20, 230)
    cv2.rectangle(output, (4, 4), (output.shape[1] - 5, output.shape[0] - 5), color, 8)
    lines = [
        f"OpenCV render-quality gate: {record['status']}",
        record["filename"],
        f"mean={record['metrics']['gray_mean']:.1f} std={record['metrics']['gray_stddev']:.1f} edge={record['metrics']['canny_edge_fraction']:.4f}",
        f"overexp={record['metrics']['overexposed_fraction_ge_250']:.4f} cyan={record['metrics']['cyan_component_pixels']} orange={record['metrics']['orange_modeled_support_pixels']}",
        "Quality/visibility evidence only; not optical or mechanical PASS.",
    ]
    y = 34
    for line in lines:
        cv2.putText(output, line, (24, y), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(output, line, (24, y), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (255, 255, 255), 1, cv2.LINE_AA)
        y += 30
    return output


def main() -> None:
    AUDITS.mkdir(parents=True, exist_ok=True)
    reopen = json.loads(SECOND_REOPEN.read_text(encoding="utf-8"))
    expected_hashes = {Path(item["relative_private_path"]).name: item["sha256"] for item in reopen["render_records"]}
    records = []
    thumbnails = []
    for filename, expected in EXPECTED.items():
        path = RENDERS / filename
        if not path.is_file():
            raise RuntimeError(f"missing required render {filename}")
        record, image = metric_record(path, expected)
        record["matches_second_reopen_hash"] = record["sha256"] == expected_hashes.get(filename)
        if not record["matches_second_reopen_hash"]:
            record["status"] = "BLOCKED"
        annotated = annotated_image(image, record)
        annotated_path = AUDITS / f"AUDIT__{filename}"
        if not cv2.imwrite(str(annotated_path), annotated):
            raise RuntimeError(f"could not write {annotated_path.name}")
        record["annotated_filename"] = annotated_path.name
        record["annotated_sha256"] = sha256(annotated_path)
        records.append(record)
        thumbnail = cv2.resize(annotated, (480, 300), interpolation=cv2.INTER_AREA)
        thumbnails.append(thumbnail)

    blank = np.full_like(thumbnails[0], 24)
    while len(thumbnails) < 9:
        thumbnails.append(blank.copy())
    rows = [np.hstack(thumbnails[index:index + 3]) for index in range(0, 9, 3)]
    sheet = np.vstack(rows)
    sheet_path = AUDITS / "FULL_32_RENDER_CONTACT_SHEET.png"
    if not cv2.imwrite(str(sheet_path), sheet):
        raise RuntimeError("could not write contact sheet")

    failures = [record["filename"] for record in records if record["status"] != "PASS"]
    report = {
        "schema": "opticalmodeler.full32.opencv-render-audit.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "RENDER_QUALITY_AND_ROLE_VISIBILITY_ONLY_NOT_GEOMETRY_OR_PERFORMANCE",
        "opencv_version": cv2.__version__,
        "numpy_version": np.__version__,
        "render_count": len(records),
        "records": records,
        "contact_sheet": {
            "filename": sheet_path.name,
            "width_px": int(sheet.shape[1]),
            "height_px": int(sheet.shape[0]),
            "sha256": sha256(sheet_path),
        },
        "status_boundaries": {
            "model_scope": "PARTIAL_SCOPED",
            "literal_paper_performance": "BLOCKED",
            "final_or_release": "BLOCKED",
            "final_or_release_reason": "AWAITING_SUPERVISOR_APPROVAL",
            "S4FC488_source_diagnostics": "PARTIAL_SCOPED",
            "S4FC637_source_diagnostics": "PARTIAL_SCOPED",
        },
        "failures": failures,
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise RuntimeError(f"OpenCV render gate failed: {failures}")
    print(json.dumps({
        "status": report["status"],
        "render_count": len(records),
        "contact_sheet_sha256": report["contact_sheet"]["sha256"],
        "report": str(REPORT.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2))


if __name__ == "__main__":
    main()
