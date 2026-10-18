"""Keep the optional Codex package aligned with the existing Skill registry."""

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PluginMarketplaceTests(unittest.TestCase):
    def setUp(self):
        self.plugin = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        self.marketplace = json.loads(
            (ROOT / ".agents/plugins/marketplace.json").read_text(encoding="utf-8")
        )
        self.registry = json.loads(
            (ROOT / "portable-skill-registry.json").read_text(encoding="utf-8")
        )

    def test_portable_manifest_has_stable_identity_and_display(self):
        self.assertEqual(
            self.plugin["$schema"],
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        )
        self.assertRegex(self.plugin["name"], r"^[a-z][a-z0-9-]*$")
        self.assertRegex(self.plugin["version"], r"^\d+\.\d+\.\d+$")
        self.assertTrue(self.plugin["description"].strip())
        self.assertTrue(self.plugin["author"]["name"].strip())
        interface = self.plugin["extensions"]["com.openai"]["interface"]
        self.assertTrue(interface["displayName"].strip())
        self.assertTrue(interface["shortDescription"].strip())

    def test_marketplace_resolves_this_package_without_auto_install(self):
        self.assertEqual(self.marketplace["name"], "leo-team")
        self.assertTrue(self.marketplace["interface"]["displayName"].strip())
        self.assertEqual(len(self.marketplace["plugins"]), 1)
        entry = self.marketplace["plugins"][0]
        self.assertEqual(entry["name"], self.plugin["name"])
        self.assertEqual(entry["source"], {"source": "local", "path": "./"})
        self.assertEqual((ROOT / entry["source"]["path"]).resolve(), ROOT)
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")
        self.assertEqual(entry["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(entry["category"], "Productivity")

    def test_discovered_skills_are_exactly_the_registered_sources(self):
        registered = {item["source"] for item in self.registry["skills"]}
        discovered = {
            path.parent.relative_to(ROOT).as_posix()
            for path in (ROOT / "skills").glob("*/SKILL.md")
        }
        self.assertEqual(discovered, registered)
        for item in self.registry["skills"]:
            with self.subTest(skill=item["name"]):
                self.assertEqual(item["source"], "skills/" + item["name"])
                self.assertTrue((ROOT / item["source"] / "SKILL.md").is_file())
        self.assertFalse(list((ROOT / "docs").rglob("SKILL.md")))

    def test_package_adds_no_mcp_hooks_or_global_rule_changes(self):
        for path in ["mcp.json", ".mcp.json", ".app.json", "hooks/hooks.json", ".codex/config.toml"]:
            with self.subTest(path=path):
                self.assertFalse((ROOT / path).exists())
        openai = self.plugin["extensions"]["com.openai"]
        self.assertEqual(set(openai), {"interface"})
        self.assertNotIn("license", self.plugin)

    def test_readme_uses_the_real_marketplace_and_plugin_names(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        identifier = self.plugin["name"] + "@" + self.marketplace["name"]
        self.assertIn("codex plugin add " + identifier, readme)
        self.assertIn("codex plugin marketplace upgrade " + self.marketplace["name"], readme)
        self.assertIsNotNone(re.search(r"仓库.*公开", readme))


if __name__ == "__main__":
    unittest.main()
