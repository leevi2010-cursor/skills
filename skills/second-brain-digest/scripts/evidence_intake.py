#!/usr/bin/env python3
"""Plan, apply, and verify resumable moves into Second Brain evidence/."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


SCHEMA_VERSION = "1.0"
BUFFER_SIZE = 4 * 1024 * 1024
IGNORED_NAMES = {".DS_Store", ".localized"}
IGNORED_PREFIXES = ("~$",)


class IntakeError(RuntimeError):
    """A fail-closed intake error."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(BUFFER_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    temporary = path.with_name(f".{path.name}.partial-{uuid.uuid4().hex}")
    try:
        with temporary.open("xb") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def append_receipt(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        with os.fdopen(descriptor, "ab", closefd=True) as handle:
            handle.write(canonical_bytes(payload) + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        os.chmod(path, 0o600)


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def safe_slug(name: str) -> str:
    value = re.sub(r"[^\w.-]+", "-", name, flags=re.UNICODE).strip("-._")
    return (value or "source")[:48]


def validate_vault(value: str | Path) -> Path:
    vault = Path(value).expanduser().resolve(strict=True)
    if not vault.is_dir() or not (vault / ".AGENTS.md").is_file():
        raise IntakeError(f"not a Second Brain vault: {vault}")
    evidence = vault / "evidence"
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    return vault


def validate_source_roots(vault: Path, values: list[str]) -> list[Path]:
    if not values:
        raise IntakeError("at least one --source is required")
    evidence = (vault / "evidence").resolve(strict=False)
    home = Path.home().resolve()
    roots: list[Path] = []
    for value in values:
        root = Path(value).expanduser().resolve(strict=True)
        if root in {Path("/"), home, vault}:
            raise IntakeError(f"source root is too broad: {root}")
        if root == evidence or root in evidence.parents:
            raise IntakeError(f"source root contains the evidence target: {root}")
        if is_relative_to(root, evidence):
            raise IntakeError(f"source is already inside evidence: {root}")
        roots.append(root)
    unique = sorted(set(roots), key=lambda item: str(item))
    for index, left in enumerate(unique):
        for right in unique[index + 1 :]:
            if is_relative_to(left, right) or is_relative_to(right, left):
                raise IntakeError(f"overlapping source roots: {left} and {right}")
    return unique


def normalize_extensions(values: Iterable[str]) -> set[str]:
    extensions: set[str] = set()
    for raw_value in values:
        value = raw_value.strip().lower()
        if not value or "/" in value or "\\" in value:
            raise IntakeError(f"invalid excluded extension: {raw_value!r}")
        extensions.add(value if value.startswith(".") else f".{value}")
    return extensions


def should_ignore(path: Path, excluded_extensions: set[str]) -> str | None:
    if path.name in IGNORED_NAMES:
        return "system_metadata"
    if path.name.startswith(IGNORED_PREFIXES):
        return "temporary_office_file"
    if path.suffix.lower() in excluded_extensions:
        return f"excluded_extension:{path.suffix.lower()}"
    return None


def iter_regular_files(
    root: Path, excluded_extensions: set[str]
) -> tuple[list[Path], list[dict[str, str]], list[dict[str, str]]]:
    files: list[Path] = []
    skipped: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []

    def inspect(path: Path) -> None:
        reason = should_ignore(path, excluded_extensions)
        if reason:
            skipped.append({"path": str(path), "reason": reason})
            return
        try:
            info = path.lstat()
        except OSError as exc:
            blocked.append({"path": str(path), "reason": f"lstat_failed:{exc}"})
            return
        if stat.S_ISLNK(info.st_mode):
            blocked.append({"path": str(path), "reason": "symbolic_link"})
        elif stat.S_ISREG(info.st_mode):
            files.append(path)
        else:
            blocked.append({"path": str(path), "reason": "not_regular_file"})

    if root.is_symlink() or root.is_file():
        inspect(root)
        return files, skipped, blocked
    if not root.is_dir():
        return files, skipped, [{"path": str(root), "reason": "unsupported_root"}]

    for current, directories, names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directories):
            candidate = current_path / name
            reason = should_ignore(candidate, excluded_extensions)
            if reason:
                skipped.append({"path": str(candidate), "reason": reason})
            elif candidate.is_symlink():
                blocked.append({"path": str(candidate), "reason": "symbolic_link_directory"})
            else:
                kept_directories.append(name)
        directories[:] = kept_directories
        for name in sorted(names):
            inspect(current_path / name)
    files.sort(key=lambda item: str(item))
    return files, skipped, blocked


def stable_file_record(path: Path) -> tuple[os.stat_result, str]:
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode):
        raise IntakeError(f"not a regular file: {path}")
    digest = sha256_file(path)
    after = path.stat(follow_symlinks=False)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after:
        raise IntakeError(f"file changed while hashing: {path}")
    return after, digest


