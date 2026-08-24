#!/usr/bin/env python3
"""Check and install repository-owned portable Codex Skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
DEFAULT_REGISTRY = Path(__file__).with_name("portable-skill-registry.json")


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def tree_digest(root: Path) -> tuple[str, int]:
    """Return a deterministic digest and file count for a Skill tree."""
    if not root.is_dir():
        raise FileNotFoundError(root)
    digest = hashlib.sha256()
    count = 0
    for path in sorted(item for item in root.rglob("*") if item.is_file() and not _is_ignored(item)):
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
        count += 1
    return digest.hexdigest(), count


def load_registry(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0" or not isinstance(payload.get("skills"), list):
        raise ValueError("unsupported portable skill registry")
    return payload


def resolve_source(registry_path: Path, value: str) -> Path:
    if Path(value).is_absolute():
        raise ValueError("skill source must be relative to the registry")
    root = registry_path.parent.resolve()
    source = (root / value).resolve()
    if source == root or root not in source.parents:
        raise ValueError("skill source escapes the portable skill root")
    return source


def resolve_target(value: str) -> Path:
    return Path(os.path.expanduser(value)).resolve(strict=False)


def selected_skills(registry: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    skills = registry["skills"]
    if not names:
        return skills
    by_name = {item.get("name"): item for item in skills}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise ValueError(f"unknown skill: {', '.join(missing)}")
    return [by_name[name] for name in names]


def check_skill(registry_path: Path, item: dict[str, Any]) -> dict[str, Any]:
    name = item["name"]
    source = resolve_source(registry_path, item["source"])
    target = resolve_target(item["install_target"])
    if not source.is_dir() or not (source / "SKILL.md").is_file():
        return {"name": name, "status": "source_invalid", "source": str(source), "target": str(target)}
    source_digest, source_files = tree_digest(source)
    result: dict[str, Any] = {
        "name": name,
        "source": str(source),
        "target": str(target),
        "source_digest": source_digest,
        "source_files": source_files,
    }
    if target.is_symlink():
        result["status"] = "unsafe_target_symlink"
        return result
    if not target.exists():
        result["status"] = "missing"
        return result
    if not target.is_dir():
        result["status"] = "unsafe_target_not_directory"
        return result
    target_digest, target_files = tree_digest(target)
    result.update({"target_digest": target_digest, "target_files": target_files})
    result["status"] = "installed" if source_digest == target_digest else "drifted"
    return result


def install_skill(registry_path: Path, item: dict[str, Any]) -> dict[str, Any]:
    before = check_skill(registry_path, item)
    if before["status"] == "installed":
        return {**before, "action": "noop"}
    if before["status"] not in {"missing", "drifted"}:
        return {**before, "action": "blocked"}

    source = Path(before["source"])
    target = Path(before["target"])
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.installing-", dir=target.parent))
    backup: Path | None = None
    try:
        staged = temporary / target.name
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"))
        staged_digest, _ = tree_digest(staged)
        if staged_digest != before["source_digest"]:
            raise RuntimeError("staged skill digest mismatch")
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup = target.with_name(f".{target.name}.backup-{stamp}")
            if backup.exists():
                raise FileExistsError(backup)
            target.rename(backup)
        staged.rename(target)
        after = check_skill(registry_path, item)
        if after["status"] != "installed":
            raise RuntimeError("installed skill failed readback")
        return {**after, "action": "installed", "backup": str(backup) if backup else None}
    except Exception:
        if target.exists() and backup is not None:
            shutil.rmtree(target)
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "check", "install"))
    parser.add_argument("skills", nargs="*")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args()

    registry_path = args.registry.expanduser().resolve()
    try:
        registry = load_registry(registry_path)
        skills = selected_skills(registry, args.skills)
        if args.command == "list":
            results = [
                {
                    "name": item["name"],
                    "source": str(resolve_source(registry_path, item["source"])),
                    "target": str(resolve_target(item["install_target"])),
                    "required_for": item.get("required_for", []),
                }
                for item in skills
            ]
        elif args.command == "check":
            results = [check_skill(registry_path, item) for item in skills]
        else:
            results = [install_skill(registry_path, item) for item in skills]
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 3

    success = all(item.get("status", "installed") == "installed" for item in results)
    print(json.dumps({"status": "ready" if success else "attention_required", "skills": results}, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
