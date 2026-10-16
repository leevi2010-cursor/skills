"""Offline manager tests: every installation and fixture stays in TemporaryDirectory."""

import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


MANAGER = Path(__file__).resolve().parents[1] / "portable_skill_manager.py"
SPEC = importlib.util.spec_from_file_location("portable_manager_test_subject", MANAGER)
manager = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manager)


class PortableManagerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="portable-manager-test-")
        self.addCleanup(self.temporary.cleanup)
        # macOS temp roots can be reached through /var; test the actual physical path.
        self.root = Path(self.temporary.name).resolve()
        self.repository = self.root / "repository"
        self.repository.mkdir()
        self.runtime = self.root / "runtime" / "skills"
        self.source = self.repository / "skills" / "demo"
        self.item = self.make_skill("demo")
        self.payload = {"schema_version": "1.0", "skills": [self.item]}
        self.registry = self.repository / "portable-skill-registry.json"
        self.save_registry()
        self.target = self.runtime / "demo"

    def make_skill(self, name):
        source = self.repository / "skills" / name
        source.mkdir(parents=True)
        (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Test fixture.\n---\n# Fixture\n")
        (source / "data.txt").write_text("source-v1")
        return {"name": name, "source": f"skills/{name}",
                "install_target": f"~/.codex/skills/{name}", "required_for": ["fixture"],
                "summary": "Fixture", "when_to_use": "Tests", "prerequisites": [],
                "version_policy": "content-sha256"}

    def save_registry(self):
        self.registry.write_text(json.dumps(self.payload), encoding="utf-8")

    def install(self, **kwargs):
        return manager.install_skill(self.registry, self.item, self.runtime, **kwargs)

    def check(self):
        return manager.check_skill(self.registry, self.item, self.runtime)

    def local_copy(self, content="local"):
        shutil.copytree(self.source, self.target)
        (self.target / "data.txt").write_text(content)

    def receipt_path(self):
        return self.runtime / manager.STATE_DIRECTORY / "demo.json"

    def cli(self, *args, env=None):
        environment = dict(os.environ, CODEX_HOME=str(self.root / "unused-codex"))
        if env:
            environment.update(env)
        result = subprocess.run([sys.executable, "-B", str(MANAGER), *args,
                                 "--registry", str(self.registry), "--skills-dir", str(self.runtime)],
                                capture_output=True, text=True, env=environment)
        self.assertFalse(result.stderr, result.stderr)
        return result.returncode, json.loads(result.stdout)

    def validate(self):
        payload = manager.load_registry(self.registry)
        return manager.validate_repository(self.registry, payload)

    def test_fresh_install_writes_external_receipt_and_reads_back(self):
        result = self.install()
        self.assertEqual(result["action"], "installed")
        self.assertEqual(self.check()["status"], "installed")
        self.assertEqual(json.loads(self.receipt_path().read_text())["source_digest"], result["source_digest"])
        self.assertEqual(result["receipt_digest"], self.check()["receipt_digest"])
        self.assertTrue(result["update_allowed"])
        self.assertFalse((self.target / manager.STATE_DIRECTORY).exists())

    def test_identical_install_is_noop(self):
        self.install()
        before = self.receipt_path().read_bytes()
        self.assertEqual(self.install()["action"], "noop")
        self.assertEqual(before, self.receipt_path().read_bytes())

    def test_identical_unknown_copy_is_noop_without_adoption(self):
        shutil.copytree(self.source, self.target)
        self.assertEqual(self.install()["action"], "noop")
        self.assertFalse(self.receipt_path().exists())
        (self.source / "data.txt").write_text("source-v2")
        self.assertEqual(self.install()["action"], "blocked")

    def test_managed_unchanged_copy_updates_and_preserves_backup(self):
        self.install()
        (self.source / "data.txt").write_text("source-v2")
        self.assertTrue(self.check()["update_allowed"])
        result = self.install()
        self.assertEqual(result["action"], "installed")
        self.assertEqual((self.target / "data.txt").read_text(), "source-v2")
        self.assertEqual((Path(result["backup"]) / "data.txt").read_text(), "source-v1")
        self.assertNotIn(self.runtime, Path(result["backup"]).parents)
        self.assertIn(manager._backup_root(self.target), Path(result["backup"]).parents)
        self.assertEqual(json.loads(self.receipt_path().read_text())["source_digest"], result["source_digest"])

    def test_locally_modified_managed_copy_is_blocked(self):
        self.install()
        (self.target / "data.txt").write_text("custom")
        self.assertEqual(self.install()["action"], "blocked")
        self.assertEqual((self.target / "data.txt").read_text(), "custom")
        self.assertFalse(list(self.runtime.glob(".demo.backup-*")))

    def test_unknown_drift_is_blocked(self):
        self.local_copy()
        self.assertEqual(self.install()["action"], "blocked")
        self.assertEqual((self.target / "data.txt").read_text(), "local")

    def test_explicit_replace_preserves_local_copy(self):
        self.local_copy()
        result = self.install(replace_local=True)
        self.assertEqual((Path(result["backup"]) / "data.txt").read_text(), "local")
        self.assertEqual(self.check()["status"], "installed")

    def test_dry_run_missing_creates_nothing(self):
        self.assertEqual(self.install(dry_run=True)["action"], "would_install")
        self.assertFalse(self.runtime.parent.exists())

    def test_dry_run_replacement_creates_no_receipt_or_backup(self):
        self.local_copy()
        self.assertEqual(self.install(dry_run=True, replace_local=True)["action"], "would_update")
        self.assertFalse(self.receipt_path().exists())
        self.assertFalse(list(self.runtime.glob(".demo.backup-*")))
        self.assertFalse(manager._backup_root(self.target).exists())
        self.assertEqual((self.target / "data.txt").read_text(), "local")

    def test_target_symlink_is_blocked_even_with_replace(self):
        self.runtime.mkdir(parents=True)
        self.target.symlink_to(self.source, target_is_directory=True)
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")
        self.assertTrue(self.target.is_symlink())

    def test_broken_target_symlink_is_blocked(self):
        self.runtime.mkdir(parents=True)
        self.target.symlink_to(self.root / "missing", target_is_directory=True)
        self.assertEqual(self.install()["action"], "blocked")

    def test_target_ancestor_symlink_is_blocked(self):
        external = self.root / "external"
        external.mkdir()
        self.runtime.parent.mkdir()
        self.runtime.symlink_to(external, target_is_directory=True)
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")
        self.assertEqual(list(external.iterdir()), [])

    def test_target_internal_symlink_is_blocked(self):
        self.local_copy()
        (self.target / "link").symlink_to(self.source / "data.txt")
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")

    def test_state_symlink_is_blocked(self):
        self.runtime.mkdir(parents=True)
        external = self.root / "external"
        external.mkdir()
        (self.runtime / manager.STATE_DIRECTORY).symlink_to(external, target_is_directory=True)
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")
        self.assertEqual(list(external.iterdir()), [])

    def test_source_file_and_directory_symlinks_are_rejected(self):
        for name, target in (("link", self.registry), ("__pycache__", self.root)):
            with self.subTest(name=name):
                link = self.source / name
                link.symlink_to(target, target_is_directory=target.is_dir())
                with self.assertRaisesRegex(ValueError, "symlink"):
                    self.validate()
                link.unlink()

    def test_skill_frontmatter_symlink_is_rejected_before_reading(self):
        skill = self.source / "SKILL.md"
        skill.unlink()
        skill.symlink_to(self.registry)
        with mock.patch.object(manager, "_frontmatter", side_effect=AssertionError("must not read link")):
            with self.assertRaisesRegex(ValueError, "symlink"):
                self.validate()

    def test_source_ancestor_symlink_is_rejected(self):
        skills = self.repository / "skills"
        real = self.repository / "real-skills"
        skills.rename(real)
        skills.symlink_to(real, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.validate()

    def test_source_target_overlap_is_blocked(self):
        result = manager.install_skill(self.registry, self.item, self.repository / "skills", replace_local=True)
        self.assertEqual(result["action"], "blocked")
        self.assertIn("overlap", result["reason"])
        result = manager.install_skill(self.registry, self.item, self.source / "nested", replace_local=True)
        self.assertEqual(result["action"], "blocked")
        self.assertFalse((self.source / "nested").exists())

    def test_target_inside_other_skill_or_repository_is_blocked_without_source_writes(self):
        other = self.make_skill("other-skill")
        self.payload["skills"].append(other)
        self.save_registry()
        before = {str(p.relative_to(self.repository)): p.read_bytes()
                  for p in self.repository.rglob("*") if p.is_file()}
        for directory in (self.repository / "skills" / "other-skill", self.source,
                          self.repository, self.repository / "skills"):
            with self.subTest(directory=directory):
                result = manager.install_skill(self.registry, self.item, directory, replace_local=True)
                self.assertEqual(result["action"], "blocked")
        with self.assertRaisesRegex(ValueError, "overlap"):
            manager._safe_target(self.source, self.source.parent)
        after = {str(p.relative_to(self.repository)): p.read_bytes()
                 for p in self.repository.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_backup_root_symlink_or_file_blocks_before_writing(self):
        external = self.root / "external-backups"
        external.mkdir()
        backup_root = manager._backup_root(self.target)
        backup_root.parent.mkdir(parents=True)
        backup_root.symlink_to(external, target_is_directory=True)
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")
        self.assertFalse(self.target.exists())
        self.assertEqual(list(external.iterdir()), [])
        backup_root.unlink()
        backup_root.write_text("keep file")
        self.assertEqual(self.install(replace_local=True)["action"], "blocked")
        self.assertEqual(backup_root.read_text(), "keep file")

    def test_codex_home_mapping_and_explicit_override(self):
        home = self.root / "codex-custom"
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(home)}):
            self.assertEqual(manager.resolve_target(self.item["install_target"]), home / "skills" / "demo")
            self.assertEqual(manager.resolve_target(self.item["install_target"], self.runtime), self.target)
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(manager.Path, "home", return_value=self.root):
            self.assertEqual(manager.resolve_target(self.item["install_target"]), self.root / ".codex" / "skills" / "demo")

    def test_relative_codex_home_and_relative_skills_dir_are_rejected(self):
        with mock.patch.dict(os.environ, {"CODEX_HOME": "relative"}):
            with self.assertRaisesRegex(ValueError, "absolute"):
                manager.resolve_target(self.item["install_target"])
        with self.assertRaisesRegex(ValueError, "absolute"):
            manager.resolve_target(self.item["install_target"], Path("relative"))

    def test_registry_rejects_duplicates_malformed_entries_and_target_escapes(self):
        invalid = [
            [],
            {"schema_version": "2", "skills": []},
            {"schema_version": "1.0", "skills": ["demo"]},
            {"schema_version": "1.0", "skills": [self.item, self.item]},
        ]
        for key, value in (("name", "../demo"), ("source", "../skills/demo"),
                           ("source", "skills/other"), ("install_target", "/tmp/demo"),
                           ("install_target", "~/.codex/skills/../demo"), ("prerequisites", "text"),
                           ("required_for", [1]), ("summary", 1), ("version_policy", "made-up")):
            invalid.append({"schema_version": "1.0", "skills": [{**self.item, key: value}]})
        for payload in invalid:
            with self.subTest(payload=payload):
                self.registry.write_text(json.dumps(payload))
                with self.assertRaises(ValueError):
                    manager.load_registry(self.registry)

    def test_registry_detects_unregistered_directory(self):
        (self.repository / "skills" / "unregistered").mkdir()
        with self.assertRaisesRegex(ValueError, "unregistered"):
            self.validate()

    def test_registry_detects_registered_missing_skill_file(self):
        (self.source / "SKILL.md").unlink()
        with self.assertRaisesRegex(ValueError, "missing SKILL.md"):
            self.validate()

    def test_frontmatter_requires_matching_name_and_description(self):
        skill = self.source / "SKILL.md"
        for content in ("# Missing frontmatter", "---\nname: wrong\ndescription: Test\n---\n",
                        "---\nname: demo\n---\n"):
            with self.subTest(content=content):
                skill.write_text(content)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_folded_frontmatter_description_is_supported(self):
        (self.source / "SKILL.md").write_text("---\nname: 'demo'\ndescription: >-\n  Useful\n  fixture.\n---\n")
        self.assertEqual(len(self.validate()[0]), 1)

    def add_document(self):
        document = self.repository / "docs" / "principle.md"
        document.parent.mkdir()
        document.write_text("# Fixture principle｜v1.2\n\nBody.\n")
        self.payload["documents"] = [{"name": "fixture-principle", "kind": "principle",
                                     "title": "Fixture principle", "version": "1.2",
                                     "source": "docs/principle.md", "when_to_use": "Tests",
                                     "sync": "read-reference"}]
        self.save_registry()
        return document

    def test_list_includes_metadata_content_version_and_reference_documents(self):
        self.add_document()
        code, result = self.cli("list")
        self.assertEqual(code, 0)
        self.assertIn("skills", result)
        self.assertEqual(result["skills"][0]["version"], "sha256:" + result["skills"][0]["source_digest"])
        self.assertEqual(result["skills"][0]["required_for"], ["fixture"])
        self.assertEqual(result["skills"][0]["summary"], "Fixture")
        self.assertEqual(len(result["documents"][0]["sha256"]), 64)
        self.assertFalse(self.runtime.parent.exists())

    def test_documents_check_title_version_existence_and_relative_source(self):
        document = self.add_document()
        document.write_text("# Fixture principle｜v9.9\n")
        with self.assertRaisesRegex(ValueError, "title/version"):
            self.validate()
        document.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.validate()
        self.payload["documents"][0]["source"] = "../private.md"
        self.save_registry()
        with self.assertRaisesRegex(ValueError, "inside"):
            self.validate()

    def test_document_symlink_is_not_followed(self):
        document = self.add_document()
        document.unlink()
        document.symlink_to(self.registry)
        with self.assertRaisesRegex(ValueError, "symlink"):
            self.validate()

    def test_validate_does_not_access_runtime_or_require_valid_codex_home(self):
        code, result = self.cli("validate", env={"CODEX_HOME": "relative-invalid-for-runtime"})
        self.assertEqual(code, 0)
        self.assertNotIn("target", result["skills"][0])
        self.assertFalse(self.runtime.parent.exists())

    def test_legacy_no_name_install_and_check_exit_codes(self):
        second = self.make_skill("second")
        self.payload["skills"].append(second)
        self.save_registry()
        self.assertEqual(self.cli("check")[0], 2)
        code, result = self.cli("install")
        self.assertEqual(code, 0)
        self.assertEqual(len(result["skills"]), 2)
        self.assertEqual(self.cli("check")[0], 0)
        self.assertEqual(self.cli("check", "unknown")[0], 3)

    def test_preexisting_same_timestamp_backup_is_preserved(self):
        self.local_copy()
        old = manager._backup_root(self.target) / ".demo.backup-20000101T000000Z"
        old.mkdir(parents=True)
        (old / "keep").write_text("older backup")
        result = self.install(replace_local=True)
        self.assertEqual((old / "keep").read_text(), "older backup")
        self.assertNotEqual(Path(result["backup"]), old)
        self.assertEqual((Path(result["backup"]) / "data.txt").read_text(), "local")

    def test_backup_allocation_failure_preserves_target_and_previous_backup(self):
        self.local_copy()
        old = manager._backup_root(self.target) / ".demo.backup-existing"
        old.mkdir(parents=True)
        (old / "keep").write_text("older")
        real = manager.tempfile.mkdtemp

        def allocate(*args, **kwargs):
            if ".backup-" in kwargs.get("prefix", ""):
                raise FileExistsError("forced collision")
            return real(*args, **kwargs)

        with mock.patch.object(manager.tempfile, "mkdtemp", side_effect=allocate):
            with self.assertRaises(FileExistsError):
                self.install(replace_local=True)
        self.assertEqual((self.target / "data.txt").read_text(), "local")
        self.assertEqual((old / "keep").read_text(), "older")
        self.assertFalse(list(self.runtime.glob(".demo.installing-*")))

    def test_backup_rename_failure_does_not_remove_current_target(self):
        self.local_copy()
        real = Path.rename

        def rename(path, destination):
            if path == self.target:
                raise OSError("forced backup rename failure")
            return real(path, destination)

        with mock.patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.install(replace_local=True)
        self.assertEqual((self.target / "data.txt").read_text(), "local")
        self.assertEqual(list(manager._backup_root(self.target).iterdir()), [])

    def test_stage_rename_failure_restores_current_target(self):
        self.local_copy()
        real = Path.rename

        def rename(path, destination):
            if ".installing-" in str(path):
                raise OSError("forced stage rename failure")
            return real(path, destination)

        with mock.patch.object(Path, "rename", rename):
            with self.assertRaises(OSError):
                self.install(replace_local=True)
        self.assertEqual((self.target / "data.txt").read_text(), "local")
        self.assertEqual(list(manager._backup_root(self.target).iterdir()), [])

    def readback_failure(self):
        real = manager.check_skill
        calls = 0

        def check(*args, **kwargs):
            nonlocal calls
            calls += 1
            result = real(*args, **kwargs)
            return {**result, "status": "drifted"} if calls == 3 else result
        return mock.patch.object(manager, "check_skill", side_effect=check)

    def test_readback_failure_restores_original_and_preserves_receipt(self):
        self.install()
        original_receipt = self.receipt_path().read_bytes()
        (self.source / "data.txt").write_text("source-v2")
        with self.readback_failure(), self.assertRaisesRegex(RuntimeError, "readback"):
            self.install()
        self.assertEqual((self.target / "data.txt").read_text(), "source-v1")
        self.assertEqual(original_receipt, self.receipt_path().read_bytes())

    def test_first_install_readback_failure_removes_new_target(self):
        with self.readback_failure(), self.assertRaisesRegex(RuntimeError, "readback"):
            self.install()
        self.assertFalse(self.target.exists())
        self.assertFalse(self.receipt_path().exists())

    def test_receipt_write_failure_rolls_back_initial_and_existing_installs(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                if existing:
                    self.local_copy()
                with mock.patch.object(manager, "_write_receipt", side_effect=OSError("forced receipt failure")):
                    with self.assertRaises(OSError):
                        self.install(replace_local=True)
                if existing:
                    self.assertEqual((self.target / "data.txt").read_text(), "local")
                else:
                    self.assertFalse(self.target.exists())
                self.assertFalse(self.receipt_path().exists())

    def test_source_change_while_staging_aborts_without_replacing_target(self):
        self.local_copy()
        real = shutil.copytree

        def copy(*args, **kwargs):
            result = real(*args, **kwargs)
            (self.source / "data.txt").write_text("changed during copy")
            return result

        with mock.patch.object(manager.shutil, "copytree", side_effect=copy):
            with self.assertRaisesRegex(RuntimeError, "changed while preparing"):
                self.install(replace_local=True)
        self.assertEqual((self.target / "data.txt").read_text(), "local")

    def test_target_change_while_staging_preserves_new_local_content(self):
        self.local_copy()
        real = shutil.copytree

        def copy(*args, **kwargs):
            result = real(*args, **kwargs)
            (self.target / "data.txt").write_text("concurrent change")
            return result

        with mock.patch.object(manager.shutil, "copytree", side_effect=copy):
            with self.assertRaisesRegex(RuntimeError, "changed while preparing"):
                self.install(replace_local=True)
        self.assertEqual((self.target / "data.txt").read_text(), "concurrent change")

    def test_malformed_or_wrong_target_receipt_cannot_authorize_update(self):
        self.install()
        for content in ("not json", "[]", json.dumps({"schema_version": "1.0", "name": "demo",
                                                     "target": "/different", "source_digest": "a" * 64})):
            with self.subTest(content=content):
                self.receipt_path().write_text(content)
                (self.source / "data.txt").write_text("source-v2")
                self.assertEqual(self.install()["action"], "blocked")


if __name__ == "__main__":
    unittest.main()
