#!/usr/bin/env python3
"""Validate, inspect, and safely install repository-owned portable Codex Skills."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


IGNORED_NAMES = {".DS_Store", "__pycache__"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
DEFAULT_REGISTRY = Path(__file__).with_name("portable-skill-registry.json")
STATE_DIRECTORY = ".portable-skill-manager"
NAME_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _is_ignored(path: Path) -> bool:
    return any(part in IGNORED_NAMES for part in path.parts) or path.suffix in IGNORED_SUFFIXES


def _absolute(path: Path) -> Path:
    """Normalize spelling without resolving (and therefore hiding) symlinks."""
    return Path(os.path.abspath(path.expanduser()))


def _no_symlinks(path: Path) -> None:
    for candidate in (*reversed(path.parents), path):
        if candidate.is_symlink():
            raise ValueError(f"symlink path is not allowed: {candidate}")


def _walk_error(error: OSError) -> None:
    raise error


def tree_digest(root: Path) -> tuple[str, int]:
    """Hash regular file names and bytes; reject symlinks, including ignored ones."""
    _no_symlinks(root)
    if not root.is_dir():
        raise FileNotFoundError(root)
    files = []
    for directory, dirs, names in os.walk(root, followlinks=False, onerror=_walk_error):
        parent = Path(directory)
        for name in dirs + names:
            path = parent / name
            if path.is_symlink():
                raise ValueError(f"symlink in Skill tree: {path}")
            if name in names:
                if not path.is_file():
                    raise ValueError(f"non-regular file in Skill tree: {path}")
                if not _is_ignored(path.relative_to(root)):
                    files.append(path)
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
        digest.update(b"\0")
    return digest.hexdigest(), len(files)


def _name(value: Any) -> str:
    if not isinstance(value, str) or len(value) > 64 or not NAME_PATTERN.fullmatch(value):
        raise ValueError(f"invalid registry name: {value!r}")
    return value


def _text(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{item.get('name', 'entry')}: {key} must be a nonempty string")
    return value


def _strings(item: dict[str, Any], key: str) -> None:
    value = item.get(key, [])
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{item['name']}: {key} must be an array of nonempty strings")


def load_registry(path: Path) -> dict[str, Any]:
    _no_symlinks(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != "1.0" or not isinstance(payload.get("skills"), list):
        raise ValueError("unsupported portable skill registry")
    seen: set[str] = set()
    for item in payload["skills"]:
        if not isinstance(item, dict):
            raise ValueError("every Skill entry must be an object")
        name = _name(item.get("name"))
        if name in seen:
            raise ValueError(f"duplicate Skill name: {name}")
        seen.add(name)
        if item.get("source") != f"skills/{name}":
            raise ValueError(f"{name}: source must be skills/{name}")
        if item.get("install_target") != f"~/.codex/skills/{name}":
            raise ValueError(f"{name}: install_target must be ~/.codex/skills/{name}")
        for key in ("summary", "when_to_use"):
            if key in item:
                _text(item, key)
        for key in ("required_for", "prerequisites"):
            _strings(item, key)
        if item.get("version_policy", "content-sha256") != "content-sha256":
            raise ValueError(f"{name}: unsupported version_policy")
    documents = payload.get("documents", [])
    if not isinstance(documents, list):
        raise ValueError("documents must be an array")
    seen_documents: set[str] = set()
    for item in documents:
        if not isinstance(item, dict):
            raise ValueError("every document entry must be an object")
        name = _name(item.get("name"))
        if name in seen_documents:
            raise ValueError(f"duplicate document name: {name}")
        seen_documents.add(name)
        for key in ("title", "version", "source", "when_to_use"):
            _text(item, key)
        if item.get("kind") not in {"principle", "method", "guide"} or item.get("sync") != "read-reference":
            raise ValueError(f"{name}: unsupported document kind or sync mode")
    return payload


def resolve_source(registry_path: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("source must be a repository-relative path")
    relative = Path(value)
    if relative.is_absolute() or any(part in {".", ".."} for part in value.split("/")):
        raise ValueError("source must stay inside the repository")
    root = _absolute(registry_path.parent)
    source = root / relative
    if source == root or root not in source.parents:
        raise ValueError("source escapes the repository")
    _no_symlinks(source)
    return source


def skills_root(skills_dir: Path | None = None) -> Path:
    if skills_dir is not None:
        root = skills_dir.expanduser()
    elif "CODEX_HOME" in os.environ:
        codex_home = Path(os.environ["CODEX_HOME"]).expanduser()
        if not os.environ["CODEX_HOME"] or not codex_home.is_absolute():
            raise ValueError("CODEX_HOME must be an absolute path")
        root = codex_home / "skills"
    else:
        root = Path.home() / ".codex" / "skills"
    if not root.is_absolute():
        raise ValueError("--skills-dir must be an absolute path")
    return _absolute(root)


def resolve_target(value: str, skills_dir: Path | None = None) -> Path:
    prefix = "~/.codex/skills/"
    if not isinstance(value, str) or not value.startswith(prefix):
        raise ValueError("registry target must be under ~/.codex/skills/")
    name = _name(value[len(prefix):])
    return skills_root(skills_dir) / name


def _backup_root(target: Path) -> Path:
    return target.parent.parent / f".{target.parent.name}.portable-skill-backups"


def _safe_target(source: Path, target: Path) -> None:
    _no_symlinks(target)
    repository = source.parent.parent
    if repository == target or repository in target.parents or target in repository.parents:
        raise ValueError("distribution repository and installation target overlap")
    if target.exists() and not target.is_dir():
        raise ValueError(f"installation target is not a directory: {target}")
    state = target.parent / STATE_DIRECTORY
    _no_symlinks(state / f"{target.name}.json")
    if state.exists() and not state.is_dir():
        raise ValueError(f"installation state is not a directory: {state}")
    backup_root = _backup_root(target)
    _no_symlinks(backup_root)
    if backup_root.exists() and not backup_root.is_dir():
        raise ValueError(f"backup root is not a directory: {backup_root}")


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---" or "---" not in lines[1:]:
        raise ValueError(f"missing Skill frontmatter: {path}")
    lines = lines[1:lines.index("---", 1)]
    result: dict[str, str] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^(name|description):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if key in result:
            raise ValueError(f"duplicate frontmatter {key}: {path}")
        if value in {"|", ">", "|-", ">-", "|+", ">+"}:
            block = []
            for continuation in lines[index + 1:]:
                if continuation and not continuation[0].isspace():
                    break
                block.append(continuation.strip())
            value = " ".join(block).strip()
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        result[key] = value.strip()
    if not result.get("name") or not result.get("description"):
        raise ValueError(f"Skill frontmatter requires name and description: {path}")
    return result


def _skill_summary(registry_path: Path, item: dict[str, Any]) -> dict[str, Any]:
    source = resolve_source(registry_path, item["source"])
    skill_file = source / "SKILL.md"
    _no_symlinks(skill_file)
    if not source.is_dir() or not skill_file.is_file():
        raise ValueError(f"{item['name']}: registered source is missing SKILL.md")
    if _frontmatter(skill_file)["name"] != item["name"]:
        raise ValueError(f"{item['name']}: frontmatter name differs from directory/registry")
    digest, count = tree_digest(source)
    return {**item, "source": str(source), "source_digest": digest, "source_files": count,
            "version": f"sha256:{digest}"}


def validate_repository(registry_path: Path, registry: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    directory = registry_path.parent / "skills"
    _no_symlinks(directory)
    actual = {p.name for p in directory.iterdir() if p.is_dir() or p.is_symlink()} if directory.exists() else set()
    expected = {item["name"] for item in registry["skills"]}
    if actual != expected:
        raise ValueError(f"Skill inventory mismatch; unregistered={sorted(actual - expected)}, missing={sorted(expected - actual)}")
    skills = [_skill_summary(registry_path, item) for item in registry["skills"]]
    documents = []
    for item in registry.get("documents", []):
        source = resolve_source(registry_path, item["source"])
        if not source.is_file():
            raise ValueError(f"{item['name']}: registered document is missing")
        content = source.read_bytes()
        if item["kind"] in {"principle", "method"}:
            heading = next((line[2:].strip() for line in content.decode("utf-8").splitlines() if line.startswith("# ")), "")
            expected_heading = f"{item['title']}｜v{item['version']}"
            if heading.replace(" | ", "｜").replace(" |", "｜").replace("| ", "｜") != expected_heading:
                raise ValueError(f"{item['name']}: document title/version does not match {expected_heading}")
        documents.append({**item, "source": str(source), "sha256": hashlib.sha256(content).hexdigest()})
    return skills, documents


def selected_skills(registry: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    by_name = {item["name"]: item for item in registry["skills"]}
    missing = [name for name in names if name not in by_name]
    if missing:
        raise ValueError(f"unknown skill: {', '.join(missing)}")
    return [by_name[name] for name in dict.fromkeys(names)] if names else registry["skills"]


def _receipt(target: Path) -> dict[str, Any] | None:
    path = target.parent / STATE_DIRECTORY / f"{target.name}.json"
    _no_symlinks(path)
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError):
        return None
    if (isinstance(value, dict) and value.get("schema_version") == "1.0"
            and value.get("name") == target.name and value.get("target") == str(target)
            and isinstance(value.get("source_digest"), str)
            and re.fullmatch(r"[a-f0-9]{64}", value["source_digest"])):
        return value
    return None


def check_skill(registry_path: Path, item: dict[str, Any], skills_dir: Path | None = None) -> dict[str, Any]:
    summary = _skill_summary(registry_path, item)
    source = Path(summary["source"])
    target = resolve_target(item["install_target"], skills_dir)
    result = {**summary, "target": str(target)}
    try:
        _safe_target(source, target)
        if not target.exists():
            return {**result, "status": "missing"}
        target_digest, target_files = tree_digest(target)
        receipt = _receipt(target)
    except ValueError as exc:
        status = "unsafe_target_symlink" if "symlink" in str(exc) else "unsafe_target"
        return {**result, "status": status, "reason": str(exc)}
    result.update({"target_digest": target_digest, "target_files": target_files,
                   "receipt_digest": receipt["source_digest"] if receipt else None})
    result["status"] = "installed" if summary["source_digest"] == target_digest else "drifted"
    result["update_allowed"] = receipt is not None and receipt["source_digest"] == target_digest
    return result


def _write_receipt(target: Path, digest: str) -> None:
    directory = target.parent / STATE_DIRECTORY
    path = directory / f"{target.name}.json"
    _no_symlinks(path)
    directory.mkdir(exist_ok=True)
    _no_symlinks(path)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=f".{target.name}-", dir=directory, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump({"schema_version": "1.0", "name": target.name, "target": str(target), "source_digest": digest}, handle)
            handle.write("\n")
        _no_symlinks(path)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _snapshot(result: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(result.get(key) for key in ("status", "source_digest", "target_digest", "receipt_digest"))


def install_skill(registry_path: Path, item: dict[str, Any], skills_dir: Path | None = None,
                  *, dry_run: bool = False, replace_local: bool = False) -> dict[str, Any]:
    before = check_skill(registry_path, item, skills_dir)
    if before["status"] == "installed":
        return {**before, "action": "noop", "dry_run": dry_run}
    if before["status"] not in {"missing", "drifted"}:
        return {**before, "action": "blocked", "dry_run": dry_run}
    if before["status"] == "drifted" and not before["update_allowed"] and not replace_local:
        return {**before, "action": "blocked", "dry_run": dry_run,
                "reason": "unknown or locally modified installation; compare it first, then explicitly use --replace-local if intended"}
    if dry_run:
        return {**before, "action": "would_install" if before["status"] == "missing" else "would_update", "dry_run": True}

    source, target = Path(before["source"]), Path(before["target"])
    _safe_target(source, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    _safe_target(source, target)
    temporary = Path(tempfile.mkdtemp(prefix=f".{target.name}.installing-", dir=target.parent))
    backup_container: Path | None = None
    backup: Path | None = None
    backup_moved = False
    installed_identity: tuple[int, int] | None = None
    try:
        staged = temporary / target.name
        shutil.copytree(source, staged, symlinks=True,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".DS_Store"))
        if tree_digest(staged)[0] != before["source_digest"]:
            raise RuntimeError("staged skill digest mismatch")
        current = check_skill(registry_path, item, target.parent)
        if _snapshot(current) != _snapshot(before):
            raise RuntimeError("source, target, or receipt changed while preparing installation; retry after comparison")
        _safe_target(source, target)
        if target.exists():
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_root = _backup_root(target)
            backup_root.mkdir(parents=True, exist_ok=True)
            _safe_target(source, target)
            backup_container = Path(tempfile.mkdtemp(prefix=f".{target.name}.backup-{stamp}-", dir=backup_root))
            backup = backup_container / target.name
            target.rename(backup)
            backup_moved = True
        identity = staged.stat()
        staged.rename(target)
        installed_identity = (identity.st_dev, identity.st_ino)
        after = check_skill(registry_path, item, target.parent)
        if after["status"] != "installed":
            raise RuntimeError("installed skill failed readback")
        _write_receipt(target, after["source_digest"])
        after.update({"receipt_digest": after["source_digest"], "update_allowed": True})
        return {**after, "action": "installed", "backup": str(backup) if backup else None, "dry_run": False}
    except Exception as exc:
        if installed_identity is not None and target.exists():
            _no_symlinks(target)
            identity = target.stat()
            if (identity.st_dev, identity.st_ino) != installed_identity:
                raise RuntimeError(f"target changed during rollback; original backup retained at {backup}") from exc
            shutil.rmtree(target)
        if backup_moved and backup is not None:
            _no_symlinks(target)
            if target.exists():
                raise RuntimeError(f"rollback blocked by a new target; original backup retained at {backup}") from exc
            backup.rename(target)
            backup_moved = False
        raise
    finally:
        shutil.rmtree(temporary, ignore_errors=True)
        if backup_container is not None and not backup_moved:
            backup_container.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("list", "check", "install", "validate"))
    parser.add_argument("skills", nargs="*")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--skills-dir", type=Path, help="absolute runtime Skill directory (overrides CODEX_HOME)")
    parser.add_argument("--dry-run", action="store_true", help="preview install without writing anything")
    parser.add_argument("--replace-local", action="store_true", help="explicitly replace an unknown/modified Skill after backup")
    args = parser.parse_args()
    try:
        registry_path = _absolute(args.registry)
        registry = load_registry(registry_path)
        summaries, documents = validate_repository(registry_path, registry)
        skills = selected_skills(registry, args.skills)
        if args.command == "validate":
            selected = {item["name"] for item in skills}
            results = [item for item in summaries if item["name"] in selected]
        elif args.command == "list":
            selected = {item["name"] for item in skills}
            results = [{**item, "target": str(resolve_target(item["install_target"], args.skills_dir))}
                       for item in summaries if item["name"] in selected]
        elif args.command == "check":
            results = [check_skill(registry_path, item, args.skills_dir) for item in skills]
        else:
            results = [install_skill(registry_path, item, args.skills_dir, dry_run=args.dry_run,
                                     replace_local=args.replace_local) for item in skills]
    except (OSError, ValueError, RuntimeError, UnicodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 3
    success = all(item.get("status", "installed") == "installed" for item in results)
    print(json.dumps({"status": "ready" if success else "attention_required", "skills": results,
                      "documents": documents}, ensure_ascii=False, indent=2))
    return 0 if success else 2


if __name__ == "__main__":
    sys.exit(main())
