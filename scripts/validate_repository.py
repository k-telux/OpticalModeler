#!/usr/bin/env python3
"""Validate the public skill repository with the Python standard library."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    ROOT / "skills/thorlabs-blender-optical-path/SKILL.md": "thorlabs-blender-optical-path",
    ROOT / "i18n/zh-CN/SKILL.md": "thorlabs-blender-optical-path-zh",
    ROOT / "i18n/ja/SKILL.md": "thorlabs-blender-optical-path-ja",
}
REQUIRED = [
    ROOT / "LICENSE",
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "README.ja.md",
    ROOT / "rules/OPTICAL_PATH_PROJECT_MEMORY_TEMPLATE.md",
    ROOT / "examples/g1g2/input/fig_s17_componentlibrary_g1g2.png",
    ROOT / "examples/g1g2/output/v18_nature_hero_graphite_final_4k_preview.jpg",
    ROOT / "examples/g1g2/output/v18_nature_complete_top_annotated_final_4k_preview.jpg",
    ROOT / "examples/g1g2/evidence/v18_nature_final_acceptance.json",
]
FORBIDDEN_SUFFIXES = {".blend", ".blend1", ".blend2", ".step", ".stp"}
MAX_FILE_BYTES = 10 * 1024 * 1024


def check_frontmatter(path: Path, expected_name: str) -> None:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    assert match, f"missing YAML frontmatter: {path}"
    block = match.group(1)
    name = re.search(r"(?m)^name:\s*(.+?)\s*$", block)
    description = re.search(r"(?m)^description:\s*(.+?)\s*$", block)
    assert name and name.group(1).strip('"') == expected_name, f"wrong name: {path}"
    assert description and len(description.group(1).strip()) >= 40, f"short description: {path}"


def check_markdown_links(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = target.strip().strip("<>").split("#", 1)[0]
        if not target or re.match(r"^(https?://|mailto:)", target):
            continue
        resolved = (path.parent / target).resolve()
        assert resolved.exists(), f"broken link in {path}: {target}"


def main() -> None:
    for path in REQUIRED:
        assert path.exists(), f"missing required file: {path.relative_to(ROOT)}"

    for path, expected_name in SKILLS.items():
        check_frontmatter(path, expected_name)

    files = [path for path in ROOT.rglob("*") if path.is_file() and ".git" not in path.parts]
    for path in files:
        assert path.suffix.lower() not in FORBIDDEN_SUFFIXES, f"forbidden binary asset: {path}"
        assert path.stat().st_size <= MAX_FILE_BYTES, f"file exceeds 10 MiB: {path}"
        if path.suffix.lower() in {".md", ".yml", ".yaml", ".json", ".cff"}:
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"[A-Za-z]:[\\/]Users[\\/]", text), f"private Windows path: {path}"
        if path.suffix.lower() == ".md":
            check_markdown_links(path)

    acceptance = json.loads((ROOT / "examples/g1g2/evidence/v18_nature_final_acceptance.json").read_text(encoding="utf-8"))
    assert acceptance["status"] == "PASS_V18_NATURE_FINAL_VERIFIED"
    assert acceptance["gates"]["p0_count"] == 0
    assert acceptance["gates"]["p1_count"] == 0
    print(f"PASS: {len(files)} files, {len(SKILLS)} skill editions, public example verified")


if __name__ == "__main__":
    main()
