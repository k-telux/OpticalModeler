#!/usr/bin/env python3
"""Strip risky PNG metadata while preserving encoded and decoded pixel data."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


SIGNATURE = b"\x89PNG\r\n\x1a\n"
FORBIDDEN = {b"tEXt", b"iTXt", b"zTXt", b"eXIf"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitize(path: Path) -> dict[str, object]:
    source = path.read_bytes()
    if not source.startswith(SIGNATURE):
        raise ValueError(f"not a PNG: {path}")
    position = len(SIGNATURE)
    kept = bytearray(SIGNATURE)
    idat_before = bytearray()
    removed: dict[str, int] = {}
    ihdr = b""
    saw_iend = False
    while position < len(source):
        if position + 12 > len(source):
            raise ValueError(f"truncated PNG chunk header: {path}")
        length = struct.unpack(">I", source[position : position + 4])[0]
        chunk_type = source[position + 4 : position + 8]
        end = position + 12 + length
        if end > len(source):
            raise ValueError(f"truncated PNG chunk: {path}")
        payload = source[position + 8 : position + 8 + length]
        expected_crc = struct.unpack(">I", source[position + 8 + length : end])[0]
        actual_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(f"bad PNG CRC: {path} {chunk_type!r}")
        if chunk_type == b"IHDR":
            ihdr = payload
        if chunk_type == b"IDAT":
            idat_before.extend(payload)
        if chunk_type in FORBIDDEN:
            name = chunk_type.decode("ascii")
            removed[name] = removed.get(name, 0) + 1
        else:
            kept.extend(source[position:end])
        position = end
        if chunk_type == b"IEND":
            saw_iend = True
            break
    if not saw_iend or position != len(source) or not ihdr or not idat_before:
        raise ValueError(f"incomplete PNG: {path}")
    decoded_before = zlib.decompress(bytes(idat_before))
    output = bytes(kept)
    path.write_bytes(output)

    idat_after = bytearray()
    position = len(SIGNATURE)
    while position < len(output):
        length = struct.unpack(">I", output[position : position + 4])[0]
        chunk_type = output[position + 4 : position + 8]
        payload = output[position + 8 : position + 8 + length]
        if chunk_type == b"IDAT":
            idat_after.extend(payload)
        position += 12 + length
    decoded_after = zlib.decompress(bytes(idat_after))
    if idat_before != idat_after or decoded_before != decoded_after:
        raise RuntimeError(f"pixel payload changed: {path}")
    return {
        "path": path.as_posix(),
        "before_sha256": digest(source),
        "after_sha256": digest(output),
        "before_bytes": len(source),
        "after_bytes": len(output),
        "removed_chunks": removed,
        "ihdr_sha256": digest(ihdr),
        "idat_sha256": digest(bytes(idat_after)),
        "decoded_scanline_sha256": digest(decoded_after),
        "pixel_data_unchanged": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", type=Path)
    args = parser.parse_args()
    reports = [sanitize(path.resolve()) for path in args.paths]
    print(json.dumps(reports, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
