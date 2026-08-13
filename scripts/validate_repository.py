#!/usr/bin/env python3
"""Validate the public skill repository with the Python standard library."""

from __future__ import annotations

import hashlib
import json
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    ROOT / "skills/thorlabs-blender-optical-path/SKILL.md": "thorlabs-blender-optical-path",
    ROOT / "i18n/zh-CN/SKILL.md": "thorlabs-blender-optical-path-zh",
    ROOT / "i18n/ja/SKILL.md": "thorlabs-blender-optical-path-ja",
}
REQUIRED = [
    ROOT / "LICENSE",
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "README.ja.md",
    ROOT / "rules/OPTICAL_PATH_PROJECT_MEMORY_TEMPLATE.md",
    ROOT / "examples/g1g2/input/fig_s17_componentlibrary_g1g2.png",
    ROOT / "examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg",
    ROOT / "examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg",
    ROOT / "examples/g1g2/evidence/v18_nature_final_acceptance.json",
    ROOT / "examples/forward-tests/README.md",
    ROOT / "examples/forward-tests/RESULTS.json",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/RUN_SPEC.json",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/WORKFLOW_STATE.json",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/WORKFLOW_EVENTS.jsonl",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/README.md",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/RUNBOOK.md",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/stage-scripts/fetch_official_cad.py",
    ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay/stage-scripts/finalize_whole_system_run.py",
    ROOT / "skills/thorlabs-blender-optical-path/references/end-to-end-workflow.md",
    ROOT / "skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py",
]
PUBLIC_PACKAGES = [
    {
        "root": ROOT / "examples/forward-tests/n04-lightsheet",
        "manifest": "MANIFEST.json",
        "records": "entries",
        "path": "path",
        "bytes": "bytes",
        "extras": {"MANIFEST.json"},
    },
    {
        "root": ROOT / "examples/forward-tests/interferometer",
        "manifest": "MANIFEST.json",
        "records": "files",
        "path": "path",
        "bytes": "bytes",
        "extras": {"MANIFEST.json"},
    },
    {
        "root": ROOT / "examples/forward-tests/oct-clean-r2",
        "manifest": "MANIFEST.json",
        "records": "artifacts",
        "path": "path",
        "bytes": "byte_length",
        "extras": {"MANIFEST.json", "MANIFEST.sha256"},
    },
    {
        "root": ROOT / "examples/forward-tests/cad-conversion-clean-r2",
        "manifest": "PUBLIC_FILE_MANIFEST.json",
        "records": "entries",
        "path": "path",
        "bytes": "bytes",
        "extras": {"PUBLIC_FILE_MANIFEST.json", "MANIFEST.sha256"},
    },
]
FORBIDDEN_SUFFIXES = {".blend", ".blend1", ".blend2", ".step", ".stp", ".stl"}
FORBIDDEN_PNG_CHUNKS = {b"tEXt", b"iTXt", b"zTXt", b"eXIf"}
MAX_FILE_BYTES = 10 * 1024 * 1024
PRIVATE_PATH = re.compile(r"(?i)(?:[A-Z]:[\\/]+Users[\\/]+|/(?:Users|home)/[^/\s]+/)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_frontmatter(path: Path, expected_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert match, f"missing YAML frontmatter: {path}"
    block = match.group(1)
    name = re.search(r"(?m)^name:\s*(.+?)\s*$", block)
    description = re.search(r"(?m)^description:\s*(.+?)\s*$", block)
    assert name and name.group(1).strip('"') == expected_name, f"wrong name: {path}"
    assert description and len(description.group(1).strip()) >= 40, f"short description: {path}"


def check_markdown_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = target.strip().strip("<>").split("#", 1)[0]
        if not target or re.match(r"^(https?://|mailto:)", target):
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"broken link in {path}: {target}"


def check_private_paths(path: Path) -> None:
    data = path.read_bytes()
    candidates = {
        "byte/ASCII": data.decode("latin1"),
        "UTF-16LE": data.decode("utf-16le", errors="ignore"),
        "UTF-16BE": data.decode("utf-16be", errors="ignore"),
    }
    for encoding, text in candidates.items():
        assert not PRIVATE_PATH.search(text), f"private path ({encoding}): {path}"


def check_png(path: Path) -> None:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"), f"invalid PNG signature: {path}"
    position = 8
    chunks: list[bytes] = []
    idat = bytearray()
    while position < len(data):
        assert position + 12 <= len(data), f"truncated PNG chunk header: {path}"
        length = struct.unpack(">I", data[position : position + 4])[0]
        chunk_type = data[position + 4 : position + 8]
        end = position + 12 + length
        assert end <= len(data), f"truncated PNG chunk: {path}"
        payload = data[position + 8 : position + 8 + length]
        expected_crc = struct.unpack(">I", data[position + 8 + length : end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        assert actual_crc == expected_crc, f"bad PNG CRC: {path} {chunk_type!r}"
        assert chunk_type not in FORBIDDEN_PNG_CHUNKS, f"forbidden PNG metadata: {path} {chunk_type!r}"
        chunks.append(chunk_type)
        if chunk_type == b"IDAT":
            idat.extend(payload)
        position = end
        if chunk_type == b"IEND":
            break
    assert chunks and chunks[0] == b"IHDR", f"PNG missing first IHDR: {path}"
    assert chunks[-1] == b"IEND" and position == len(data), f"PNG missing final IEND: {path}"
    assert idat, f"PNG missing IDAT: {path}"
    try:
        zlib.decompress(bytes(idat))
    except zlib.error as exc:
        raise AssertionError(f"PNG IDAT decompression failed: {path}: {exc}") from exc


def check_manifest(package: dict[str, object]) -> int:
    package_root = package["root"]
    assert isinstance(package_root, Path) and package_root.is_dir(), f"missing package: {package_root}"
    manifest_path = package_root / str(package["manifest"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest[str(package["records"])]
    listed: set[str] = set()
    for record in records:
        relative = record[str(package["path"])]
        assert relative not in listed, f"duplicate manifest path: {manifest_path}: {relative}"
        listed.add(relative)
        target = package_root / relative
        assert target.is_file(), f"manifest target missing: {target}"
        assert target.stat().st_size == record[str(package["bytes"])], f"manifest size mismatch: {target}"
        assert sha256(target) == record["sha256"], f"manifest hash mismatch: {target}"
    actual = {path.relative_to(package_root).as_posix() for path in package_root.rglob("*") if path.is_file()}
    extras = package["extras"]
    assert isinstance(extras, set) and actual == listed | extras, f"manifest file-set mismatch: {manifest_path}"
    return len(listed)


def check_sanitization_report(report_path: Path) -> None:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "PASS", f"sanitization report is not PASS: {report_path}"
    for record in report["records"]:
        target = (report_path.parent / record["path"]).resolve()
        assert target.is_relative_to(ROOT), f"sanitization target escapes repository: {target}"
        assert target.is_file(), f"sanitization target missing: {target}"
        assert target.stat().st_size == record["public_bytes"], f"sanitization size mismatch: {target}"
        assert sha256(target) == record["public_sha256"], f"sanitization hash mismatch: {target}"
        assert record["pixel_data_unchanged"] is True, f"sanitization changed pixel data: {target}"


def check_forward_test_statuses() -> None:
    results = json.loads((ROOT / "examples/forward-tests/RESULTS.json").read_text(encoding="utf-8"))
    assert results["baseline"]["tag"] == "v1.0.0"
    assert results["baseline"]["peeled_commit"] == "048766250538f169d924c31bbdd39bf0c255c63f"
    tracks = {track["id"]: track for track in results["tracks"]}
    assert set(tracks) == {"n04-lightsheet", "interferometer", "oct-clean-r2", "cad-conversion-clean-r2"}

    n04 = json.loads((ROOT / "examples/forward-tests/n04-lightsheet/PUBLIC_EXAMPLE_GATE.json").read_text(encoding="utf-8"))
    assert (tracks["n04-lightsheet"]["gate_status"], tracks["n04-lightsheet"]["scope_status"], tracks["n04-lightsheet"]["final_status"]) == (
        n04["status"]["propagation_gate"], n04["status"]["model_scope"], n04["status"]["final_or_release"]
    )
    replay = json.loads((ROOT / "examples/forward-tests/n04-lightsheet/BUILD_PARAMS_RECOMPUTE_AUDIT.json").read_text(encoding="utf-8"))
    assert replay["status"] == "PASS" and replay["difference_paths"] == []
    n04_root = ROOT / "examples/forward-tests/n04-lightsheet"
    build_params = json.loads((n04_root / "BUILD_PARAMS.json").read_text(encoding="utf-8"))
    topology = json.loads((n04_root / "TOPOLOGY_MAP.json").read_text(encoding="utf-8"))
    expected_counts = {
        "nodes": len(build_params["nodes"]),
        "directed_edge_traversals": len(build_params["edges"]),
        "true_branch_points": len(build_params["branch_points"]),
    }
    assert expected_counts == {key: n04["counts"][key] for key in expected_counts}
    assert expected_counts == {key: topology["counts"][key] for key in expected_counts}
    assert len(topology["nodes"]) == expected_counts["nodes"]
    assert len(topology["edges"]) == expected_counts["directed_edge_traversals"]
    check_sanitization_report(n04_root / "SANITIZATION_REPORT.json")
    check_sanitization_report(ROOT / "examples/g1g2/evidence/public_png_sanitization.json")

    interferometer_root = ROOT / "examples/forward-tests/interferometer"
    interferometer = json.loads((interferometer_root / "VALIDATION_REPORT.json").read_text(encoding="utf-8"))
    assert tracks["interferometer"]["scope_status"] == "PARTIAL_SCOPED"
    assert interferometer["authoritative_saved_reopen_counts"]["zero_radius_ray_record_count"] == 32
    assert interferometer["authoritative_saved_reopen_counts"]["semantic_port_record_count"] == 497
    public_text = (interferometer_root / "README.md").read_text(encoding="utf-8") + (interferometer_root / "FULL_40_NODE_PROPAGATION_GATE.md").read_text(encoding="utf-8")
    assert "33 saved zero-radius" not in public_text and "504 CAD-port" not in public_text

    oct_matrix = json.loads((ROOT / "examples/forward-tests/oct-clean-r2/phase2/SCOPE_STATUS_MATRIX.json").read_text(encoding="utf-8"))
    assert tracks["oct-clean-r2"]["gate_status"] == oct_matrix["phase2_representative_smoke_gate"] == "UNVERIFIED"
    assert oct_matrix["propagation_authorized"] is False

    cad_gate = json.loads((ROOT / "examples/forward-tests/cad-conversion-clean-r2/GATE_DECISION.json").read_text(encoding="utf-8"))
    cad_validation = json.loads((ROOT / "examples/forward-tests/cad-conversion-clean-r2/VALIDATION.json").read_text(encoding="utf-8"))
    assert tracks["cad-conversion-clean-r2"]["gate_status"] == cad_gate["status"] == "BLOCKED"
    assert cad_validation["public_sanitization"]["status"] == "PASS"
    assert cad_validation["public_sanitization"]["binary_decode_skip_count"] == 0

    readme = (ROOT / "examples/forward-tests/README.md").read_text(encoding="utf-8")
    for track in tracks.values():
        assert track["id"] in readme, f"forward-test README omits {track['id']}"
        assert track["gate_status"] in readme, f"forward-test README omits status for {track['id']}"


def check_unified_workflow() -> None:
    root = ROOT / "examples/end-to-end-workflow/n04-v1.0.1-replay"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py"),
            "validate",
            "--spec",
            str(root / "RUN_SPEC.json"),
            "--state",
            str(root / "WORKFLOW_STATE.json"),
            "--events",
            str(root / "WORKFLOW_EVENTS.jsonl"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    summary = json.loads(result.stdout)
    assert summary["status"] == "PASS_LEDGER_INTEGRITY"
    assert summary["current_stage"] == "representative_smoke"
    assert summary["aggregate_status"] == "UNVERIFIED"
    assert summary["final_or_release"] is False
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-p", "test_workflow_ledger.py"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    assert tests.returncode == 0, tests.stderr or tests.stdout


def main() -> None:
    for path in REQUIRED:
        assert path.exists(), f"missing required file: {path.relative_to(ROOT)}"

    for path, expected_name in SKILLS.items():
        check_frontmatter(path, expected_name)

    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts and "__pycache__" not in path.parts
    ]
    png_count = 0
    for path in files:
        assert path.suffix.lower() not in FORBIDDEN_SUFFIXES, f"forbidden binary asset: {path}"
        assert path.stat().st_size <= MAX_FILE_BYTES, f"file exceeds 10 MiB: {path}"
        check_private_paths(path)
        if path.suffix.lower() == ".md":
            check_markdown_links(path)
        if path.suffix.lower() == ".png":
            check_png(path)
            png_count += 1

    manifest_entry_count = sum(check_manifest(package) for package in PUBLIC_PACKAGES)
    check_forward_test_statuses()
    check_unified_workflow()

    acceptance = json.loads((ROOT / "examples/g1g2/evidence/v18_nature_final_acceptance.json").read_text(encoding="utf-8"))
    assert acceptance["status"] == "PASS_V18_NATURE_FINAL_VERIFIED"
    assert acceptance["gates"]["p0_count"] == 0
    assert acceptance["gates"]["p1_count"] == 0
    print(
        f"PASS: {len(files)} files, {len(SKILLS)} skill editions, {png_count} sanitized PNGs, "
        f"{manifest_entry_count} forward-test manifest entries"
    )


if __name__ == "__main__":
    main()
