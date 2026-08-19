#!/usr/bin/env python3
"""Materialize every SOURCE_LOCK literature byte record into one fresh run."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path


DOWNLOAD_OVERRIDES = {
    "literature/Dibaji2024_Fig1.png": "https://media.springernature.com/full/springer-static/image/art%3A10.1038%2Fs41467-024-49291-0/MediaObjects/41467_2024_49291_Fig1_HTML.png",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def valid(path: Path, record: dict) -> bool:
    return path.is_file() and path.stat().st_size == record["bytes"] and digest(path) == record["sha256"]


def atomic_copy(source: Path, target: Path, record: dict) -> str:
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.unlink(missing_ok=True)
    shutil.copyfile(source, temporary)
    if not valid(temporary, record):
        temporary.unlink(missing_ok=True)
        raise ValueError(f"source artifact copy mismatch: {record['relative_path']}")
    os.replace(temporary, target)
    return "VERIFIED_PUBLIC_PACKAGE_COPY"


def atomic_download(url: str, target: Path, record: dict) -> str:
    temporary = target.with_suffix(target.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OpticalModeler-public-workflow/1.1"})
    value = hashlib.sha256()
    byte_count = 0
    with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            value.update(chunk)
            byte_count += len(chunk)
    if byte_count != record["bytes"] or value.hexdigest() != record["sha256"]:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"source artifact download mismatch: {record['relative_path']}")
    os.replace(temporary, target)
    return url


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fetch_source_lock_artifacts.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    repository = Path(__file__).resolve().parents[4]
    phase1 = root / "outputs" / "phase1_source_cad_topology_lock"
    source_lock_path = phase1 / "SOURCE_LOCK.json"
    source_lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    commit_path = phase1 / "SOURCE_BUNDLE_COMMIT.json"
    commit_path.unlink(missing_ok=True)
    package = repository / "examples" / "forward-tests" / "n04-lightsheet"
    records, failures = [], []
    for locked in source_lock["literature"]["files"]:
        relative = Path(locked["relative_path"])
        destination = phase1 / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            if valid(destination, locked):
                source = "VERIFIED_EXISTING_RUN_INPUT"
            elif valid(package / relative, locked):
                source = atomic_copy(package / relative, destination, locked)
            else:
                url = DOWNLOAD_OVERRIDES.get(relative.as_posix(), locked["source_url"])
                source = atomic_download(url, destination, locked)
            records.append({"relative_path": relative.as_posix(), "status": "PASS", "source": source, "bytes": destination.stat().st_size, "sha256": digest(destination)})
        except Exception as error:
            failures.append({"relative_path": relative.as_posix(), "error_type": type(error).__name__, "error": str(error)})
    report = {
        "schema": "opticalmodeler.source-artifact-fetch-audit.v1",
        "status": "PASS" if not failures and len(records) == len(source_lock["literature"]["files"]) else "BLOCKED",
        "source_lock_sha256": digest(source_lock_path),
        "expected_file_count": len(source_lock["literature"]["files"]),
        "verified_file_count": len(records),
        "records": records,
        "failures": failures,
    }
    output = phase1 / "SOURCE_ARTIFACT_FETCH_AUDIT.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    if report["status"] == "PASS":
        bundle_records = [
            {"relative_path": record["relative_path"], "bytes": record["bytes"], "sha256": record["sha256"]}
            for record in sorted(records, key=lambda item: item["relative_path"])
        ]
        commit = {
            "schema": "opticalmodeler.source-bundle-commit.v1",
            "status": "PASS",
            "source_lock_sha256": digest(source_lock_path),
            "file_count": len(bundle_records),
            "files": bundle_records,
            "bundle_root_sha256": hashlib.sha256(canonical(bundle_records)).hexdigest(),
            "commit_semantics": "WRITTEN_LAST; ABSENCE_OR_MISMATCH_MAKES_BUNDLE_NONCONSUMABLE",
        }
        temporary = commit_path.with_suffix(".json.part")
        temporary.write_text(json.dumps(commit, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.replace(temporary, commit_path)
    print(json.dumps({"status": report["status"], "expected_file_count": report["expected_file_count"], "verified_file_count": report["verified_file_count"], "failures": failures}, indent=2))
    raise SystemExit(report["status"] != "PASS")


if __name__ == "__main__":
    main()
