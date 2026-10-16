#!/usr/bin/env python3
"""Render the README catalog from the existing distribution registry."""

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN = "<!-- BEGIN REGISTRY CATALOG -->"
END = "<!-- END REGISTRY CATALOG -->"


def cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(registry):
    lines = [BEGIN, "", "| 类型 | 内容与版本 | 什么时候用 |", "| --- | --- | --- |"]
    kinds = {"principle": "共同原则", "method": "工作方法", "guide": "同步说明"}
    for item in registry["documents"]:
        version = "随仓库 commit" if item["version"] == "git" else "v" + item["version"]
        link = f'[{cell(item["title"])}]({item["source"]}) · {version}'
        lines.append(f'| {kinds[item["kind"]]} | {link} | {cell(item["when_to_use"])} |')
    lines.extend(["", '<a id="已收录-skills"></a>', "", "以下 Skill 都按需安装。它们尚未单独编号，以固定 commit 和目录 SHA-256 识别版本；`list` 可查看校验值。", "", "| Skill | 用途与适用情况 | 必要前提 |", "| --- | --- | --- |"])
    for item in registry["skills"]:
        link = f'[`{item["name"]}`]({item["source"]}/SKILL.md)'
        purpose = cell(item["summary"] + " " + item["when_to_use"])
        prerequisites = "<br>".join(cell(value) for value in item["prerequisites"])
        lines.append(f"| {link} | {purpose} | {prerequisites} |")
    lines.extend(["", END])
    return "\n".join(lines)


def updated_readme(text, catalog):
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        raise ValueError("README must contain exactly one catalog marker pair")
    before, rest = text.split(BEGIN)
    old, after = rest.split(END)
    return before + catalog + after


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    registry = json.loads((ROOT / "portable-skill-registry.json").read_text(encoding="utf-8"))
    readme = ROOT / "README.md"
    original = readme.read_text(encoding="utf-8")
    updated = updated_readme(original, render(registry))
    if args.write:
        readme.write_text(updated, encoding="utf-8")
    elif updated != original:
        parser.exit(1, "README catalog is stale; run scripts/render_catalog.py --write\n")
    print("README catalog matches registry")


if __name__ == "__main__":
    main()
