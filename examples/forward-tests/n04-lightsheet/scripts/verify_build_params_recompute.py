"""Prove that the published BUILD_PARAMS semantics are reconstructed by script."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


# Public replay must not mutate the candidate with an unmanifested __pycache__.
sys.dont_write_bytecode = True


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def semantic(value):
    if isinstance(value, dict):
        return {key: semantic(item) for key, item in value.items() if key != "generated_utc"}
    if isinstance(value, list):
        return [semantic(item) for item in value]
    return value


def digest_value(value) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def diff_paths(left, right, prefix="$") -> list[str]:
    if type(left) is not type(right):
        return [prefix]
    if isinstance(left, dict):
        paths = []
        for key in sorted(set(left) | set(right)):
            child = f"{prefix}.{key}"
            if key not in left or key not in right:
                paths.append(child)
            else:
                paths.extend(diff_paths(left[key], right[key], child))
        return paths
    if isinstance(left, list):
        if len(left) != len(right):
            return [prefix]
        paths = []
        for index, (a, b) in enumerate(zip(left, right)):
            paths.extend(diff_paths(a, b, f"{prefix}[{index}]"))
        return paths
    return [] if left == right else [prefix]


def main() -> None:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]
    base = root / "work" / "full_32_node_propagation_v3"
    script = Path(__file__).resolve().with_name("make_full_locks.py")
    packaged_build = Path(__file__).resolve().parent.parent / "BUILD_PARAMS.json"
    published_path = packaged_build if packaged_build.is_file() else base / "BUILD_PARAMS.json"
    published_target_kind = "PUBLIC_PACKAGE_BUILD_PARAMS" if published_path == packaged_build else "LOCK_STAGE_WORK_BUILD_PARAMS"

    spec = importlib.util.spec_from_file_location("full32_v3_lock_generator", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import lock generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    published = json.loads(published_path.read_text(encoding="utf-8"))
    _, _, recomputed = module.build_payloads(root, "RECOMPUTED_TIMESTAMP_IGNORED_BY_SEMANTIC_GATE")
    published_semantic = semantic(published)
    recomputed_semantic = semantic(recomputed)
    differences = diff_paths(published_semantic, recomputed_semantic)

    centers_published = {node["node_id"]: node["world_port_center_m"] for node in published["nodes"]}
    centers_recomputed = {node["node_id"]: node["world_port_center_m"] for node in recomputed["nodes"]}
    required = {
        "N30": [0.7125, -0.55, 0.125],
        "N31": [0.9625, -0.55, 0.125],
    }
    required_centers_match = all(
        centers_published[node_id] == expected and centers_recomputed[node_id] == expected
        for node_id, expected in required.items()
    )
    override_keys = sorted(recomputed.get("documented_port_center_overrides_m", {}))
    conditions = {
        "semantic_build_params_equal": not differences,
        "published_node_count_32": len(centers_published) == 32,
        "recomputed_node_count_32": len(centers_recomputed) == 32,
        "all_node_port_centers_equal": centers_published == centers_recomputed,
        "N30_N31_required_centers_match": required_centers_match,
        "documented_override_keys_exact": override_keys == ["N30", "N31"],
        "documented_override_count_2": recomputed["determinism"].get("documented_port_center_override_count") == 2,
        "manual_unlogged_transforms_zero": recomputed["determinism"].get("manual_unlogged_transforms") == 0,
    }
    status = "PASS" if all(conditions.values()) else "BLOCKED"
    report = {
        "schema": "opticalmodeler.full32.build-params-recompute-audit.v1",
        "status": status,
        "scope": "FULL_32_NODE_PROPAGATION_GATE_v3_LOCK_STAGE",
        "comparison": "Canonical JSON equality after recursively excluding generated_utc only",
        "published_target_kind": published_target_kind,
        "conditions": conditions,
        "difference_paths": differences,
        "make_full_locks_script_sha256": sha256(script),
        "published_build_params_sha256": sha256(published_path),
        "published_semantic_sha256": digest_value(published_semantic),
        "recomputed_semantic_sha256": digest_value(recomputed_semantic),
        "required_port_centers_m": required,
        "published_port_centers_m": centers_published,
        "recomputed_port_centers_m": centers_recomputed,
        "documented_port_center_overrides_m": recomputed["documented_port_center_overrides_m"],
        "literal_paper_performance": "BLOCKED",
        "final_or_release": "BLOCKED",
    }
    out_name = "BUILD_PARAMS_PUBLIC_RECOMPUTE_READBACK.json" if published_target_kind == "PUBLIC_PACKAGE_BUILD_PARAMS" else "BUILD_PARAMS_RECOMPUTE_AUDIT.json"
    out = base / "evidence" / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "audit": str(out), "semantic_sha256": report["published_semantic_sha256"]}, indent=2))
    if status != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
