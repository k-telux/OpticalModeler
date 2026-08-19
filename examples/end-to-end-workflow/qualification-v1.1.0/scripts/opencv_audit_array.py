#!/usr/bin/env python3
"""Role/visibility-only OpenCV gate for scaled N04 array renders."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(sys.argv[1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
BASE = ROOT / "work" / "array_scale"
EVIDENCE = BASE / "evidence"
RENDERS = EVIDENCE / "renders"
AUDITS = EVIDENCE / "audits"
AUDITS.mkdir(parents=True, exist_ok=True)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


records, annotated = [], []
for path in sorted(RENDERS.glob("CAM_ARRAY_*.png")):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"could not read {path}")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    edges = cv2.Canny(gray, 60, 160)
    cyan = cv2.inRange(hsv, np.array([80, 40, 70]), np.array([105, 255, 255]))
    orange = cv2.inRange(hsv, np.array([4, 80, 80]), np.array([30, 255, 255]))
    metrics = {
        "width_px": int(image.shape[1]),
        "height_px": int(image.shape[0]),
        "gray_mean": float(gray.mean()),
        "gray_stddev": float(gray.std()),
        "edge_fraction": float(np.count_nonzero(edges) / edges.size),
        "overexposed_fraction": float(np.count_nonzero(gray >= 250) / gray.size),
        "cyan_pixels": int(np.count_nonzero(cyan)),
        "orange_pixels": int(np.count_nonzero(orange)),
    }
    checks = {
        "resolution_exact": image.shape[1] == 1600 and image.shape[0] == 950,
        "not_blank": metrics["gray_stddev"] >= 18.0 and metrics["edge_fraction"] >= 0.001,
        "exposure_bounded": metrics["gray_mean"] >= 12.0 and metrics["overexposed_fraction"] <= 0.60,
        "optical_family_visible": metrics["cyan_pixels"] >= 20,
        "modeled_load_family_visible": metrics["orange_pixels"] >= 5,
    }
    status = "PASS" if all(checks.values()) else "BLOCKED"
    record = {"filename": path.name, "bytes": path.stat().st_size, "sha256": digest(path), "metrics": metrics, "checks": checks, "status": status}
    records.append(record)
    header = np.full((170, image.shape[1], 3), 24, np.uint8)
    lines = [
        f"OpenCV array visibility gate: {status}",
        path.name,
        f"mean={metrics['gray_mean']:.1f} std={metrics['gray_stddev']:.1f} edge={metrics['edge_fraction']:.4f} overexp={metrics['overexposed_fraction']:.4f}",
        f"cyan={metrics['cyan_pixels']} orange={metrics['orange_pixels']}",
        "Visibility evidence only; not optical, mechanical, or literal-performance proof.",
    ]
    for index, line in enumerate(lines):
        cv2.putText(header, line, (24, 32 + index * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (245, 245, 245), 1, cv2.LINE_AA)
    framed = np.vstack((header, image))
    cv2.rectangle(framed, (3, 170), (framed.shape[1] - 4, framed.shape[0] - 4), (30, 210, 30) if status == "PASS" else (20, 20, 230), 7)
    thumb_height = round(760 * framed.shape[0] / framed.shape[1])
    annotated.append(cv2.resize(framed, (760, thumb_height), interpolation=cv2.INTER_AREA))

if len(records) != 4:
    raise RuntimeError(f"expected four array renders, found {len(records)}")
sheet = np.vstack((np.hstack(annotated[:2]), np.hstack(annotated[2:])))
sheet_path = AUDITS / "N04_ARRAY_CONTACT_SHEET.png"
if not cv2.imwrite(str(sheet_path), sheet):
    raise RuntimeError("could not write array contact sheet")
failures = [record["filename"] for record in records if record["status"] != "PASS"]
report = {
    "schema": "opticalmodeler.n04-array-opencv-audit.v1",
    "status": "PASS" if not failures else "BLOCKED",
    "scope": "VISIBILITY_ONLY_NOT_GEOMETRY_OR_PERFORMANCE",
    "run_id": CONFIG["run_id"],
    "station_count": CONFIG["station_count"],
    "opencv_version": cv2.__version__,
    "numpy_version": np.__version__,
    "render_count": len(records),
    "records": records,
    "contact_sheet": {"relative_private_path": sheet_path.relative_to(ROOT).as_posix(), "bytes": sheet_path.stat().st_size, "sha256": digest(sheet_path), "width_px": sheet.shape[1], "height_px": sheet.shape[0]},
    "status_boundaries": {"model_scope": "PARTIAL_SCOPED", "literal_paper_multi_station_system": "BLOCKED_NOT_CLAIMED", "final_or_release": False},
    "failures": failures,
}
(EVIDENCE / "ARRAY_OPENCV_AUDIT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"status": report["status"], "render_count": len(records), "contact_sheet_sha256": report["contact_sheet"]["sha256"], "failures": failures}, indent=2))
raise SystemExit(report["status"] != "PASS")