def make_plan(
    vault: Path,
    roots: list[Path],
    output: Path | None = None,
    excluded_extensions: set[str] | None = None,
) -> Path:
    excluded_extensions = excluded_extensions or set()
    run_id = f"intake_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}_{uuid.uuid4().hex[:8]}"
    output = output or vault / "evidence" / ".intake" / run_id / "plan.json"
    output = output.expanduser().resolve(strict=False)
    private_root = (vault / "evidence" / ".intake").resolve(strict=False)
    if not is_relative_to(output, private_root):
        raise IntakeError(f"plan must remain under {private_root}")

    entries: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []
    root_records: list[dict[str, str]] = []

    for root in roots:
        root_key = sha256_bytes(str(root).encode("utf-8"))[:10]
        root_id = f"{safe_slug(root.name)}-{root_key}"
        root_records.append(
            {"path": str(root), "root_id": root_id, "kind": "directory" if root.is_dir() else "file"}
        )
        files, root_skipped, root_blocked = iter_regular_files(root, excluded_extensions)
        skipped.extend(root_skipped)
        blocked.extend(root_blocked)
        for source in files:
            info, digest = stable_file_record(source)
            relative = source.relative_to(root) if root.is_dir() else Path(source.name)
            destination = Path("evidence") / "sources" / root_id / relative
            source_id = "src_" + sha256_bytes(
                f"{root_id}\0{relative.as_posix()}\0{digest}".encode("utf-8")
            )[:24]
            entries.append(
                {
                    "source_id": source_id,
                    "source_root": str(root),
                    "source_path": str(source),
                    "relative_path": relative.as_posix(),
                    "destination": destination.as_posix(),
                    "size": info.st_size,
                    "mtime_ns": info.st_mtime_ns,
                    "original_mode": stat.S_IMODE(info.st_mode),
                    "sha256": digest,
                }
            )

    entries.sort(key=lambda item: item["source_path"])
    core: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "plan_id": run_id,
        "created_at": utc_now(),
        "vault": str(vault),
        "source_roots": root_records,
        "excluded_extensions": sorted(excluded_extensions),
        "entries": entries,
        "skipped": sorted(skipped, key=lambda item: item["path"]),
        "blocked": sorted(blocked, key=lambda item: item["path"]),
    }
    core["summary"] = {
        "files": len(entries),
        "bytes": sum(item["size"] for item in entries),
        "skipped": len(skipped),
        "blocked": len(blocked),
    }
    core["plan_digest"] = sha256_bytes(canonical_bytes(core))
    atomic_write_json(output, core)
    return output


