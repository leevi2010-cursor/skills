"""Offline regression fixtures for the five-level tree renderer."""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/five-level-ternary-thinking/scripts/render_tree.py"
)
SPEC = importlib.util.spec_from_file_location("render_tree", SCRIPT)
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


def tree_fixture(omit_leaf_children=True):
    def node(path, depth):
        result = {
            "label": f"Question {path}",
            "detail": f"This explains the action at {path}.",
            "example": f"A person completes a practical step for {path}.",
        }
        if depth < 5:
            result["children"] = [
                node(f"{path}.{index}", depth + 1) for index in range(1, 4)
            ]
        elif not omit_leaf_children:
            result["children"] = []
        return result

    return {"title": "Offline fixture", "mode": "how", "root": node("0", 0)}


class RenderTreeTests(unittest.TestCase):
    def load_fixture(self, directory, payload):
        input_path = Path(directory) / "tree.json"
        input_path.write_text(json.dumps(payload), encoding="utf-8")
        return RENDERER.load_and_validate(input_path)

    def test_omitted_leaf_children_match_explicit_empty_children(self):
        with tempfile.TemporaryDirectory() as directory:
            omitted = self.load_fixture(directory, tree_fixture())
            explicit = self.load_fixture(directory, tree_fixture(False))
        self.assertEqual(omitted, explicit)
        leaf = omitted["root"]["children"][1]
        for _ in range(4):
            leaf = leaf["children"][0]
        self.assertEqual(leaf["children"], [])
        self.assertEqual(leaf["id"], "2.1.1.1.1")
        self.assertEqual(RENDERER.render_fragment(omitted), RENDERER.render_fragment(explicit))

    def test_nonempty_leaf_children_are_rejected(self):
        payload = tree_fixture()
        leaf = payload["root"]
        for _ in range(5):
            leaf = leaf["children"][0]
        leaf["children"] = [{"label": "Unexpected sixth level"}]
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RENDERER.TreeValidationError, "level 5 requires 0 children"):
                self.load_fixture(directory, payload)

    def test_cli_renders_omitted_leaf_children_in_a_writable_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            output_path = Path(directory) / "output" / "tree.html"
            input_path.write_text(json.dumps(tree_fixture()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "--input", str(input_path), "--output", str(output_path)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["nodes"], 364)
            self.assertIn('"id":"3.3.3.3.3"', output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
