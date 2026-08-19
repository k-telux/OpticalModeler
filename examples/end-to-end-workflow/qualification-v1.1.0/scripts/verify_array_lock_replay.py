#!/usr/bin/env python3
"""Recompute the array topology from frozen public topology and compare every field."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

from build_array_lock import namespace_station


ROOT = Path(sys.argv[1]).resolve()
CONFIG = json.loads((ROOT / "RUN_CONFIG.json").read_text(encoding="utf-8"))
PHASE1 = ROOT / "outputs" / "phase1_source_cad_topology_lock"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def differences(left: object, right: object, path: str = "") -> list[str]:
    if type(left) is not type(right):
        return [path or "/"]
    if isinstance(left, dict):
        paths = []
        for key in sorted(set(left) | set(right)):
            child = f"{path}/{key}"
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(differences(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [path + "/length"]
        paths = []
        for index, (a, b) in enumerate(zip(left, right)):
            paths.extend(differences(a, b, f"{path}/{index}"))
        return paths
    return [] if left == right else [path or "/"]


base = json.loads((PHASE1 / "TOPOLOGY_MAP.json").read_text(encoding="utf-8"))
expected = copy.deepcopy(base)
expected["schema"] = "opticalmodeler.n04-array-topology.v1"
expected["scope"] = "DETERMINISTIC_MULTI_STATION_WORKFLOW_QUALIFICATION_NOT_LITERAL_PAPER_SYSTEM"
expected["station_count"] = CONFIG["station_count"]
expected["station_spacing_m"] = CONFIG["station_spacing_m"]
expected["clearance_margin_m"] = CONFIG.get("clearance_margin_m", 0.25)
expected["base_topology_sha256"] = digest(PHASE1 / "TOPOLOGY_MAP.json")
expected["nodes"], expected["edges"], expected["branch_points"], expected["source_merges"] = [], [], [], []
for index in range(CONFIG["station_count"]):
    station = f"S{index + 1:02d}"
    expected["nodes"].extend(namespace_station(item, station) for item in base["nodes"])
    expected["edges"].extend(namespace_station(item, station) for item in base["edges"])
    expected["branch_points"].extend(namespace_station(item, station) for item in base["branch_points"])
    expected["source_merges"].extend(namespace_station(item, station) for item in base["source_merges"])
expected["counts"] = {key: value * CONFIG["station_count"] for key, value in base["counts"].items()}
expected["automatic_reciprocal_edge_generation"] = False
actual_path = PHASE1 / "ARRAY_TOPOLOGY_MAP.json"
actual = json.loads(actual_path.read_text(encoding="utf-8"))
diff = differences(expected, actual)
report = {
    "schema": "opticalmodeler.n04-array-lock-replay.v1",
    "status": "PASS" if not diff else "BLOCKED",
    "run_id": CONFIG["run_id"],
    "base_topology_sha256": digest(PHASE1 / "TOPOLOGY_MAP.json"),
    "actual_array_topology_sha256": digest(actual_path),
    "station_count": CONFIG["station_count"],
    "recomputed_nodes": len(expected["nodes"]),
    "recomputed_directed_edges": len(expected["edges"]),
    "difference_paths": diff,
    "automatic_reciprocal_edge_generation": False,
}
output = ROOT / "work" / "array_scale" / "evidence" / "ARRAY_LOCK_REPLAY.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
print(json.dumps(report, indent=2))
raise SystemExit(report["status"] != "PASS")