def load_plan(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntakeError(f"cannot read plan: {exc}") from exc
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise IntakeError("unsupported plan schema")
    expected = payload.get("plan_digest")
    if not isinstance(expected, str):
        raise IntakeError("plan_digest missing")
    unsigned = dict(payload)
    unsigned.pop("plan_digest", None)
    actual = sha256_bytes(canonical_bytes(unsigned))
    if actual != expected:
        raise IntakeError("plan digest mismatch")
    return payload


def validate_target(vault: Path, relative: str) -> Path:
    target = (vault / relative).resolve(strict=False)
    source_root = (vault / "evidence" / "sources").resolve(strict=False)
    if not is_relative_to(target, source_root):
        raise IntakeError(f"target escapes evidence/sources: {relative}")
    return target


def verify_file(path: Path, entry: dict[str, Any], *, check_mtime: bool) -> None:
    if path.is_symlink() or not path.is_file():
        raise IntakeError(f"expected regular file: {path}")
    info = path.stat(follow_symlinks=False)
    if info.st_size != entry["size"]:
        raise IntakeError(f"size drift: {path}")
    if check_mtime and info.st_mtime_ns != entry["mtime_ns"]:
        raise IntakeError(f"mtime drift: {path}")
    if sha256_file(path) != entry["sha256"]:
        raise IntakeError(f"content drift: {path}")


def preflight_plan(payload: dict[str, Any]) -> tuple[Path, list[tuple[dict[str, Any], Path, Path]]]:
    if payload.get("blocked"):
        raise IntakeError("plan has blocked paths; exclude or resolve them and create a new plan")
    vault = validate_vault(payload["vault"])
    items: list[tuple[dict[str, Any], Path, Path]] = []
    for entry in payload.get("entries", []):
        source = Path(entry["source_path"])
        target = validate_target(vault, entry["destination"])
        if target.exists():
            verify_file(target, entry, check_mtime=False)
            if source.exists():
                verify_file(source, entry, check_mtime=True)
        else:
            if not source.exists():
                raise IntakeError(f"source and target are both missing: {entry['source_id']}")
            verify_file(source, entry, check_mtime=True)
        items.append((entry, source, target))
    if not items:
        raise IntakeError("plan contains no files")
    return vault, items


def move_one(entry: dict[str, Any], source: Path, target: Path) -> str:
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(target.parent, 0o700)
    if target.exists():
        verify_file(target, entry, check_mtime=False)
        if source.exists():
            verify_file(source, entry, check_mtime=True)
            source.unlink()
            fsync_directory(source.parent)
            return "deduplicated_source_path"
        return "already_completed"

    if not source.exists():
        raise IntakeError(f"source disappeared before move: {entry['source_id']}")
    same_device = source.stat().st_dev == target.parent.stat().st_dev
    if same_device:
        os.replace(source, target)
        try:
            verify_file(target, entry, check_mtime=False)
        except Exception:
            if not source.exists() and target.exists():
                os.replace(target, source)
            raise
        os.chmod(target, 0o600)
        fsync_directory(target.parent)
        fsync_directory(source.parent)
        return "atomic_move"

    temporary = target.with_name(f".{target.name}.partial-{uuid.uuid4().hex}")
    try:
        with source.open("rb") as input_handle, temporary.open("xb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle, BUFFER_SIZE)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.chmod(temporary, 0o600)
        verify_file(temporary, entry, check_mtime=False)
        os.replace(temporary, target)
        fsync_directory(target.parent)
        verify_file(target, entry, check_mtime=False)
        source.unlink()
        fsync_directory(source.parent)
        return "verified_cross_device_move"
    finally:
        if temporary.exists():
            temporary.unlink()


def prune_empty_directories(payload: dict[str, Any]) -> int:
    removed = 0
    for root_item in payload.get("source_roots", []):
        if root_item.get("kind") != "directory":
            continue
        root = Path(root_item["path"])
        if not root.exists() or not root.is_dir() or root.is_symlink():
            continue
        for current, _, _ in os.walk(root, topdown=False, followlinks=False):
            current_path = Path(current)
            if current_path == root:
                continue
            try:
                current_path.rmdir()
                removed += 1
            except OSError:
                pass
    return removed


def apply_plan(plan_path: Path, confirm: str, prune_empty: bool) -> dict[str, Any]:
    payload = load_plan(plan_path)
    if confirm != payload["plan_digest"]:
        raise IntakeError("--confirm must exactly equal plan_digest")
    _, items = preflight_plan(payload)
    receipt_path = plan_path.parent / "receipts.jsonl"
    completed = 0
    for entry, source, target in items:
        method = move_one(entry, source, target)
        append_receipt(
            receipt_path,
            {
                "schema_version": SCHEMA_VERSION,
                "plan_id": payload["plan_id"],
                "plan_digest": payload["plan_digest"],
                "source_id": entry["source_id"],
                "source_path": entry["source_path"],
                "destination": entry["destination"],
                "sha256": entry["sha256"],
                "completed_at": utc_now(),
                "method": method,
            },
        )
        completed += 1
    removed = prune_empty_directories(payload) if prune_empty else 0
    return {
        "status": "completed",
        "plan_id": payload["plan_id"],
        "plan_digest": payload["plan_digest"],
        "files": completed,
        "bytes": payload["summary"]["bytes"],
        "pruned_empty_directories": removed,
        "receipt_path": str(receipt_path),
    }


def status_plan(plan_path: Path) -> dict[str, Any]:
    payload = load_plan(plan_path)
    vault = validate_vault(payload["vault"])
    counts = {"completed": 0, "pending": 0, "duplicated": 0, "missing": 0, "drifted": 0}
    for entry in payload.get("entries", []):
        source = Path(entry["source_path"])
        target = validate_target(vault, entry["destination"])
        try:
            source_valid = False
            target_valid = False
            if source.exists():
                verify_file(source, entry, check_mtime=True)
                source_valid = True
            if target.exists():
                verify_file(target, entry, check_mtime=False)
                target_valid = True
        except IntakeError:
            counts["drifted"] += 1
            continue
        if target_valid and not source_valid:
            counts["completed"] += 1
        elif source_valid and not target_valid:
            counts["pending"] += 1
        elif source_valid and target_valid:
            counts["duplicated"] += 1
        else:
            counts["missing"] += 1
    overall = "completed" if counts["completed"] == len(payload.get("entries", [])) else "attention_required"
    return {
        "status": overall,
        "plan_id": payload["plan_id"],
        "plan_digest": payload["plan_digest"],
        "counts": counts,
    }


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="second-brain-digest-test-") as temporary:
        base = Path(temporary)
        vault = base / "Second Brain"
        vault.mkdir()
        (vault / ".AGENTS.md").write_text("# test\n", encoding="utf-8")
        (vault / "evidence").mkdir()
        source = base / "incoming"
        (source / "nested").mkdir(parents=True)
        (source / "one.txt").write_text("alpha\n", encoding="utf-8")
        (source / "nested" / "two.txt").write_text("beta\n", encoding="utf-8")
        (source / ".DS_Store").write_bytes(b"ignored")
        (source / "program.exe").write_bytes(b"excluded")

        plan_path = make_plan(
            validate_vault(vault), [source.resolve()], excluded_extensions={".exe"}
        )
        payload = load_plan(plan_path)
        if payload["summary"] != {"files": 2, "bytes": 11, "skipped": 2, "blocked": 0}:
            raise IntakeError("self-test plan summary mismatch")
        if not (source / "one.txt").exists():
            raise IntakeError("plan unexpectedly moved a file")
        if not (source / "program.exe").exists():
            raise IntakeError("excluded extension was moved")
        try:
            apply_plan(plan_path, "wrong", False)
        except IntakeError:
            pass
        else:
            raise IntakeError("wrong confirmation was accepted")

        result = apply_plan(plan_path, payload["plan_digest"], True)
        if result["files"] != 2 or (source / "one.txt").exists():
            raise IntakeError("self-test move did not complete")
        status = status_plan(plan_path)
        if status["status"] != "completed" or status["counts"]["completed"] != 2:
            raise IntakeError("self-test readback failed")
        return {"status": "passed", "checks": 7}


def print_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="hash sources and write a no-move plan")
    plan_parser.add_argument("--vault", required=True)
    plan_parser.add_argument("--source", action="append", required=True)
    plan_parser.add_argument(
        "--exclude-extension",
        action="append",
        default=[],
        help="exclude one file or bundle extension; repeat as needed (for example .dmg)",
    )
    plan_parser.add_argument("--output", type=Path)

    apply_parser = subparsers.add_parser("apply", help="apply one exact plan")
    apply_parser.add_argument("--plan", required=True, type=Path)
    apply_parser.add_argument("--confirm", required=True)
    apply_parser.add_argument("--prune-empty", action="store_true")

    status_parser = subparsers.add_parser("status", help="hash and read back one plan")
    status_parser.add_argument("--plan", required=True, type=Path)

    subparsers.add_parser("self-test", help="run an isolated move and recovery test")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "plan":
            vault = validate_vault(args.vault)
            roots = validate_source_roots(vault, args.source)
            excluded_extensions = normalize_extensions(args.exclude_extension)
            plan_path = make_plan(vault, roots, args.output, excluded_extensions)
            payload = load_plan(plan_path)
            print_result(
                {
                    "status": "ready" if not payload["blocked"] else "attention_required",
                    "plan_path": str(plan_path),
                    "plan_id": payload["plan_id"],
                    "plan_digest": payload["plan_digest"],
                    "source_roots": [item["path"] for item in payload["source_roots"]],
                    "excluded_extensions": payload["excluded_extensions"],
                    "summary": payload["summary"],
                }
            )
        elif args.command == "apply":
            print_result(apply_plan(args.plan.expanduser().resolve(strict=True), args.confirm, args.prune_empty))
        elif args.command == "status":
            print_result(status_plan(args.plan.expanduser().resolve(strict=True)))
        else:
            print_result(self_test())
    except (IntakeError, OSError, ValueError, KeyError) as exc:
        print_result({"status": "error", "error": str(exc)})
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
