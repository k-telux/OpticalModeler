#!/usr/bin/env python3
"""Download and hash-check the six official N04 assembly drawings."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


PARTS = ("T1225C", "BA1/M", "PH75/M", "TR75/M", "SM1RC/M", "AC254-045-A-ML")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_name(part: str) -> str:
    return "".join(character if character.isalnum() or character == "-" else "_" for character in part) + ".pdf"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_official_drawings.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    work = root / "work" / "phase2_representative_smoke_r3"
    manifest = json.loads((root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json").read_text(encoding="utf-8"))
    input_lock = json.loads((work / "measurements" / "REPRESENTATIVE_INPUT_LOCK.json").read_text(encoding="utf-8"))
    records = {item["requested_part_number"]: item for item in manifest["records"]}
    expected = {item["part_number"]: item for item in input_lock["official_drawing_files"]}
    output = work / "tmp" / "source_url_verify"
    output.mkdir(parents=True, exist_ok=True)
    results, failures = [], []

    for part in PARTS:
        catalog = records[part]["cad_pdfs"][0]
        lock = expected[part]
        urls = [catalog["source_url"], catalog.get("alternate_official_url")]
        path = urllib.parse.urlsplit(catalog["source_url"]).path
        urls.append("https://media.thorlabs.com" + path + ("?" + urllib.parse.urlsplit(catalog["source_url"]).query if urllib.parse.urlsplit(catalog["source_url"]).query else ""))
        attempts, accepted = [], None
        for url in dict.fromkeys(item for item in urls if item):
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "OpticalModeler-evidence-verifier/1.0"})
                with urllib.request.urlopen(request, timeout=60) as response:
                    data = response.read(10 * 1024 * 1024 + 1)
                    status = response.status
                digest = sha256(data)
                match = len(data) == lock["bytes"] and digest == lock["sha256"] and data.startswith(b"%PDF")
                attempts.append({"url": url, "http_status": status, "bytes": len(data), "sha256": digest, "status": "PASS" if match else "BLOCKED"})
                if match:
                    accepted = (url, data)
                    break
            except Exception as error:  # Network and TLS failures are evidence, not implicit success.
                attempts.append({"url": url, "status": "BLOCKED", "error_type": type(error).__name__})
        if accepted is None:
            failures.append(part)
            results.append({"part_number": part, "status": "BLOCKED", "attempts": attempts})
            continue
        destination = output / safe_name(part)
        temporary = destination.with_suffix(".pdf.part")
        temporary.write_bytes(accepted[1])
        os.replace(temporary, destination)
        results.append({"part_number": part, "status": "PASS", "accepted_url": accepted[0], "bytes": destination.stat().st_size, "sha256": sha256(destination.read_bytes()), "attempts": attempts})

    report = {
        "schema": "opticalmodeler.phase2.official-drawing-url-verification.v1",
        "status": "PASS" if not failures else "BLOCKED",
        "scope": "N04_REPRESENTATIVE_ONLY_R3",
        "verified_count": len(results) - len(failures),
        "failed_parts": failures,
        "records": results,
    }
    destination = work / "measurements" / "OFFICIAL_DRAWING_URL_VERIFY.json"
    destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "verified_count": report["verified_count"], "failed_parts": failures}, indent=2))
    raise SystemExit(bool(failures))


if __name__ == "__main__":
    main()
