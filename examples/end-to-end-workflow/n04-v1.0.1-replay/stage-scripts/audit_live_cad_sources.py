#!/usr/bin/env python3
"""Compare current official CAD payloads with the pinned manifest without replacing either."""

from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

from fetch_official_cad import locked_files


def probe(item: dict) -> dict:
    attempts = []
    for url in item["urls"]:
        try:
            value = hashlib.sha256()
            byte_count = 0
            request = urllib.request.Request(url, headers={"User-Agent": "OpticalModeler-live-provenance-audit/1.1"})
            with urllib.request.urlopen(request, timeout=120) as response:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    value.update(chunk)
                    byte_count += len(chunk)
            actual = value.hexdigest()
            match = byte_count == item["bytes"] and actual == item["sha256"]
            return {
                "filename": item["filename"],
                "status": "PASS_PINNED_IDENTITY_MATCH" if match else "PARTIAL_SCOPED_SOURCE_DRIFT",
                "accepted_url": url,
                "pinned_bytes": item["bytes"],
                "pinned_sha256": item["sha256"],
                "current_bytes": byte_count,
                "current_sha256": actual,
                "gate_credit": match,
            }
        except Exception as error:
            attempts.append({"url": url, "error_type": type(error).__name__})
    return {"filename": item["filename"], "status": "BLOCKED_RETRIEVAL", "attempts": attempts, "gate_credit": False}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: audit_live_cad_sources.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    manifest_path = root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    started = time.perf_counter()
    records = []
    for index, item in enumerate(locked_files(manifest), 1):
        record = probe(item)
        records.append(record)
        print(f"[{index:02d}/{manifest['coverage']['official_step_files_hashed']:02d}] {item['filename']}: {record['status']}", flush=True)
    retrieval_failures = [record for record in records if record["status"] == "BLOCKED_RETRIEVAL"]
    drifts = [record for record in records if record["status"] == "PARTIAL_SCOPED_SOURCE_DRIFT"]
    status = "BLOCKED" if retrieval_failures else ("PARTIAL_SCOPED_SOURCE_DRIFT" if drifts else "PASS")
    report = {
        "schema": "opticalmodeler.live-cad-source-audit.v1",
        "status": status,
        "scope": "CURRENT_OFFICIAL_PAYLOAD_IDENTITY_ONLY_NOT_GEOMETRY_OR_SEMANTIC_INTERFACE",
        "expected_file_count": manifest["coverage"]["official_step_files_hashed"],
        "retrieved_file_count": len(records) - len(retrieval_failures),
        "pinned_identity_match_count": len(records) - len(retrieval_failures) - len(drifts),
        "source_drift_count": len(drifts),
        "retrieval_failure_count": len(retrieval_failures),
        "elapsed_seconds": time.perf_counter() - started,
        "gate_credit": status == "PASS",
        "records": records,
        "drifts": drifts,
        "retrieval_failures": retrieval_failures,
        "decision": "A drift does not invalidate historical cached bytes, but it blocks a current-catalog provenance PASS until a new run-specific lock and geometry audit are frozen.",
    }
    output = root / "work" / "vendor_cad_cache" / "CAD_LIVE_SOURCE_AUDIT.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({key: report[key] for key in ("status", "expected_file_count", "retrieved_file_count", "pinned_identity_match_count", "source_drift_count", "retrieval_failure_count", "gate_credit")}, indent=2))
    raise SystemExit(status != "PASS")


if __name__ == "__main__":
    main()
