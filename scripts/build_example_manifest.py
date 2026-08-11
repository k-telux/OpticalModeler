#!/usr/bin/env python3
"""Build a deterministic self-excluding manifest for one public example."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", default="MANIFEST.json")
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / args.output
    entries = []
    for path in sorted(item for item in root.rglob("*") if item.is_file() and item != output):
        data = path.read_bytes()
        entries.append(
            {
                "path": path.relative_to(root).as_posix(),
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    payload = {
        "schema": "opticalmodeler.public-example-manifest.v1",
        "status": "PASS",
        "self_excluding": True,
        "entries": entries,
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
