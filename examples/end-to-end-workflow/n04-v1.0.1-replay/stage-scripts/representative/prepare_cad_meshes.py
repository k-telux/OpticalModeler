"""Create deterministic private STL derivatives for the N04 smoke scene."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.StlAPI import StlAPI_Writer
from OCP.gp import gp_Pnt


ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) == 2 else Path(__file__).resolve().parents[2]
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"
CACHE = ROOT / "work" / "vendor_cad_cache"
BASE = ROOT / "work" / "phase2_representative_smoke_r3"
MESH_DIR = BASE / "vendor_derivatives"
MEASUREMENTS = BASE / "measurements"
PARTS = ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bounds(shape) -> dict:
    box = Bnd_Box()
    BRepBndLib.Add_s(shape, box)
    values = [float(value) for value in box.Get()]
    minimum, maximum = values[:3], values[3:]
    return {
        "min_mm": minimum,
        "max_mm": maximum,
        "size_mm": [maximum[index] - minimum[index] for index in range(3)],
    }


def optimal_bounds(shape) -> dict:
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape, box, False, False)
    values = [float(value) for value in box.Get()]
    minimum, maximum = values[:3], values[3:]
    return {
        "min_mm": minimum,
        "max_mm": maximum,
        "size_mm": [maximum[index] - minimum[index] for index in range(3)],
        "method": "OpenCascade BRepBndLib.AddOptimal_s(useTriangulation=false,useShapeTolerance=false)",
    }


def cache_path(part: str, original: str) -> Path:
    expected = f"{part.replace('/', '_')}__{original}".casefold()
    matches = [path for path in CACHE.iterdir() if path.name.casefold() == expected]
    if len(matches) != 1:
        raise RuntimeError(f"cache lookup for {part}/{original} returned {len(matches)} files")
    return matches[0]


def read_step(path: Path):
    reader = STEPControl_Reader()
    if reader.ReadFile(str(path)) != IFSelect_RetDone or reader.TransferRoots() < 1:
        raise RuntimeError(f"OpenCascade failed to read {path.name}")
    shape = reader.OneShape()
    if shape.IsNull():
        raise RuntimeError(f"OpenCascade returned a null shape for {path.name}")
    return shape


def main() -> None:
    manifest = json.loads((PHASE1 / "CAD_MANIFEST.json").read_text(encoding="utf-8"))
    records = {record["requested_part_number"]: record for record in manifest["records"]}
    MESH_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for part in PARTS:
        cad = records[part]["cad_files"][0]
        source = cache_path(part, cad["original_filename"])
        if sha256(source) != cad["sha256"]:
            raise RuntimeError(f"{part}: source hash changed")
        source_shape = read_step(source)
        source_bbox = bounds(source_shape)
        source_bbox_optimal = optimal_bounds(source_shape)
        if any(abs(source_bbox["size_mm"][index] - cad["bbox"]["size"][index]) > 0.002 for index in range(3)):
            raise RuntimeError(f"{part}: source bbox changed")

        derivative_shape = source_shape
        operation = "FULL_OFFICIAL_CAD_SHAPE"
        if part == "T1225C":
            crop_box = BRepPrimAPI_MakeBox(gp_Pnt(-0.1, -0.1, -1200.1), 250.2, 210.2, 250.2).Shape()
            common = BRepAlgoAPI_Common(source_shape, crop_box)
            common.Build()
            if not common.IsDone() or common.Shape().IsNull():
                raise RuntimeError("T1225C OpenCascade crop failed")
            derivative_shape = common.Shape()
            operation = "OPENCASCADE_COMMON_WITH_PADDED_NATIVE_BOX_X_NEG0.1_250.1_Y_NEG0.1_210.1_Z_NEG1200.1_NEG949.9_MM"

        linear_deflection_mm = 0.15 if part == "T1225C" else (0.005 if part == "AC254-045-A-ML" else 0.03)
        angular_deflection_rad = 0.015 if part == "AC254-045-A-ML" else 0.12
        mesher = BRepMesh_IncrementalMesh(
            derivative_shape,
            linear_deflection_mm,
            False,
            angular_deflection_rad,
            True,
        )
        mesher.Perform()
        if not mesher.IsDone():
            raise RuntimeError(f"{part}: deterministic tessellation failed")

        filename = f"{part.replace('/', '_')}.stl"
        destination = MESH_DIR / filename
        writer = StlAPI_Writer()
        writer.ASCIIMode = False
        if not writer.Write(derivative_shape, str(destination)):
            raise RuntimeError(f"{part}: STL write failed")

        results.append({
            "part_number": part,
            "status": "PASS",
            "source_step": {
                "original_filename": cad["original_filename"],
                "sha256": cad["sha256"],
                "bytes": cad["bytes"],
                "source_bbox_conservative_mm": source_bbox,
                "source_bbox_optimal_mm": source_bbox_optimal,
            },
            "derivative": {
                "relative_private_path": f"vendor_derivatives/{filename}",
                "sha256": sha256(destination),
                "bytes": destination.stat().st_size,
                "bbox_conservative_mm": bounds(derivative_shape),
                "bbox_optimal_mm": optimal_bounds(derivative_shape),
                "operation": operation,
                "linear_deflection_mm": linear_deflection_mm,
                "angular_deflection_rad": angular_deflection_rad,
                "coordinate_unit": "millimetre",
                "redistribution_decision": "EXCLUDE_FROM_PUBLIC_CANDIDATE",
            },
        })

    output = {
        "schema": "opticalmodeler.phase2.cad-mesh-derivatives.v1",
        "status": "PASS",
        "scope": "N04_REPRESENTATIVE_ONLY",
        "vendor_geometry_public_output_count": 0,
        "parts": results,
    }
    destination = MEASUREMENTS / "CAD_MESH_DERIVATIVES.json"
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "part_count": len(results),
        "mesh_bytes": sum(record["derivative"]["bytes"] for record in results),
        "output": str(destination.relative_to(ROOT)).replace("\\", "/"),
    }, indent=2))


if __name__ == "__main__":
    main()
