#!/usr/bin/env python3
"""Lock official OCCT and Blender runtimes before any CAD conversion."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import platform
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PHASE2 = ROOT / "work" / "phase2"
DOWNLOADS = PHASE2 / "runtime-downloads"
OCCT_ROOT = PHASE2 / "runtime" / "occt" / "opencascade-8.0.0-vc14-64"
THIRD_ROOT = PHASE2 / "runtime" / "occt" / "3rdparty-vc14-64"
OCCT_STAGE = PHASE2 / "runtime" / "occt-stage" / "bin"
BLENDER_ROOT = PHASE2 / "runtime" / "blender" / "blender-4.5.12-windows-x64"

OCCT_ARCHIVE_SHA256 = "48fa1f384432b89a96f2c02f44ea7a034612111a891414486443d737918dfb50"
BLENDER_ARCHIVE_SHA256 = "317ef64e7a2c3cc79ec810c766ae9828aff865bea78039dc695b3f1118c34b4f"


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def binary_record(path: Path, public_path: str) -> dict[str, object]:
    return {"path": public_path, "bytes": path.stat().st_size, "sha256": sha256(path)}


def occt_environment() -> dict[str, str]:
    env = os.environ.copy()
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    env.update(
        {
            "PATH": os.pathsep.join((str(OCCT_STAGE), str(windows / "System32"), str(windows))),
            "CASROOT": str(OCCT_ROOT),
            "TCL_LIBRARY": str(THIRD_ROOT / "tcltk-8.6.15-x64" / "lib" / "tcl8.6"),
            "TK_LIBRARY": str(THIRD_ROOT / "tcltk-8.6.15-x64" / "lib" / "tk8.6"),
            "DRAWHOME": str(OCCT_ROOT / "src" / "DrawResources"),
            "DRAWDEFAULT": str(OCCT_ROOT / "src" / "DrawResources" / "DrawDefault"),
            "CSF_DrawPluginDefaults": str(OCCT_ROOT / "src" / "DrawResources"),
            "CSF_OCCTResourcePath": str(OCCT_ROOT / "src"),
            "CSF_SHMessage": str(OCCT_ROOT / "src" / "SHMessage"),
            "CSF_XSMessage": str(OCCT_ROOT / "src" / "XSMessage"),
            "CSF_StandardDefaults": str(OCCT_ROOT / "src" / "StdResource"),
            "CSF_PluginDefaults": str(OCCT_ROOT / "src" / "StdResource"),
            "CSF_XCAFDefaults": str(OCCT_ROOT / "src" / "StdResource"),
            "CSF_STEPDefaults": str(OCCT_ROOT / "src" / "XSTEPResource"),
            "CSF_LANGUAGE": "us",
            "MMGT_CLEAR": "1",
            "CSF_FPE": "0",
        }
    )
    return env


def main() -> int:
    occt_archive = DOWNLOADS / "occt-combined-release-no-pch.zip"
    blender_archive = DOWNLOADS / "blender-4.5.12-windows-x64.zip"
    if sha256(occt_archive) != OCCT_ARCHIVE_SHA256:
        raise SystemExit("OCCT archive hash mismatch")
    if sha256(blender_archive) != BLENDER_ARCHIVE_SHA256:
        raise SystemExit("Blender archive hash mismatch")

    version_header = (OCCT_ROOT / "inc" / "Standard_Version.hxx").read_text(encoding="utf-8")
    header_version = re.search(r'#define OCC_VERSION_COMPLETE "([^"]+)"', version_header).group(1)
    if header_version != "8.0.0":
        raise SystemExit("OCCT header version mismatch")

    origin_dirs = [
        OCCT_ROOT / "win64" / "vc14" / "bin",
        THIRD_ROOT / "tcltk-8.6.15-x64" / "bin",
        THIRD_ROOT / "freetype-2.13.3-x64" / "bin",
        THIRD_ROOT / "freeimage-3.18.0-x64" / "bin",
        THIRD_ROOT / "angle-gles2-2.1.0-vc14-64" / "bin",
        THIRD_ROOT / "tbb-2021.13.0-x64" / "bin",
        THIRD_ROOT / "vtk-9.4.1-x64" / "bin",
        THIRD_ROOT / "ffmpeg-3.3.4-64" / "bin",
        THIRD_ROOT / "jemalloc-vc14-64" / "bin",
        THIRD_ROOT / "openvr-1.14.15-64" / "bin" / "win64",
    ]
    stage_records: list[dict[str, object]] = []
    copy_matches = 0
    for staged in sorted(path for path in OCCT_STAGE.iterdir() if path.is_file()):
        record = binary_record(staged, f"occt-stage/bin/{staged.name}")
        candidates = [directory / staged.name for directory in origin_dirs if (directory / staged.name).is_file()]
        if not candidates or not any(sha256(candidate) == record["sha256"] for candidate in candidates):
            raise SystemExit(f"staged OCCT byte provenance mismatch: {staged.name}")
        copy_matches += 1
        stage_records.append(record)

    blender_records = [
        binary_record(path, f"blender/{path.relative_to(BLENDER_ROOT).as_posix()}")
        for path in sorted(BLENDER_ROOT.rglob("*"))
        if path.is_file() and path.suffix.casefold() in {".exe", ".dll", ".pyd"}
    ]
    windows = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    system_records = [
        binary_record(windows / "System32" / name, f"system/{name}")
        for name in ("KERNEL32.dll", "ntdll.dll", "ucrtbase.dll", "VCRUNTIME140.dll", "VCRUNTIME140_1.dll", "MSVCP140.dll")
    ]

    occt_probe = subprocess.run(
        [str(OCCT_STAGE / "DRAWEXE.exe"), "-b", "-f", str(PHASE2 / "scripts" / "occt_version_probe.tcl")],
        env=occt_environment(),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=True,
    ).stdout
    marker = re.search(r"PHASE2_OCCT_VERSION_BEGIN\s*(.*?)\s*PHASE2_OCCT_VERSION_END", occt_probe, re.S)
    if not marker or "Open CASCADE Technology 8.0.0" not in marker.group(1):
        raise SystemExit("OCCT runtime version probe mismatch")
    occt_version_probe = marker.group(1).strip().splitlines()

    blender_env = os.environ.copy()
    blender_env["PATH"] = os.pathsep.join((str(BLENDER_ROOT), str(windows / "System32"), str(windows)))
    blender_probe = subprocess.run(
        [str(BLENDER_ROOT / "blender.exe"), "--background", "--factory-startup", "--version"],
        env=blender_env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=True,
    ).stdout.strip().splitlines()
    if not blender_probe or "Blender 4.5.12 LTS" not in blender_probe[0]:
        raise SystemExit("Blender runtime version probe mismatch")

    all_records = sorted(stage_records + blender_records + system_records, key=lambda item: item["path"])
    manifest_text = "".join(f"{item['sha256']}  {item['path']}\n" for item in all_records)
    manifest_path = PHASE2 / "RUNTIME_BINARY_MANIFEST.sha256"
    manifest_path.write_text(manifest_text, encoding="utf-8", newline="\n")

    core_names = ("DRAWEXE.exe", "TKernel.dll", "TKXCAF.dll", "TKDESTEP.dll")
    core_occt = [item for item in stage_records if Path(str(item["path"])).name in core_names]
    core_blender = next(item for item in blender_records if item["path"] == "blender/blender.exe")
    lock = {
        "schema": "opticalmodeler.phase2_runtime_lock.v1",
        "status": "PASS",
        "locked_at_utc": utc_now(),
        "conversion_started_before_lock": False,
        "occt": {
            "version": header_version,
            "official_release_page": "https://github.com/Open-Cascade-SAS/OCCT/releases/tag/V8_0_0",
            "official_archive_url": "https://github.com/Open-Cascade-SAS/OCCT/releases/download/V8_0_0/occt-combined-release-no-pch.zip",
            "archive_bytes": occt_archive.stat().st_size,
            "archive_expected_sha256": OCCT_ARCHIVE_SHA256,
            "archive_actual_sha256": sha256(occt_archive),
            "version_probe": occt_version_probe,
            "isolated_stage_file_count": len(stage_records),
            "stage_bytes_matching_official_archive": copy_matches,
            "core_binaries": core_occt,
        },
        "blender": {
            "version": "4.5.12 LTS",
            "official_release_directory": "https://download.blender.org/release/Blender4.5/",
            "official_archive_url": "https://download.blender.org/release/Blender4.5/blender-4.5.12-windows-x64.zip",
            "official_sha256_url": "https://download.blender.org/release/Blender4.5/blender-4.5.12.sha256",
            "archive_bytes": blender_archive.stat().st_size,
            "archive_expected_sha256": BLENDER_ARCHIVE_SHA256,
            "archive_actual_sha256": sha256(blender_archive),
            "version_probe": blender_probe,
            "core_binary": core_blender,
        },
        "host_runtime": {
            "os": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "system_binary_count": len(system_records),
        },
        "binary_manifest": {
            "path": "RUNTIME_BINARY_MANIFEST.sha256",
            "entry_count": len(all_records),
            "sha256": sha256(manifest_path),
        },
        "environment_policy": "Isolated application-directory staging plus Windows system directories only; no ambient PATH entries are used by conversion subprocesses.",
    }
    (PHASE2 / "RUNTIME_LOCK.json").write_text(
        json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({"status": "PASS", "binary_entries": len(all_records), "occt_stage_files": len(stage_records), "blender_binaries": len(blender_records)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
