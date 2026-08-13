"""Measure native CAD features for the approved N04 representative smoke.

The script is read-only with respect to phase 1 and vendor STEP inputs. It
records OpenCascade geometry in millimetres before any Blender placement.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.GeomAbs import GeomAbs_SurfaceType
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_ShapeEnum
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parents[2]
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
CACHE = ROOT / "work" / "vendor_cad_cache"
OUT = ROOT / "work" / "phase2_representative_smoke_r3" / "measurements"
PARTS = ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML")
TARGET_TABLE_NATIVE_MM = (112.5, -1087.5)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rounded(value: float, digits: int = 6) -> float:
    result = round(float(value), digits)
    return 0.0 if result == 0 else result


def vector(values) -> list[float]:
    result = [rounded(value) for value in values]
    for value in result:
        if abs(value) > 1e-9:
            if value < 0:
                result = [-item for item in result]
            break
    return result


def point(value) -> list[float]:
    return [rounded(value.X()), rounded(value.Y()), rounded(value.Z())]


def direction(value) -> list[float]:
    return vector((value.X(), value.Y(), value.Z()))


def bbox(shape) -> dict:
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    values = [float(value) for value in box.Get()]
    minimum = values[:3]
    maximum = values[3:]
    return {
        "min_mm": [rounded(value) for value in minimum],
        "max_mm": [rounded(value) for value in maximum],
        "size_mm": [rounded(maximum[index] - minimum[index]) for index in range(3)],
    }


def surface_record(face) -> dict:
    adaptor = BRepAdaptor_Surface(face, True)
    surface_type = adaptor.GetType()
    props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, props)
    record = {
        "area_mm2": rounded(props.Mass()),
        "bbox": bbox(face),
    }
    if surface_type == GeomAbs_SurfaceType.GeomAbs_Plane:
        plane = adaptor.Plane()
        record.update({
            "type": "PLANE",
            "origin_mm": point(plane.Location()),
            "normal": direction(plane.Axis().Direction()),
        })
    elif surface_type == GeomAbs_SurfaceType.GeomAbs_Cylinder:
        cylinder = adaptor.Cylinder()
        record.update({
            "type": "CYLINDER",
            "axis_origin_mm": point(cylinder.Axis().Location()),
            "axis_direction": direction(cylinder.Axis().Direction()),
            "radius_mm": rounded(cylinder.Radius()),
        })
    elif surface_type == GeomAbs_SurfaceType.GeomAbs_Sphere:
        sphere = adaptor.Sphere()
        record.update({
            "type": "SPHERE",
            "center_mm": point(sphere.Location()),
            "radius_mm": rounded(sphere.Radius()),
        })
    elif surface_type == GeomAbs_SurfaceType.GeomAbs_Cone:
        cone = adaptor.Cone()
        record.update({
            "type": "CONE",
            "axis_origin_mm": point(cone.Axis().Location()),
            "axis_direction": direction(cone.Axis().Direction()),
            "reference_radius_mm": rounded(cone.RefRadius()),
            "semi_angle_rad": rounded(cone.SemiAngle()),
        })
    else:
        record["type"] = str(surface_type).rsplit(".", 1)[-1].replace("GeomAbs_", "").upper()
    return record


def keep(part: str, feature: dict) -> bool:
    if part != "T1225C":
        if feature["type"] in {"CYLINDER", "SPHERE", "CONE"}:
            return True
        return feature["type"] == "PLANE" and feature["area_mm2"] >= 20.0

    if feature["type"] == "PLANE":
        return feature["area_mm2"] >= 100_000.0
    if feature["type"] != "CYLINDER":
        return False
    axis = feature["axis_direction"]
    radius = feature.get("radius_mm", 0.0)
    origin = feature["axis_origin_mm"]
    return (
        abs(axis[1]) > 0.9999
        and 2.0 <= radius <= 4.0
        and abs(origin[0] - TARGET_TABLE_NATIVE_MM[0]) <= 75.0
        and abs(origin[2] - TARGET_TABLE_NATIVE_MM[1]) <= 75.0
    )


def table_prefilter(face) -> bool:
    """Reject irrelevant T1225C faces before expensive area/bbox work."""
    adaptor = BRepAdaptor_Surface(face, True)
    surface_type = adaptor.GetType()
    if surface_type == GeomAbs_SurfaceType.GeomAbs_Cylinder:
        cylinder = adaptor.Cylinder()
        axis = direction(cylinder.Axis().Direction())
        origin = point(cylinder.Axis().Location())
        radius = cylinder.Radius()
        return (
            abs(axis[1]) > 0.9999
            and 2.0 <= radius <= 4.0
            and abs(origin[0] - TARGET_TABLE_NATIVE_MM[0]) <= 75.0
            and abs(origin[2] - TARGET_TABLE_NATIVE_MM[1]) <= 75.0
        )
    if surface_type == GeomAbs_SurfaceType.GeomAbs_Plane:
        plane = adaptor.Plane()
        normal = direction(plane.Axis().Direction())
        origin = point(plane.Location())
        return abs(normal[1]) > 0.9999 and (abs(origin[1]) < 0.01 or abs(origin[1] - 210.0) < 0.01)
    return False


def cache_path(part: str, original: str) -> Path:
    expected = f"{part.replace('/', '_')}__{original}".casefold()
    matches = [path for path in CACHE.iterdir() if path.name.casefold() == expected]
    if len(matches) != 1:
        raise RuntimeError(f"cache lookup for {part}/{original} returned {len(matches)} files")
    return matches[0]


def main() -> None:
    manifest = json.loads((PHASE1 / "CAD_MANIFEST.json").read_text(encoding="utf-8"))
    manifest_records = {record["requested_part_number"]: record for record in manifest["records"]}
    measured = []

    for part in PARTS:
        record = manifest_records[part]
        cad = record["cad_files"][0]
        source = cache_path(part, cad["original_filename"])
        actual_hash = sha256(source)
        if actual_hash != cad["sha256"]:
            raise RuntimeError(f"{part}: source STEP hash mismatch")

        reader = STEPControl_Reader()
        if reader.ReadFile(str(source)) != IFSelect_RetDone or reader.TransferRoots() < 1:
            raise RuntimeError(f"{part}: OpenCascade read/transfer failed")
        shape = reader.OneShape()
        if shape.IsNull():
            raise RuntimeError(f"{part}: OpenCascade returned a null shape")

        measured_bbox = bbox(shape)
        expected_size = cad["bbox"]["size"]
        if any(abs(measured_bbox["size_mm"][index] - expected_size[index]) > 0.002 for index in range(3)):
            raise RuntimeError(f"{part}: phase-1 bbox mismatch")

        features = []
        explorer = TopExp_Explorer(shape, TopAbs_ShapeEnum.TopAbs_FACE)
        while explorer.More():
            face = TopoDS.Face_s(explorer.Current())
            if part == "T1225C" and not table_prefilter(face):
                explorer.Next()
                continue
            feature = surface_record(face)
            if keep(part, feature):
                features.append(feature)
            explorer.Next()

        grouped = {}
        for feature in features:
            key = json.dumps(feature, sort_keys=True, separators=(",", ":"))
            grouped.setdefault(key, {"feature": feature, "occurrences": 0})["occurrences"] += 1
        unique_features = [value for _, value in sorted(grouped.items())]

        measured.append({
            "part_number": part,
            "source_step": {
                "original_filename": cad["original_filename"],
                "sha256": actual_hash,
                "bytes": source.stat().st_size,
            },
            "phase1_bbox_mm": cad["bbox"],
            "measured_bbox_mm": measured_bbox,
            "selected_native_features": unique_features,
        })

    result = {
        "schema": "opticalmodeler.phase2.representative-cad-features.v1",
        "status": "PASS",
        "scope": "N04_REPRESENTATIVE_ONLY",
        "unit": "millimetre",
        "placement_applied": False,
        "target_table_native_x_z_mm": list(TARGET_TABLE_NATIVE_MM),
        "parts": measured,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    destination = OUT / "REPRESENTATIVE_CAD_FEATURES.json"
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "part_count": len(measured),
        "feature_counts": {item["part_number"]: len(item["selected_native_features"]) for item in measured},
        "output": str(destination.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2))


if __name__ == "__main__":
    main()
