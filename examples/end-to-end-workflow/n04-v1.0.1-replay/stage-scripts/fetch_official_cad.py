#!/usr/bin/env python3
"""Fetch the manifest-locked official CAD into a private, non-redistributable cache."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def locked_files(manifest: dict) -> list[dict]:
    by_name: dict[str, dict] = {}
    for record in manifest["records"]:
        for cad in record.get("cad_files", []):
            assert cad["redistribution_decision"] == "EXCLUDE_FROM_PUBLIC_CANDIDATE"
            item = {
                "filename": cad["original_filename"],
                "cache_aliases": [f"{record['requested_part_number'].replace('/', '_')}__{cad['original_filename']}"],
                "bytes": cad["bytes"],
                "sha256": cad["sha256"],
                "urls": [
                    url
                    for url in (cad.get("source_url"), cad.get("catalog_asset_url"), cad.get("alternate_official_url"))
                    if url
                ],
            }
            previous = by_name.get(item["filename"].casefold())
            if previous:
                assert previous["bytes"] == item["bytes"] and previous["sha256"] == item["sha256"], (
                    f"conflicting locked CAD record: {item['filename']}"
                )
                previous["urls"] = list(dict.fromkeys(previous["urls"] + item["urls"]))
                previous["cache_aliases"] = list(dict.fromkeys(previous["cache_aliases"] + item["cache_aliases"]))
            else:
                by_name[item["filename"].casefold()] = item
    return sorted(by_name.values(), key=lambda item: item["filename"].casefold())


def valid(path: Path, item: dict) -> bool:
    return path.is_file() and path.stat().st_size == item["bytes"] and sha256(path) == item["sha256"]


def ensure_aliases(cache: Path, item: dict, destination: Path) -> list[str]:
    verified = []
    for name in item["cache_aliases"]:
        alias = cache / name
        if not valid(alias, item):
            partial = alias.with_suffix(alias.suffix + ".part")
            partial.unlink(missing_ok=True)
            try:
                os.link(destination, partial)
            except OSError:
                shutil.copyfile(destination, partial)
            if not valid(partial, item):
                partial.unlink(missing_ok=True)
                raise ValueError(f"cache alias bytes/hash mismatch: {name}")
            os.replace(partial, alias)
        verified.append(name)
    return verified


def fetch(cache: Path, item: dict) -> dict:
    destination = cache / item["filename"]
    if valid(destination, item):
        return {"filename": item["filename"], "status": "PASS", "source": "VERIFIED_EXISTING_CACHE", "verified_cache_aliases": ensure_aliases(cache, item, destination)}

    failures = []
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)
    aliases = [
        path
        for path in cache.iterdir()
        if path.is_file() and path.name.casefold().endswith("__" + item["filename"].casefold())
    ]
    for alias in aliases:
        if not valid(alias, item):
            continue
        try:
            os.link(alias, partial)
        except OSError:
            shutil.copyfile(alias, partial)
        os.replace(partial, destination)
        return {
            "filename": item["filename"],
            "status": "PASS",
            "source": "VERIFIED_EXISTING_CACHE_ALIAS",
            "alias": alias.name,
            "verified_cache_aliases": ensure_aliases(cache, item, destination),
        }

    for url in item["urls"]:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "OpticalModeler-public-workflow/1.0"})
            digest = hashlib.sha256()
            byte_count = 0
            with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    byte_count += len(chunk)
            if byte_count != item["bytes"] or digest.hexdigest() != item["sha256"]:
                raise ValueError(f"locked bytes/hash mismatch: {byte_count} {digest.hexdigest()}")
            os.replace(partial, destination)
            return {"filename": item["filename"], "status": "PASS", "source": url, "verified_cache_aliases": ensure_aliases(cache, item, destination)}
        except Exception as exc:  # Network and vendor mirrors are an external trust boundary.
            partial.unlink(missing_ok=True)
            failures.append({"url": url, "error": f"{type(exc).__name__}: {exc}"})
    return {"filename": item["filename"], "status": "BLOCKED", "failures": failures}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: fetch_official_cad.py <RUN_ROOT>")
    root = Path(sys.argv[1]).resolve()
    manifest_path = root / "outputs" / "phase1_source_cad_topology_lock" / "CAD_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cache = root / "work" / "vendor_cad_cache"
    cache.mkdir(parents=True, exist_ok=True)
    items = locked_files(manifest)
    records = []
    for index, item in enumerate(items, 1):
        record = fetch(cache, item)
        records.append(record)
        print(f"[{index:02d}/{len(items):02d}] {item['filename']}: {record['status']}", flush=True)
    failures = [record for record in records if record["status"] != "PASS"]
    expected = manifest["coverage"]["official_step_files_hashed"]
    report = {
        "schema": "opticalmodeler.official-cad-fetch-audit.v1",
        "status": "PASS" if not failures and len(items) == expected else "BLOCKED",
        "scope": "PRIVATE_VERIFIED_CACHE_ONLY",
        "manifest_relative_path": "outputs/phase1_source_cad_topology_lock/CAD_MANIFEST.json",
        "manifest_sha256": sha256(manifest_path),
        "expected_file_count": expected,
        "verified_file_count": len(records) - len(failures),
        "verified_cache_alias_count": sum(len(record.get("verified_cache_aliases", [])) for record in records),
        "redistribution": "BLOCKED_EXCLUDE_ALL_VENDOR_CAD",
        "records": records,
        "failures": failures,
    }
    write_json(cache / "CAD_FETCH_AUDIT.json", report)
    print(json.dumps({key: report[key] for key in ("status", "expected_file_count", "verified_file_count")}, indent=2))
    raise SystemExit(report["status"] != "PASS")


if __name__ == "__main__":
    main()
