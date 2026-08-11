from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import cv2


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "MANIFEST.json"

FORBIDDEN_EXTENSIONS = {
    ".step", ".stp", ".brep", ".iges", ".igs", ".obj", ".stl", ".ply",
    ".fbx", ".glb", ".gltf", ".usd", ".usda", ".usdc", ".dae", ".3mf",
    ".blend", ".blend1", ".zip", ".7z", ".rar", ".tar", ".gz", ".bz2", ".xz",
}
ALLOWED_EXTENSIONS = {".json", ".md", ".png", ".py", ".sha256"}
TEXT_EXTENSIONS = {".json", ".md", ".py", ".sha256"}
EXPECTED_RENDERS = {
    "evidence/render_top.png", "evidence/render_side.png",
    "evidence/render_axial.png", "evidence/render_cutaway.png",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_json(path: Path):
    def reject(value: str):
        raise ValueError(f"non-finite JSON value: {value}")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=reject)


def forbidden_magic(path: Path) -> str | None:
    head = path.read_bytes()[:512]
    stripped = head.lstrip()
    signatures = {
        b"BLENDER": "BLEND",
        b"glTF": "GLB",
        b"ply\n": "PLY",
        b"ply\r\n": "PLY",
        b"ISO-10303-21": "STEP",
        b"DBRep_DrawableShape": "BREP",
        b"PK\x03\x04": "ZIP",
        b"7z\xbc\xaf\x27\x1c": "7Z",
        b"Rar!\x1a\x07": "RAR",
        b"solid ": "ASCII_STL",
    }
    for signature, label in signatures.items():
        if head.startswith(signature) or stripped.startswith(signature):
            return label
    return None


def main() -> int:
    errors: list[str] = []
    manifest = strict_json(MANIFEST)
    artifacts = manifest.get("artifacts", [])
    manifest_paths = {item["path"] for item in artifacts}
    actual_paths = {
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*") if path.is_file()
    }
    expected_paths = manifest_paths | {"MANIFEST.json", "MANIFEST.sha256"}
    if actual_paths != expected_paths:
        errors.append(f"file-set mismatch missing={sorted(expected_paths-actual_paths)} extra={sorted(actual_paths-expected_paths)}")

    for item in artifacts:
        path = ROOT / item["path"]
        if not path.is_file():
            errors.append(f"missing artifact: {item['path']}")
            continue
        if sha256(path) != item["sha256"]:
            errors.append(f"hash mismatch: {item['path']}")
        if path.stat().st_size != item["byte_length"]:
            errors.append(f"size mismatch: {item['path']}")

    sidecar = (ROOT / "MANIFEST.sha256").read_text(encoding="ascii").strip().split()[0]
    if sidecar != sha256(MANIFEST):
        errors.append("MANIFEST.sha256 mismatch")

    private_dir_token = "phase2" + "_private"
    local_user_token = "te" + "lux"
    file_scheme = "file" + "://"
    absolute_path = re.compile(r"(?i)(?:(?<![A-Za-z])[A-Z]:[\\/]|" + re.escape(file_scheme) + r"|\\\\[A-Za-z0-9_.-]+[\\/])")
    uuid_token = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
    for rel in sorted(actual_paths):
        path = ROOT / rel
        suffix = path.suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            errors.append(f"extension outside allowlist: {rel}")
        if suffix in FORBIDDEN_EXTENSIONS:
            errors.append(f"forbidden extension: {rel}")
        magic = forbidden_magic(path)
        if magic and suffix != ".png":
            errors.append(f"forbidden magic {magic}: {rel}")
        if suffix in TEXT_EXTENSIONS:
            text = path.read_text(encoding="utf-8")
            if absolute_path.search(text):
                errors.append(f"absolute/private path text: {rel}")
            if private_dir_token in text:
                errors.append(f"private directory token: {rel}")
            if local_user_token in text.lower():
                errors.append(f"local username token: {rel}")
            if uuid_token.search(text):
                errors.append(f"task/session-like UUID token: {rel}")

    if manifest.get("phase2_representative_smoke_gate") != "UNVERIFIED":
        errors.append("gate verdict must remain UNVERIFIED")
    if manifest.get("audit_scope") != "PARTIAL_SCOPED":
        errors.append("audit scope drift")
    if manifest.get("private_context_reads") != 0:
        errors.append("private_context_reads drift")
    if manifest.get("public_vendor_cad_count") != 0 or manifest.get("public_derived_mesh_count") != 0 or manifest.get("public_blend_count") != 0:
        errors.append("public geometry exclusion count drift")
    if manifest.get("propagation_authorized") is not False:
        errors.append("propagation must remain unauthorized")

    topology = strict_json(ROOT / "phase2/REPRESENTATIVE_TOPOLOGY.json")
    expected_counts = {"role_node_count": 22, "physical_instance_count": 20, "edge_count": 36, "path_count": 7}
    for key, value in expected_counts.items():
        if topology.get(key) != value:
            errors.append(f"topology count drift: {key}")
    if topology.get("domain_counts") != {"guided_fiber": 10, "free_space_optical": 25, "electrical_data": 1}:
        errors.append("topology domain count drift")
    if topology.get("excluded_optional", {}).get("node_ids") != ["n22_frame_grabber", "n28_spectrometer_controller"]:
        errors.append("optional exclusion ID drift")
    if topology.get("deferred_required_full_graph", {}).get("node_ids") != [
        "n24_analog_output_daq", "n25_sample_galvo_driver", "n26_reference_galvo_driver",
        "n27_sld_controller", "n29_display_storage",
    ]:
        errors.append("required-deferred node ID drift")
    expected_returns = ["e08", "e09", "e10", "e11", "e12", "e13", "e20", "e21", "e22", "e26", "e27", "e28", "e29", "e30", "e31"]
    if topology.get("explicit_return_edges_with_inferred_reciprocal_evidence") != expected_returns:
        errors.append("explicit return-edge boundary drift")
    if topology.get("automatic_reciprocal_edge_generation") is not False:
        errors.append("automatic reciprocal inference must remain disabled")

    render_audit = strict_json(ROOT / "phase2/RENDER_OPENCV_AUDIT.json")
    if render_audit.get("status") != "PASS":
        errors.append("OpenCV audit not PASS")
    for rel in sorted(EXPECTED_RENDERS):
        image = cv2.imread(str(ROOT / rel), cv2.IMREAD_COLOR)
        if image is None or image.shape != (900, 1400, 3):
            errors.append(f"render decode/shape failure: {rel}")
        elif float(image.std()) < 8.0 or float(image.mean()) < 80.0:
            errors.append(f"render brightness/non-empty failure: {rel}")

    validation = strict_json(ROOT / "phase2/VALIDATION_REPORT.json")
    if validation.get("status") != "PASS":
        errors.append("public validation report not PASS")

    result = {
        "status": "PASS" if not errors else "BLOCKED",
        "artifact_count": len(artifacts),
        "manifest_sha256": sha256(MANIFEST),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
