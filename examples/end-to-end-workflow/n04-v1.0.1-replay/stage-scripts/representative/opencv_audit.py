"""Deterministic role-specific OpenCV checks for the N04 representative renders."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import cv2
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bbox(mask: np.ndarray) -> list[int] | None:
    y, x = np.nonzero(mask)
    if not len(x):
        return None
    return [int(x.min()), int(y.min()), int(x.max()), int(y.max())]


def color_masks(image: np.ndarray) -> dict[str, np.ndarray]:
    blue, green, red = [channel.astype(np.int16) for channel in cv2.split(image)]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return {
        "red_axis": (red >= 170) & ((red - green) >= 18) & ((red - blue) >= 18),
        "cyan_optic": (green >= 60) & (blue >= 50) & ((green - red) >= 18) & ((blue - red) >= 12),
        "orange_non_thorlabs_fastener": (hsv[:, :, 0] <= 30) & (hsv[:, :, 1] >= 20) & (hsv[:, :, 2] >= 100),
    }


def image_statistics(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return {
        "width_px": int(image.shape[1]),
        "height_px": int(image.shape[0]),
        "gray_mean": float(gray.mean()),
        "gray_stddev": float(gray.std()),
        "gray_p01": float(np.percentile(gray, 1)),
        "gray_p99": float(np.percentile(gray, 99)),
        "intentional_dark_background_fraction_gray_le_5": float(np.mean(gray <= 5)),
        "highlight_fraction_gray_ge_250": float(np.mean(gray >= 250)),
    }


def annotate_label(image: np.ndarray, lines: list[str]) -> None:
    y = 30
    for line in lines:
        cv2.putText(image, line, (22, y), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (60, 255, 80), 2, cv2.LINE_AA)
        y += 27


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: opencv_audit.py ROOT")
    root = Path(sys.argv[1]).resolve()
    output = root / "outputs" / "phase2_representative_smoke_r3"
    render_dir = output / "renders"
    audit_dir = output / "audits"
    audit_dir.mkdir(parents=True, exist_ok=True)

    side_path = render_dir / "N04_representative_side.png"
    axial_path = render_dir / "N04_representative_axial.png"
    side = cv2.imread(str(side_path), cv2.IMREAD_COLOR)
    axial = cv2.imread(str(axial_path), cv2.IMREAD_COLOR)
    if side is None or axial is None:
        raise SystemExit("BLOCKED: one or both render files could not be decoded")

    side_masks = color_masks(side)
    axial_masks = color_masks(axial)
    side_y, side_x = np.ogrid[: side.shape[0], : side.shape[1]]
    # Role regions prevent the blue-gray table and warm ray highlight from being
    # mistaken for the optic or the explicitly non-Thorlabs generic fasteners.
    side_masks["red_axis"] &= side_y < 450
    side_masks["cyan_optic"] &= (side_y < 430) & (side_x >= 450) & (side_x <= 800)
    side_masks["orange_non_thorlabs_fastener"] &= (side_y > 500) & (side_x >= 350) & (side_x <= 950)
    side_stats = image_statistics(side)
    axial_stats = image_statistics(axial)

    side_metrics = {
        **side_stats,
        "red_axis_pixel_count": int(side_masks["red_axis"].sum()),
        "red_axis_bbox_px": bbox(side_masks["red_axis"]),
        "cyan_optic_pixel_count": int(side_masks["cyan_optic"].sum()),
        "cyan_optic_bbox_px": bbox(side_masks["cyan_optic"]),
        "orange_non_thorlabs_fastener_pixel_count": int(side_masks["orange_non_thorlabs_fastener"].sum()),
        "orange_non_thorlabs_fastener_bbox_px": bbox(side_masks["orange_non_thorlabs_fastener"]),
    }
    side_thresholds = {
        "resolution_exact_px": [1280, 900],
        "gray_stddev_min": 45.0,
        "highlight_fraction_max": 0.12,
        "red_axis_pixel_count_min": 1200,
        "cyan_optic_pixel_count_min": 5000,
        "orange_non_thorlabs_fastener_pixel_count_min": 1500,
    }
    side_checks = {
        "resolution": [side_stats["width_px"], side_stats["height_px"]] == side_thresholds["resolution_exact_px"],
        "dynamic_range": side_stats["gray_stddev"] >= side_thresholds["gray_stddev_min"],
        "highlight_control": side_stats["highlight_fraction_gray_ge_250"] <= side_thresholds["highlight_fraction_max"],
        "ray_axis_visible": side_metrics["red_axis_pixel_count"] >= side_thresholds["red_axis_pixel_count_min"],
        "optic_visible": side_metrics["cyan_optic_pixel_count"] >= side_thresholds["cyan_optic_pixel_count_min"],
        "modeled_fastener_color_key_visible": side_metrics["orange_non_thorlabs_fastener_pixel_count"] >= side_thresholds["orange_non_thorlabs_fastener_pixel_count_min"],
    }

    cyan_mask = (axial_masks["cyan_optic"].astype(np.uint8) * 255)
    cyan_mask = cv2.morphologyEx(cyan_mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    contours, _ = cv2.findContours(cyan_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest = max(contours, key=cv2.contourArea) if contours else None
    if largest is None:
        circle = {"center_px": None, "radius_px": 0.0, "contour_area_px2": 0.0, "fill_ratio": 0.0}
    else:
        area = float(cv2.contourArea(largest))
        (center_x, center_y), radius = cv2.minEnclosingCircle(largest)
        circle = {
            "center_px": [float(center_x), float(center_y)],
            "radius_px": float(radius),
            "contour_area_px2": area,
            "fill_ratio": float(area / (np.pi * radius * radius)) if radius else 0.0,
        }

    expected_center = np.array([axial.shape[1] / 2.0, axial.shape[0] / 2.0])
    detected_center = np.array(circle["center_px"] if circle["center_px"] else [-1e9, -1e9])
    circle_center_error = float(np.linalg.norm(detected_center - expected_center))
    yy, xx = np.ogrid[: axial.shape[0], : axial.shape[1]]
    central_roi = (xx - expected_center[0]) ** 2 + (yy - expected_center[1]) ** 2 <= 100**2
    central_red_count = int(np.sum(axial_masks["red_axis"] & central_roi))
    axial_metrics = {
        **axial_stats,
        "red_port_pixel_count_within_center_radius_100_px": central_red_count,
        "cyan_optic_pixel_count": int(axial_masks["cyan_optic"].sum()),
        "cyan_optic_circle": circle,
        "cyan_optic_circle_center_error_px": circle_center_error,
    }
    axial_thresholds = {
        "resolution_exact_px": [1280, 900],
        "gray_stddev_min": 45.0,
        "highlight_fraction_max": 0.03,
        "central_red_port_pixel_count_min": 300,
        "cyan_optic_pixel_count_min": 50000,
        "cyan_circle_radius_range_px": [180.0, 270.0],
        "cyan_circle_center_error_max_px": 20.0,
        "cyan_circle_fill_ratio_min": 0.80,
    }
    axial_checks = {
        "resolution": [axial_stats["width_px"], axial_stats["height_px"]] == axial_thresholds["resolution_exact_px"],
        "dynamic_range": axial_stats["gray_stddev"] >= axial_thresholds["gray_stddev_min"],
        "highlight_control": axial_stats["highlight_fraction_gray_ge_250"] <= axial_thresholds["highlight_fraction_max"],
        "semantic_port_centered_and_visible": central_red_count >= axial_thresholds["central_red_port_pixel_count_min"],
        "optic_visible": axial_metrics["cyan_optic_pixel_count"] >= axial_thresholds["cyan_optic_pixel_count_min"],
        "optic_radius": axial_thresholds["cyan_circle_radius_range_px"][0] <= circle["radius_px"] <= axial_thresholds["cyan_circle_radius_range_px"][1],
        "optic_centered": circle_center_error <= axial_thresholds["cyan_circle_center_error_max_px"],
        "optic_circularity": circle["fill_ratio"] >= axial_thresholds["cyan_circle_fill_ratio_min"],
    }

    side_overlay = side.copy()
    for mask_name, color in (("red_axis", (0, 0, 255)), ("cyan_optic", (255, 255, 0)), ("orange_non_thorlabs_fastener", (0, 165, 255))):
        box = bbox(side_masks[mask_name])
        if box:
            cv2.rectangle(side_overlay, (box[0], box[1]), (box[2], box[3]), color, 2)
    annotate_label(side_overlay, ["NODE N04 SIDE ROLE AUDIT", f"red ray px={side_metrics['red_axis_pixel_count']}", f"cyan optic px={side_metrics['cyan_optic_pixel_count']}", f"orange modeled-fastener px={side_metrics['orange_non_thorlabs_fastener_pixel_count']}"])
    side_overlay_path = audit_dir / "N04_side_opencv_audit.png"
    cv2.imwrite(str(side_overlay_path), side_overlay)

    axial_overlay = axial.copy()
    if circle["center_px"]:
        center_tuple = tuple(int(round(value)) for value in circle["center_px"])
        cv2.circle(axial_overlay, center_tuple, int(round(circle["radius_px"])), (60, 255, 80), 3)
        cv2.drawMarker(axial_overlay, center_tuple, (60, 255, 80), cv2.MARKER_CROSS, 24, 3)
    cv2.circle(axial_overlay, (int(expected_center[0]), int(expected_center[1])), 100, (0, 0, 255), 2)
    annotate_label(axial_overlay, ["NODE N04 AXIAL ROLE AUDIT", f"optic r={circle['radius_px']:.2f}px center err={circle_center_error:.2f}px", f"central red port px={central_red_count}", f"circle fill={circle['fill_ratio']:.3f}"])
    axial_overlay_path = audit_dir / "N04_axial_opencv_audit.png"
    cv2.imwrite(str(axial_overlay_path), axial_overlay)

    failures = [f"side:{name}" for name, passed in side_checks.items() if not passed]
    failures.extend(f"axial:{name}" for name, passed in axial_checks.items() if not passed)
    report = {
        "schema": "opticalmodeler.phase2.opencv-render-audit.v3",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "opencv_version": cv2.__version__,
        "method_note": "Color masks validate presentation overlays only; ray and clearance truth comes from REPRESENTATIVE_SMOKE_AUDIT.json.",
        "side": {"source_sha256": sha256(side_path), "metrics": side_metrics, "thresholds": side_thresholds, "checks": side_checks},
        "axial": {"source_sha256": sha256(axial_path), "metrics": axial_metrics, "thresholds": axial_thresholds, "checks": axial_checks},
        "audit_overlays": [
            {"relative_path": str(side_overlay_path.relative_to(output)).replace("\\", "/"), "sha256": sha256(side_overlay_path)},
            {"relative_path": str(axial_overlay_path.relative_to(output)).replace("\\", "/"), "sha256": sha256(axial_overlay_path)},
        ],
        "failures": failures,
    }
    report_path = output / "OPENCV_RENDER_AUDIT.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "failures": failures, "side_red_pixels": side_metrics["red_axis_pixel_count"], "axial_center_error_px": circle_center_error}, indent=2))
    raise SystemExit(0 if not failures else 2)


if __name__ == "__main__":
    main()
