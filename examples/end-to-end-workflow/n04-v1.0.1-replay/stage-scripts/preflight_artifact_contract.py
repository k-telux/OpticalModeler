#!/usr/bin/env python3
"""Verify that every acquired input exists under the exact next-consumer key."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def check(path: Path, expected_bytes: int, expected_sha256: str, role: str, records: list, failures: list) -> None:
    actual = {"bytes": path.stat().st_size, "sha256": digest(path)} if path.is_file() else None
    status = "PASS" if actual == {"bytes": expected_bytes, "sha256": expected_sha256} else "BLOCKED"
    records.append({"role": role, "relative_path": path.as_posix(), "status": status, "expected_bytes": expected_bytes, "expected_sha256": expected_sha256, "actual": actual})
    if status != "PASS":
        failures.append({"role": role, "path": path.as_posix()})


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: preflight_artifact_contract.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    phase1 = root / "outputs" / "phase1_source_cad_topology_lock"
    work = root / "work" / "phase2_representative_smoke_r3"
    cache = root / "work" / "vendor_cad_cache"
    source = json.loads((phase1 / "SOURCE_LOCK.json").read_text(encoding="utf-8"))
    bundle_commit_path = phase1 / "SOURCE_BUNDLE_COMMIT.json"
    bundle_commit = json.loads(bundle_commit_path.read_text(encoding="utf-8")) if bundle_commit_path.is_file() else {}
    manifest = json.loads((phase1 / "CAD_MANIFEST.json").read_text(encoding="utf-8"))
    representative = json.loads((work / "measurements" / "REPRESENTATIVE_INPUT_LOCK.json").read_text(encoding="utf-8"))
    records, failures = [], []
    for locked in source["literature"]["files"]:
        check(phase1 / locked["relative_path"], locked["bytes"], locked["sha256"], "source_lock_artifact", records, failures)
    expected_bundle = [
        {"relative_path": item["relative_path"], "bytes": item["bytes"], "sha256": item["sha256"]}
        for item in sorted(source["literature"]["files"], key=lambda item: item["relative_path"])
    ]
    expected_root = hashlib.sha256(canonical(expected_bundle)).hexdigest()
    if not (
        bundle_commit.get("status") == "PASS"
        and bundle_commit.get("files") == expected_bundle
        and bundle_commit.get("bundle_root_sha256") == expected_root
        and bundle_commit.get("source_lock_sha256") == digest(phase1 / "SOURCE_LOCK.json")
    ):
        failures.append({"role": "source_bundle_commit", "path": bundle_commit_path.as_posix()})
    cad_keys = set()
    for product in manifest["records"]:
        for cad in product.get("cad_files", []):
            keys = (cad["original_filename"], f"{product['requested_part_number'].replace('/', '_')}__{cad['original_filename']}")
            for name in keys:
                identity = (name.casefold(), cad["sha256"])
                if identity in cad_keys:
                    continue
                cad_keys.add(identity)
                check(cache / name, cad["bytes"], cad["sha256"], "vendor_cad_consumer_key", records, failures)
    for locked in representative["official_drawing_files"]:
        check(work / "vendor_docs" / locked["filename"], locked["bytes"], locked["sha256"], "official_drawing_consumer_key", records, failures)
    report = {
        "schema": "opticalmodeler.artifact-contract-preflight.v1",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "SOURCE_CAD_DRAWING_PRODUCER_TO_NEXT_CONSUMER_KEYS",
        "source_artifact_count": len(source["literature"]["files"]),
        "source_bundle_root_sha256": expected_root,
        "vendor_cad_consumer_key_count": sum(record["role"] == "vendor_cad_consumer_key" for record in records),
        "official_drawing_consumer_key_count": len(representative["official_drawing_files"]),
        "records": records,
        "failures": failures,
    }
    output = work / "measurements" / "ARTIFACT_CONTRACT_PREFLIGHT.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "source_artifacts": report["source_artifact_count"], "vendor_cad_consumer_keys": report["vendor_cad_consumer_key_count"], "official_drawing_consumer_keys": report["official_drawing_consumer_key_count"], "failures": failures}, indent=2))
    raise SystemExit(report["status"] != "PASS")


if __name__ == "__main__":
    main()
