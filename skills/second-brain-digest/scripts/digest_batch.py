#!/usr/bin/env python3
"""Prepare, validate, complete, and inspect resumable semantic digest batches."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Iterator

from evidence_intake import (
    IntakeError,
    atomic_write_json,
    is_relative_to,
    sha256_file,
    utc_now,
    validate_vault,
)


SCHEMA_VERSION = "1.0"
BATCH_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SOURCE_ID_PATTERN = re.compile(r"^src_[a-f0-9]{24}$")
REQUIRED_RESULT_KEYS = {
    "schema_version",
    "batch_id",
    "source_ids",
    "read_set",
    "object_changes",
    "relationship_changes",
    "event_changes",
    "no_change",
    "concept_convergence",
    "conflicts",
    "residue",
}
OPTIONAL_RESULT_KEYS = {
    "method_candidates",
}


class DigestError(RuntimeError):
    """A fail-closed semantic batch error."""


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DigestError(f"expected JSON object: {path}")
    return payload


def unique(values: Iterable[str], label: str) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise DigestError(f"duplicate {label}: {value}")
        seen.add(value)
        output.append(value)
    return output


def validate_batch_id(value: str) -> str:
    if not BATCH_ID_PATTERN.fullmatch(value):
        raise DigestError(f"invalid batch id: {value!r}")
    return value


def processing_root(vault: Path) -> Path:
    return vault.resolve(strict=True) / "evidence" / ".processing"


def batch_root(vault: Path, batch_id: str) -> Path:
    root = (processing_root(vault) / validate_batch_id(batch_id)).resolve(strict=False)
    if not is_relative_to(root, processing_root(vault).resolve(strict=False)):
        raise DigestError("batch path escapes evidence/.processing")
    return root


def normalize_note_path(vault: Path, raw: str, must_exist: bool = True) -> tuple[str, Path]:
    vault = vault.resolve(strict=True)
    value = Path(raw)
    if value.is_absolute():
        raise DigestError(f"note path must be vault-relative: {raw}")
    path = (vault / value).resolve(strict=must_exist)
    if not is_relative_to(path, vault) or is_relative_to(
        path, (vault / "evidence").resolve(strict=True)
    ):
        raise DigestError(f"note path is outside the core layer: {raw}")
    if must_exist and not path.is_file():
        raise DigestError(f"note is not a file: {raw}")
    return path.relative_to(vault).as_posix(), path


def source_records(vault: Path, source_ids: list[str]) -> list[dict[str, Any]]:
    vault = vault.resolve(strict=True)
    requested = unique(source_ids, "source id")
    if not requested:
        raise DigestError("at least one --source-id is required")
    for source_id in requested:
        if not SOURCE_ID_PATTERN.fullmatch(source_id):
            raise DigestError(f"invalid source id: {source_id}")

    found: dict[str, dict[str, Any]] = {}
    intake_root = vault / "evidence" / ".intake"
    for plan_path in sorted(intake_root.glob("*/plan.json")):
        plan = load_json(plan_path)
        for entry in plan.get("entries", []):
            source_id = entry.get("source_id")
            if source_id not in requested:
                continue
            record = {
                "source_id": source_id,
                "source_path": entry["destination"],
                "sha256": entry["sha256"],
                "size": entry["size"],
                "intake_plan_id": plan.get("plan_id"),
            }
            previous = found.get(source_id)
            if previous and {
                key: previous[key] for key in ("source_path", "sha256", "size")
            } != {key: record[key] for key in ("source_path", "sha256", "size")}:
                raise DigestError(f"conflicting intake records for {source_id}")
            found[source_id] = record

    missing = [source_id for source_id in requested if source_id not in found]
    if missing:
        raise DigestError(f"source ids not found in intake plans: {', '.join(missing)}")
    records = [found[source_id] for source_id in requested]
    verify_sources(vault, records)
    return records


def verify_sources(vault: Path, records: list[dict[str, Any]]) -> None:
    vault = vault.resolve(strict=True)
    source_root = (vault / "evidence" / "sources").resolve(strict=True)
    for record in records:
        relative = Path(record["source_path"])
        if relative.is_absolute():
            raise DigestError(f"source path must be vault-relative: {relative}")
        path = (vault / relative).resolve(strict=True)
        if not is_relative_to(path, source_root) or not path.is_file():
            raise DigestError(f"invalid admitted source path: {relative}")
        if path.stat().st_size != record["size"] or sha256_file(path) != record["sha256"]:
            raise DigestError(f"admitted source drifted: {relative}")


def build_read_set(vault: Path, note_paths: list[str]) -> list[dict[str, str]]:
    normalized: list[tuple[str, Path]] = [normalize_note_path(vault, value) for value in note_paths]
    unique([item[0] for item in normalized], "read note")
    return [
        {"note_path": relative, "sha256": sha256_file(path)}
        for relative, path in normalized
    ]


def verify_read_set(vault: Path, read_set: list[dict[str, str]]) -> None:
    for item in read_set:
        relative, path = normalize_note_path(vault, item["note_path"])
        if relative != item["note_path"] or sha256_file(path) != item["sha256"]:
            raise DigestError(f"read set drifted: {item['note_path']}")


def prepare_batch(
    vault: Path, batch_id: str, source_ids: list[str], note_paths: list[str]
) -> dict[str, Any]:
    root = batch_root(vault, batch_id)
    manifest_path = root / "manifest.json"
    requested_sources = unique(source_ids, "source id")
    requested_notes = unique(note_paths, "read note")
    if manifest_path.exists():
        manifest = load_json(manifest_path)
        existing_sources = [item["source_id"] for item in manifest["source_records"]]
        existing_notes = [item["note_path"] for item in manifest["read_set"]]
        normalized_notes = [normalize_note_path(vault, value)[0] for value in requested_notes]
        if existing_sources != requested_sources or existing_notes != normalized_notes:
            raise DigestError("existing batch inputs do not match; use a new batch id")
        verify_sources(vault, manifest["source_records"])
        verify_read_set(vault, manifest["read_set"])
        action = "resumed"
    else:
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "batch_id": validate_batch_id(batch_id),
            "created_at": utc_now(),
            "status": "prepared",
            "source_records": source_records(vault, requested_sources),
            "read_set": build_read_set(vault, requested_notes),
        }
        atomic_write_json(manifest_path, manifest)
        action = "prepared"
    return {
        "status": action,
        "batch_id": batch_id,
        "manifest_path": str(manifest_path),
        "sources": len(manifest["source_records"]),
        "read_notes": len(manifest["read_set"]),
        "result_path": str(root / "result.json"),
    }


def iter_evidence_refs(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        if {"source_id", "source_path", "sha256", "locator"}.issubset(value):
            yield value
        for child in value.values():
            yield from iter_evidence_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_evidence_refs(child)


def require_exact_object(
    value: Any, label: str, required: set[str], optional: set[str] | None = None
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DigestError(f"{label} must be an object")
    allowed = required | (optional or set())
    missing = required - value.keys()
    extra = value.keys() - allowed
    if missing or extra:
        raise DigestError(
            f"{label} keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    return value


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise DigestError(f"{label} must be a non-empty string")
    return value


def require_string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise DigestError(f"{label} must be an array of strings")
    return value


def validate_evidence_refs_value(value: Any, label: str, allow_empty: bool = False) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise DigestError(f"{label} must be a {'possibly empty' if allow_empty else 'non-empty'} array")
    required = {"source_id", "source_path", "sha256", "locator"}
    optional = {"excerpt"}
    for index, raw in enumerate(value):
        ref = require_exact_object(raw, f"{label}[{index}]", required, optional)
        for key in required:
            require_nonempty_string(ref[key], f"{label}[{index}].{key}")
        if not SOURCE_ID_PATTERN.fullmatch(ref["source_id"]):
            raise DigestError(f"{label}[{index}].source_id is invalid")
        if not ref["source_path"].startswith("evidence/sources/"):
            raise DigestError(f"{label}[{index}].source_path is outside evidence/sources")
        if not re.fullmatch(r"[a-f0-9]{64}", ref["sha256"]):
            raise DigestError(f"{label}[{index}].sha256 is invalid")
        if "excerpt" in ref and (not isinstance(ref["excerpt"], str) or len(ref["excerpt"]) > 500):
            raise DigestError(f"{label}[{index}].excerpt is invalid")


def validate_ideology_updates(result: dict[str, Any]) -> None:
    required = {
        "operation",
        "dimension",
        "statement",
        "basis",
        "confidence",
        "as_of",
        "decision_relevance",
        "counterevidence",
        "evidence_refs",
        "unknowns",
    }
    for object_index, raw_object in enumerate(result["object_changes"]):
        if not isinstance(raw_object, dict) or "ideology_updates" not in raw_object:
            continue
        label = f"object_changes[{object_index}]"
        updates = raw_object["ideology_updates"]
        if not isinstance(updates, list) or not updates:
            raise DigestError(f"{label}.ideology_updates must be a non-empty array")
        if raw_object.get("action") != "update_existing":
            raise DigestError(f"{label}.ideology_updates only applies to update_existing")
        require_nonempty_string(raw_object.get("note_path"), f"{label}.note_path")
        if not isinstance(raw_object.get("roles"), list) or "person" not in raw_object["roles"]:
            raise DigestError(f"{label}.ideology_updates requires the person role")
        for update_index, raw_update in enumerate(updates):
            update_label = f"{label}.ideology_updates[{update_index}]"
            update = require_exact_object(raw_update, update_label, required)
            if update["operation"] not in {"upsert", "retract"}:
                raise DigestError(f"{update_label}.operation is invalid")
            if update["dimension"] not in {"worldview", "life_view", "values"}:
                raise DigestError(f"{update_label}.dimension is invalid")
            if update["basis"] not in {"direct", "inferred"}:
                raise DigestError(f"{update_label}.basis is invalid")
            for key in ("statement", "decision_relevance"):
                require_nonempty_string(update[key], f"{update_label}.{key}")
            confidence = update["confidence"]
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                raise DigestError(f"{update_label}.confidence must be between 0 and 1")
            if update["as_of"] is not None and not isinstance(update["as_of"], str):
                raise DigestError(f"{update_label}.as_of must be a string or null")
            require_string_list(update["counterevidence"], f"{update_label}.counterevidence")
            require_string_list(update["unknowns"], f"{update_label}.unknowns")
            validate_evidence_refs_value(update["evidence_refs"], f"{update_label}.evidence_refs")


def validate_method_candidates(result: dict[str, Any]) -> None:
    required = {
        "action",
        "note_path",
        "name",
        "domain",
        "status",
        "trigger",
        "decision_rule",
        "expected_output",
        "applicability_scope",
        "counterexamples",
        "validation_status",
        "validation_evidence_refs",
        "reason",
        "evidence_refs",
        "unknowns",
    }
    actions = {"create_candidate", "update_existing", "no_change", "review"}
    statuses = {"candidate", "draft", "validated", "disputed"}
    validation_statuses = {"untested", "single_case", "multi_case", "feedback_validated", "disputed"}
    for index, raw in enumerate(result.get("method_candidates", [])):
        label = f"method_candidates[{index}]"
        item = require_exact_object(raw, label, required)
        if item["action"] not in actions or item["status"] not in statuses:
            raise DigestError(f"{label} action or status is invalid")
        if item["validation_status"] not in validation_statuses:
            raise DigestError(f"{label}.validation_status is invalid")
        for key in ("name", "domain", "trigger", "decision_rule", "expected_output", "applicability_scope", "reason"):
            require_nonempty_string(item[key], f"{label}.{key}")
        if item["note_path"] is not None and not isinstance(item["note_path"], str):
            raise DigestError(f"{label}.note_path must be a string or null")
        if item["action"] in {"create_candidate", "update_existing"}:
            require_nonempty_string(item["note_path"], f"{label}.note_path")
        require_string_list(item["counterexamples"], f"{label}.counterexamples")
        require_string_list(item["unknowns"], f"{label}.unknowns")
        validate_evidence_refs_value(item["evidence_refs"], f"{label}.evidence_refs")
        validation_refs = item["validation_evidence_refs"]
        validate_evidence_refs_value(validation_refs, f"{label}.validation_evidence_refs", allow_empty=True)
        if item["validation_status"] != "untested" and not validation_refs:
            raise DigestError(f"{label}.validation_evidence_refs cannot be empty for this validation status")
        if item["status"] == "validated" and item["validation_status"] not in {
            "multi_case",
            "feedback_validated",
        }:
            raise DigestError(f"{label} cannot be validated without multi-case or Feedback validation")


def validate_ideology_targets(
    result: dict[str, Any], read_set: list[dict[str, str]]
) -> None:
    read_notes = {item["note_path"] for item in read_set}
    for index, item in enumerate(result["object_changes"]):
        if isinstance(item, dict) and "ideology_updates" in item:
            note_path = item.get("note_path")
            if note_path not in read_notes:
                raise DigestError(
                    f"object_changes[{index}].ideology_updates targets a note outside the read set"
                )


def fallback_contract_check(result: dict[str, Any]) -> None:
    missing = REQUIRED_RESULT_KEYS - result.keys()
    extra = result.keys() - REQUIRED_RESULT_KEYS - OPTIONAL_RESULT_KEYS
    if missing or extra:
        raise DigestError(
            f"result keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if result["schema_version"] != SCHEMA_VERSION:
        raise DigestError("unsupported result schema version")
    for key in REQUIRED_RESULT_KEYS - {"schema_version", "batch_id"}:
        if not isinstance(result[key], list):
            raise DigestError(f"result field must be an array: {key}")
    for key in OPTIONAL_RESULT_KEYS & result.keys():
        if not isinstance(result[key], list):
            raise DigestError(f"result field must be an array: {key}")
    if not isinstance(result["batch_id"], str) or not result["batch_id"]:
        raise DigestError("result batch_id must be a non-empty string")
    validate_ideology_updates(result)
    validate_method_candidates(result)
    for ref in iter_evidence_refs(result):
        if not all(isinstance(ref[key], str) and ref[key] for key in ("source_id", "source_path", "sha256", "locator")):
            raise DigestError("Evidence ref contains an empty required field")


def schema_check(result: dict[str, Any], schema_path: Path) -> str:
    try:
        import jsonschema  # type: ignore[import-not-found]
    except ImportError:
        fallback_contract_check(result)
        return "built_in_contract"
    schema = load_json(schema_path)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(result), key=lambda error: list(error.path))
    if errors:
        first = errors[0]
        location = "/".join(str(item) for item in first.path) or "$"
        raise DigestError(f"result schema invalid at {location}: {first.message}")
    return f"jsonschema-{jsonschema.__version__}"


def validate_batch(vault: Path, batch_id: str) -> dict[str, Any]:
    root = batch_root(vault, batch_id)
    manifest = load_json(root / "manifest.json")
    result_path = root / "result.json"
    result = load_json(result_path)
    backend = schema_check(
        result,
        Path(__file__).resolve().parent.parent / "references" / "digest-result.schema.json",
    )
    if result["batch_id"] != manifest["batch_id"]:
        raise DigestError("result batch_id does not match manifest")
    expected_sources = [item["source_id"] for item in manifest["source_records"]]
    if result["source_ids"] != expected_sources:
        raise DigestError("result source_ids do not exactly match manifest order")
    if result["read_set"] != manifest["read_set"]:
        raise DigestError("result read_set does not exactly match manifest")
    validate_ideology_targets(result, manifest["read_set"])

    verify_sources(vault, manifest["source_records"])
    verify_read_set(vault, manifest["read_set"])
    by_source = {item["source_id"]: item for item in manifest["source_records"]}
    references = list(iter_evidence_refs(result))
    for ref in references:
        source = by_source.get(ref["source_id"])
        if source is None:
            raise DigestError(f"Evidence ref uses source outside batch: {ref['source_id']}")
        if ref["source_path"] != source["source_path"] or ref["sha256"] != source["sha256"]:
            raise DigestError(f"Evidence ref does not match intake record: {ref['source_id']}")

    validation = {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch_id,
        "validated_at": utc_now(),
        "status": "valid",
        "schema_backend": backend,
        "result_sha256": sha256_file(result_path),
        "sources_verified": len(manifest["source_records"]),
        "read_notes_verified": len(manifest["read_set"]),
        "evidence_refs_verified": len(references),
    }
    atomic_write_json(root / "validation.json", validation)
    return validation


def complete_batch(
    vault: Path,
    batch_id: str,
    changed_notes: list[str],
    new_notes: list[str],
) -> dict[str, Any]:
    root = batch_root(vault, batch_id)
    manifest = load_json(root / "manifest.json")
    validation = load_json(root / "validation.json")
    result_path = root / "result.json"
    result = load_json(result_path)
    if validation.get("status") != "valid" or validation.get("result_sha256") != sha256_file(result_path):
        raise DigestError("result changed after validation; validate again before completion")
    verify_sources(vault, manifest["source_records"])

    normalized_changed = unique(
        [normalize_note_path(vault, value)[0] for value in changed_notes], "changed note"
    )
    normalized_new = unique(
        [normalize_note_path(vault, value)[0] for value in new_notes], "new note"
    )
    read_by_path = {item["note_path"]: item for item in manifest["read_set"]}
    outside_read_set = [path for path in normalized_changed if path not in read_by_path]
    if outside_read_set:
        raise DigestError(f"changed notes were not in read set: {', '.join(outside_read_set)}")
    proposed_new = {
        item.get("note_path")
        for item in result.get("object_changes", [])
        if item.get("action") == "create_candidate"
    }
    proposed_new.update(
        item.get("note_path")
        for item in result.get("method_candidates", [])
        if item.get("action") == "create_candidate"
    )
    undeclared_new = [path for path in normalized_new if path not in proposed_new]
    if undeclared_new:
        raise DigestError(f"new notes were not declared create_candidate: {', '.join(undeclared_new)}")

    changes: list[dict[str, Any]] = []
    for relative, item in read_by_path.items():
        _, path = normalize_note_path(vault, relative)
        current = sha256_file(path)
        if relative in normalized_changed:
            if current == item["sha256"]:
                raise DigestError(f"declared changed note is unchanged: {relative}")
            changes.append(
                {"note_path": relative, "before_sha256": item["sha256"], "after_sha256": current}
            )
        elif current != item["sha256"]:
            raise DigestError(f"undeclared read-set note changed: {relative}")
    for relative in normalized_new:
        _, path = normalize_note_path(vault, relative)
        changes.append({"note_path": relative, "before_sha256": None, "after_sha256": sha256_file(path)})

    completion = {
        "schema_version": SCHEMA_VERSION,
        "batch_id": batch_id,
        "completed_at": utc_now(),
        "status": "completed",
        "result_sha256": validation["result_sha256"],
        "core_changes": changes,
        "core_change_count": len(changes),
    }
    atomic_write_json(root / "completion.json", completion)
    return completion


def batch_status(vault: Path, batch_id: str) -> dict[str, Any]:
    root = batch_root(vault, batch_id)
    if not (root / "manifest.json").is_file():
        raise DigestError(f"unknown batch: {batch_id}")
    if (root / "completion.json").is_file():
        return load_json(root / "completion.json")
    if (root / "validation.json").is_file():
        return load_json(root / "validation.json")
    if (root / "result.json").is_file():
        return {"batch_id": batch_id, "status": "result_pending_validation"}
    return {"batch_id": batch_id, "status": "prepared"}


def self_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="second-brain-digest-batch-test-") as temporary:
        base = Path(temporary)
        vault = base / "Second Brain"
        vault.mkdir()
        (vault / ".AGENTS.md").write_text("# test\n", encoding="utf-8")
        source_path = vault / "evidence" / "sources" / "sample" / "source.txt"
        source_path.parent.mkdir(parents=True)
        source_path.write_text("source fact\n", encoding="utf-8")
        note_path = vault / "Projects" / "sample.md"
        note_path.parent.mkdir()
        note_path.write_text("# Sample\n", encoding="utf-8")
        source_id = "src_" + "a" * 24
        plan_path = vault / "evidence" / ".intake" / "test" / "plan.json"
        atomic_write_json(
            plan_path,
            {
                "schema_version": "1.0",
                "plan_id": "test",
                "entries": [
                    {
                        "source_id": source_id,
                        "destination": "evidence/sources/sample/source.txt",
                        "sha256": sha256_file(source_path),
                        "size": source_path.stat().st_size,
                    }
                ],
            },
        )
        batch_id = "digest_test"
        prepare_batch(vault, batch_id, [source_id], ["Projects/sample.md"])
        root = batch_root(vault, batch_id)
        manifest = load_json(root / "manifest.json")
        source = manifest["source_records"][0]
        result = {
            "schema_version": "1.0",
            "batch_id": batch_id,
            "source_ids": [source_id],
            "read_set": manifest["read_set"],
            "object_changes": [],
            "relationship_changes": [],
            "event_changes": [],
            "no_change": [
                {
                    "reason": "already represented",
                    "evidence_refs": [
                        {
                            "source_id": source_id,
                            "source_path": source["source_path"],
                            "sha256": source["sha256"],
                            "locator": "line 1",
                        }
                    ],
                }
            ],
            "concept_convergence": [],
            "conflicts": [],
            "residue": [],
            "method_candidates": [
                {
                    "action": "create_candidate",
                    "note_path": "Methods/sample-method.md",
                    "name": "sample method",
                    "domain": "test",
                    "status": "candidate",
                    "trigger": "a repeatable decision is needed",
                    "decision_rule": "check evidence before acting",
                    "expected_output": "a bounded recommendation",
                    "applicability_scope": "decisions that can be checked against durable evidence",
                    "counterexamples": ["a reversible preference with no material consequence"],
                    "validation_status": "single_case",
                    "validation_evidence_refs": [
                        {
                            "source_id": source_id,
                            "source_path": source["source_path"],
                            "sha256": source["sha256"],
                            "locator": "line 1",
                        }
                    ],
                    "reason": "exercise the optional method-candidate contract",
                    "evidence_refs": [
                        {
                            "source_id": source_id,
                            "source_path": source["source_path"],
                            "sha256": source["sha256"],
                            "locator": "line 1",
                        }
                    ],
                    "unknowns": ["not yet validated in a second case"],
                }
            ],
        }
        atomic_write_json(root / "result.json", result)
        validate_batch(vault, batch_id)
        completion = complete_batch(vault, batch_id, [], [])
        if completion["core_change_count"] != 0:
            raise DigestError("no-change completion recorded a core write")
        prepare_batch(vault, batch_id, [source_id], ["Projects/sample.md"])
        result["no_change"][0]["reason"] = "tampered after validation"
        atomic_write_json(root / "result.json", result)
        try:
            complete_batch(vault, batch_id, [], [])
        except DigestError:
            pass
        else:
            raise DigestError("post-validation result drift was accepted")
        invalid_method = dict(result)
        invalid_method["method_candidates"] = [{}]
        try:
            fallback_contract_check(invalid_method)
        except DigestError:
            pass
        else:
            raise DigestError("empty method candidate passed the built-in contract")
        invalid_ideology = dict(result)
        invalid_ideology["object_changes"] = [
            {
                "action": "update_existing",
                "note_path": "Projects/sample.md",
                "roles": ["project"],
                "ideology_updates": [{}],
            }
        ]
        try:
            fallback_contract_check(invalid_ideology)
        except DigestError:
            pass
        else:
            raise DigestError("non-person ideology candidate passed the built-in contract")
        outside_read_set = dict(result)
        outside_read_set["object_changes"] = [
            {"note_path": "people/persons/missing.md", "ideology_updates": [{}]}
        ]
        try:
            validate_ideology_targets(outside_read_set, manifest["read_set"])
        except DigestError:
            pass
        else:
            raise DigestError("ideology update outside the read set was accepted")
        contradictory_method = json.loads(json.dumps(result))
        contradictory_method["method_candidates"][0]["status"] = "validated"
        contradictory_method["method_candidates"][0]["validation_status"] = "untested"
        contradictory_method["method_candidates"][0]["validation_evidence_refs"] = []
        try:
            fallback_contract_check(contradictory_method)
        except DigestError:
            pass
        else:
            raise DigestError("validated method with untested evidence passed the built-in contract")
        return {"status": "passed", "checks": 10}


def print_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--vault", required=True)
    prepare_parser.add_argument("--batch-id", required=True)
    prepare_parser.add_argument("--source-id", action="append", required=True)
    prepare_parser.add_argument("--read-note", action="append", default=[])

    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--vault", required=True)
    validate_parser.add_argument("--batch-id", required=True)

    complete_parser = subparsers.add_parser("complete")
    complete_parser.add_argument("--vault", required=True)
    complete_parser.add_argument("--batch-id", required=True)
    complete_parser.add_argument("--changed-note", action="append", default=[])
    complete_parser.add_argument("--new-note", action="append", default=[])

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--vault", required=True)
    status_parser.add_argument("--batch-id", required=True)

    subparsers.add_parser("self-test")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "self-test":
            print_result(self_test())
            return 0
        vault = validate_vault(args.vault)
        if args.command == "prepare":
            output = prepare_batch(vault, args.batch_id, args.source_id, args.read_note)
        elif args.command == "validate":
            output = validate_batch(vault, args.batch_id)
        elif args.command == "complete":
            output = complete_batch(vault, args.batch_id, args.changed_note, args.new_note)
        else:
            output = batch_status(vault, args.batch_id)
        print_result(output)
        return 0
    except (DigestError, IntakeError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print_result({"status": "error", "error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
