"""Read-only diagnostic scan of candidate CAD-native mount aperture axes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(sys.argv[sys.argv.index("--") + 1]).resolve()
OUT = ROOT / "work" / "full_32_node_propagation_v3" / "evidence" / "MOUNT_APERTURE_PROBE.json"
PARTS = ("POLARIS-K1T2", "KM2536", "SM2RC/M", "LPSA5/M", "M2M25S", "SM1A9")


def hit_line(obj, origin, axis, lo, hi):
    start = origin.copy()
    start[axis] = lo
    direction = Vector((0.0, 0.0, 0.0))
    direction[axis] = 1.0
    return obj.ray_cast(start, direction, distance=hi - lo)[0]


def main():
    records = []
    for part in PARTS:
        obj = next(item for item in bpy.data.objects if item.get("part_number") == part)
        corners = [Vector(corner) for corner in obj.bound_box]
        minimum = [min(value[index] for value in corners) for index in range(3)]
        maximum = [max(value[index] for value in corners) for index in range(3)]
        center = [(minimum[index] + maximum[index]) / 2.0 for index in range(3)]
        axes = []
        for axis in range(3):
            perpendicular = [index for index in range(3) if index != axis]
            tests = []
            for label, candidate in (("origin", [0.0, 0.0, 0.0]), ("bbox_center", center)):
                tests.append({"label": label, "point": candidate, "hit": hit_line(obj, Vector(candidate), axis, minimum[axis] - 5.0, maximum[axis] + 5.0)})
            clear = []
            steps = 25
            for first in range(steps + 1):
                for second in range(steps + 1):
                    point = center.copy()
                    point[perpendicular[0]] = minimum[perpendicular[0]] + (maximum[perpendicular[0]] - minimum[perpendicular[0]]) * (0.15 + 0.70 * first / steps)
                    point[perpendicular[1]] = minimum[perpendicular[1]] + (maximum[perpendicular[1]] - minimum[perpendicular[1]]) * (0.15 + 0.70 * second / steps)
                    if not hit_line(obj, Vector(point), axis, minimum[axis] - 5.0, maximum[axis] + 5.0):
                        clear.append(point)
            if clear:
                clear_center = [sum(item[index] for item in clear) / len(clear) for index in range(3)]
                nearest_origin = min(clear, key=lambda item: sum(item[index] ** 2 for index in perpendicular))
                nearest_bbox = min(clear, key=lambda item: sum((item[index] - center[index]) ** 2 for index in perpendicular))
            else:
                clear_center = nearest_origin = nearest_bbox = None
            axes.append({
                "axis_index": axis, "axis_name": "XYZ"[axis], "direct_tests": tests,
                "interior_grid_clear_count": len(clear), "interior_grid_total": (steps + 1) ** 2,
                "clear_centroid": clear_center, "clear_nearest_native_origin": nearest_origin,
                "clear_nearest_bbox_center": nearest_bbox,
            })
        records.append({"part_number": part, "object_name": obj.name, "native_bbox": {"min": minimum, "max": maximum, "center": center}, "axes": axes})
    output = {"schema": "opticalmodeler.full32.mount-aperture-probe.v1", "status": "DIAGNOSTIC_ONLY", "records": records}
    OUT.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
