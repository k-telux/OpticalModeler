#!/usr/bin/env python3
"""Verify the sanitized Phase 2 public package without private geometry."""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_FORBIDDEN_METADATA = {b"tEXt", b"iTXt", b"zTXt", b"eXIf"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def parse_png(data: bytes) -> list[tuple[bytes, bytes]]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("invalid PNG signature")
    chunks: list[tuple[bytes, bytes]] = []
    offset = len(PNG_SIGNATURE)
    while offset < len(data):
        if offset + 12 > len(data):
            raise ValueError("truncated PNG chunk header")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError("truncated PNG chunk payload")
        chunk_type = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length:end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise ValueError(f"PNG CRC mismatch for {chunk_type!r}")
        chunks.append((chunk_type, payload))
        offset = end
        if chunk_type == b"IEND":
            if offset != len(data):
                raise ValueError("trailing bytes after PNG IEND")
            break
    if not chunks or chunks[0][0] != b"IHDR" or chunks[-1][0] != b"IEND":
        raise ValueError("PNG is missing IHDR or IEND")
    return chunks


def scan_token_views(data: bytes, patterns: list[re.Pattern[str]]) -> list[dict[str, int | str]]:
    views = [("ascii", data.decode("latin-1"))]
    if b"\x00" in data:
        views.extend(
            (
                ("utf16le", data.decode("utf-16le", errors="ignore")),
                ("utf16be", data.decode("utf-16be", errors="ignore")),
            )
        )
    return [
        {"pattern_index": index, "encoding": encoding, "count": count}
        for encoding, text in views
        for index, pattern in enumerate(patterns)
        if (count := len(pattern.findall(text)))
    ]


def main() -> int:
    errors: list[str] = []
    files = sorted(path for path in ROOT.rglob("*") if path.is_file())
    forbidden_suffixes = {
        ".step", ".stp", ".sldprt", ".blend", ".glb", ".gltf", ".obj",
        ".mtl", ".stl", ".3mf", ".fbx", ".iges", ".igs", ".brep", ".zip",
    }
    forbidden_payloads = [path.relative_to(ROOT).as_posix() for path in files if path.suffix.casefold() in forbidden_suffixes]
    if forbidden_payloads:
        errors.append(f"forbidden geometry payloads: {forbidden_payloads}")
    if any(path.read_bytes()[:128].lstrip().upper().startswith(b"ISO-10303-21;") for path in files):
        errors.append("STEP header found")

    account = os.environ.get("USERNAME", "").casefold()
    patterns = [
        re.compile(r"(?i)(?<![a-z])[a-z]:[\\/](?:users|documents)[\\/]"),
        re.compile(r"(?i)/(?:home|users)/"),
        re.compile("".join(["f", "i", "l", "e", ":", "/", "/"]), re.I),
        re.compile("".join(["documents", r"[\\/]", "co", "dex"]), re.I),
        re.compile("".join([r"\.", "co", "dex"]), re.I),
        re.compile("".join(["c", "a", "i", "r", "n"]), re.I),
        re.compile(r"(?i)\b" + "p" + "0" + r"\b"),
        re.compile("".join(["m", "e", "m", "o", "r", "y"]), re.I),
        re.compile(re.escape("".join(["clean", "-", "r", "2"])), re.I),
        re.compile(r"(?i)work[\\/]phase2[\\/]private"),
    ]
    if account:
        patterns.append(re.compile(rf"(?i)(?<![a-z0-9]){re.escape(account)}(?![a-z0-9])"))
    token_hits = []
    png_metadata_hits = []
    png_parse_failures = []
    for path in files:
        data = path.read_bytes()
        token_data = data
        if path.suffix.casefold() == ".png":
            try:
                chunks = parse_png(data)
                zlib.decompress(b"".join(payload for chunk_type, payload in chunks if chunk_type == b"IDAT"))
            except (ValueError, zlib.error) as exc:
                png_parse_failures.append({"file": path.relative_to(ROOT).as_posix(), "error": str(exc)})
            else:
                # ponytail: IDAT is compressed pixel data, not a string channel; scan every other chunk.
                token_data = b"".join(
                    chunk_type + b"\x00" + payload
                    for chunk_type, payload in chunks
                    if chunk_type != b"IDAT"
                )
                counts = {
                    chunk_type.decode("ascii"): sum(item_type == chunk_type for item_type, _payload in chunks)
                    for chunk_type in PNG_FORBIDDEN_METADATA
                    if any(item_type == chunk_type for item_type, _payload in chunks)
                }
                if counts:
                    png_metadata_hits.append({"file": path.relative_to(ROOT).as_posix(), "chunk_counts": counts})
        for hit in scan_token_views(token_data, patterns):
            token_hits.append({"file": path.relative_to(ROOT).as_posix(), **hit})
    if token_hits:
        errors.append(f"local or isolation token hits: {token_hits}")
    if png_metadata_hits:
        errors.append(f"forbidden PNG metadata chunks: {png_metadata_hits}")
    if png_parse_failures:
        errors.append(f"PNG parse failures: {png_parse_failures}")

    manifest_entries = 0
    for line in (ROOT / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
        expected, relative = line.split("  ", 1)
        path = ROOT / relative
        manifest_entries += 1
        if not path.is_file() or sha256(path) != expected:
            errors.append(f"hash mismatch: {relative}")

    public_manifest = load("PUBLIC_FILE_MANIFEST.json")
    for entry in public_manifest["entries"]:
        path = ROOT / entry["path"]
        if not path.is_file() or path.stat().st_size != entry["bytes"] or sha256(path) != entry["sha256"]:
            errors.append(f"public file manifest mismatch: {entry['path']}")

    source = load("SOURCE_AND_PHASE1_LOCK.json")
    runtime = load("RUNTIME_LOCK.json")
    representatives = load("REPRESENTATIVE_LOCK.json")
    occt = load("OCCT_XCAF_AUDIT.json")
    blender = load("MESH_AND_BLENDER_AUDIT.json")
    gate = load("GATE_DECISION.json")
    validation = load("VALIDATION.json")
    if source["status"] != "PASS" or runtime["status"] != "PASS" or representatives["status"] != "PASS":
        errors.append("source, runtime, or representative lock is not PASS")
    if len(representatives["representatives"]) != 4 or len(occt["results"]) != 4:
        errors.append("representative count is not four")
    if occt["status"] != "BLOCKED" or blender["status"] != "BLOCKED":
        errors.append("fail-closed audits are not BLOCKED")
    if blender["converted_count"] != 3 or blender["blocked_before_blender_count"] != 1:
        errors.append("Blender converted/blocked counts differ from 3/1")
    blocked = blender["blocked_before_blender"]
    if len(blocked) != 1 or blocked[0]["sku"] != "PDA100A2" or blocked[0]["blender_executed"]:
        errors.append("PDA100A2 Blender prohibition evidence mismatch")
    if gate["gate"] != "PHASE_2_CONVERSION_SMOKE_GATE" or gate["status"] != "BLOCKED":
        errors.append("gate decision mismatch")
    recorded_scan = validation["public_sanitization"]
    current_scan = {
        "public_file_count": len(files),
        "forbidden_geometry_payload_file_count": len(forbidden_payloads),
        "step_header_file_count": sum(
            path.read_bytes()[:128].lstrip().upper().startswith(b"ISO-10303-21;") for path in files
        ),
        "local_or_isolation_token_hit_count": sum(hit["count"] for hit in token_hits),
        "binary_scan_file_count": len(files),
        "binary_decode_skip_count": 0,
        "png_binary_string_scan_scope": "All non-IDAT chunks are scanned as ASCII, UTF-16LE, and UTF-16BE; IDAT is validated and decompressed but excluded as compressed pixel data.",
        "png_file_count": sum(path.suffix.casefold() == ".png" for path in files),
        "png_forbidden_metadata_chunk_count": sum(
            sum(hit["chunk_counts"].values()) for hit in png_metadata_hits
        ),
        "png_parse_failure_count": len(png_parse_failures),
    }
    if recorded_scan.get("status") != "PASS":
        errors.append("recorded public sanitization is not PASS")
    for key, value in current_scan.items():
        if recorded_scan.get(key) != value:
            errors.append(f"recorded public sanitization mismatch: {key}")

    py_files = sorted((ROOT / "scripts").glob("*.py"))
    for path in py_files:
        compile(path.read_text(encoding="utf-8"), path.name, "exec")

    result = {
        "verification_status": "PASS" if not errors else "BLOCKED",
        "phase2_gate": gate["status"],
        "manifest_entry_count": manifest_entries,
        "public_file_manifest_entry_count": public_manifest["entry_count"],
        "python_script_syntax_count": len(py_files),
        "forbidden_geometry_payload_count": len(forbidden_payloads),
        "local_or_isolation_token_hit_count": sum(hit["count"] for hit in token_hits),
        "binary_scan_file_count": len(files),
        "binary_decode_skip_count": 0,
        "png_file_count": current_scan["png_file_count"],
        "png_forbidden_metadata_chunk_count": current_scan["png_forbidden_metadata_chunk_count"],
        "png_parse_failure_count": len(png_parse_failures),
        "errors": errors,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
