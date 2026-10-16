"""Keep the public entry point consistent with its sole distribution catalog."""

import importlib.util
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("render_catalog", ROOT / "scripts/render_catalog.py")
catalog = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(catalog)


class CatalogTests(unittest.TestCase):
    def test_readme_is_current_registry_projection(self):
        registry = json.loads((ROOT / "portable-skill-registry.json").read_text(encoding="utf-8"))
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertEqual(readme, catalog.updated_readme(readme, catalog.render(registry)))

    def test_entrypoint_local_links_are_readable(self):
        for document in [ROOT / "README.md", ROOT / "AGENTS.md", *ROOT.glob("docs/**/*.md")]:
            text = document.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", text):
                if ":" in link or link.startswith("#"):
                    continue
                target = document.parent / link.split("#", 1)[0]
                with self.subTest(document=str(document.relative_to(ROOT)), link=link):
                    self.assertTrue(target.exists())


if __name__ == "__main__":
    unittest.main()
