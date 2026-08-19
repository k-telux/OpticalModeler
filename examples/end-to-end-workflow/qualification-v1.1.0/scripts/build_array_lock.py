#!/usr/bin/env python3
"""Freeze an independently namespaced repeated-station topology inside one run."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def namespace_station(value: object, station: str) -> object:
    if isinstance(value, list):
        return [namespace_station(item, station) for item in value]
    if not isinstance(value, dict):
        return value
    result = copy.deepcopy(value)
    for key, item in list(result.items()):
        if key in {"id", "node_id", "from_node", "to_node"} and isinstance(item, str) and (item.startswith("N") or item.startswith("E")):
            result[key] = f"{station}/{item}"
        elif key in {"branch_id", "support_template"} and isinstance(item, str):
            result[key] = f"{station}/{item}"
        else:
            result[key] = namespace_station(item, station)
    result.setdefault("station_id", station)
    return result


def write(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--stations", type=int, choices=range(2, 9), required=True)
    parser.add_argument("--spacing-m", type=float, required=True)
    parser.add_argument("--clearance-margin-m", type=float, default=0.25)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--writer-id", default="n04-array-single-writer")
    args = parser.parse_args()
    root = args.run_root.resolve()
    phase1 = root / "outputs" / "phase1_source_cad_topology_lock"
    topology_path = phase1 / "TOPOLOGY_MAP.json"
    topology = json.loads(topology_path.read_text(encoding="utf-8"))
    expanded = copy.deepcopy(topology)
    expanded["schema"] = "opticalmodeler.n04-array-topology.v1"
    expanded["scope"] = "DETERMINISTIC_MULTI_STATION_WORKFLOW_QUALIFICATION_NOT_LITERAL_PAPER_SYSTEM"
    expanded["station_count"] = args.stations
    expanded["station_spacing_m"] = args.spacing_m
    expanded["clearance_margin_m"] = args.clearance_margin_m
    expanded["base_topology_sha256"] = digest(topology_path)
    expanded["nodes"], expanded["edges"], expanded["branch_points"], expanded["source_merges"] = [], [], [], []
    for index in range(args.stations):
        station = f"S{index + 1:02d}"
        expanded["nodes"].extend(namespace_station(item, station) for item in topology["nodes"])
        expanded["edges"].extend(namespace_station(item, station) for item in topology["edges"])
        expanded["branch_points"].extend(namespace_station(item, station) for item in topology["branch_points"])
        expanded["source_merges"].extend(namespace_station(item, station) for item in topology["source_merges"])
    expanded["counts"] = {key: value * args.stations for key, value in topology["counts"].items()}
    expanded["automatic_reciprocal_edge_generation"] = False
    array_path = phase1 / "ARRAY_TOPOLOGY_MAP.json"
    write(array_path, expanded)
    config = {
        "schema": "opticalmodeler.n04-array-run-config.v1",
        "status": "PASS",
        "run_id": args.run_id,
        "writer_id": args.writer_id,
        "single_writer": True,
        "allow_module_stitching": False,
        "station_count": args.stations,
        "station_spacing_m": args.spacing_m,
        "clearance_margin_m": args.clearance_margin_m,
        "max_regeneration_attempts": 1,
        "base_nodes": topology["counts"]["nodes"],
        "base_directed_edges": topology["counts"]["directed_edge_traversals"],
        "total_nodes": expanded["counts"]["nodes"],
        "total_directed_edges": expanded["counts"]["directed_edge_traversals"],
        "array_topology_sha256": digest(array_path),
        "reuse_policy": {
            "verified_vendor_source_bytes": "ALLOWED_AFTER_CURRENT_RUN_HASH_AUDIT",
            "generated_meshes_blend_audits_state_events": "FORBIDDEN_CROSS_RUN_REUSE"
        }
    }
    write(root / "RUN_CONFIG.json", config)
    print(json.dumps({"status": "PASS", "stations": args.stations, "nodes": config["total_nodes"], "directed_edges": config["total_directed_edges"], "array_topology_sha256": config["array_topology_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
