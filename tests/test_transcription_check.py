"""Exercise dependency checks with fake tools; never invoke real installers."""

import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills/analyze-showroom-sales-recording/scripts/ensure_local_transcription.sh"
)


class TranscriptionCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.install_log = self.root / "install.log"
        self.env = {
            "PATH": str(self.bin),
            "INSTALL_LOG": str(self.install_log),
            "FAKE_PLATFORM": "Darwin",
            "FAKE_MACHINE": "arm64",
        }
        self.command(
            "uname",
            'if [ "$1" = "-s" ]; then printf "%s\\n" "${FAKE_PLATFORM:-Darwin}"; '
            'else printf "%s\\n" "${FAKE_MACHINE:-arm64}"; fi',
        )
        for installer in ("brew", "uv"):
            self.command(
                installer,
                f'printf "%s\\n" "{installer} $*" >> "$INSTALL_LOG"; exit 97',
            )
        self.command("head", 'IFS= read -r line; printf "%s\\n" "$line"')

    def command(self, name, body):
        command_path = self.bin / name
        command_path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        command_path.chmod(0o700)

    def ready_tools(self):
        self.command("ffmpeg", 'printf "%s\\n" "ffmpeg fixture"')
        self.command("mlx_whisper", "exit 0")

    def run_script(self, *arguments):
        return subprocess.run(
            ["/bin/bash", str(SCRIPT), *arguments],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_no_installer_called(self):
        self.assertFalse(self.install_log.exists(), "check mode invoked an installer")

    def test_check_succeeds_with_existing_tools_without_installing(self):
        self.ready_tools()
        result = self.run_script("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dependencies are ready", result.stdout)
        self.assert_no_installer_called()

    def test_check_reports_missing_tools_without_installing(self):
        result = self.run_script("--check")
        self.assertEqual(result.returncode, 3)
        self.assertIn("ffmpeg mlx_whisper", result.stderr)
        self.assertIn("does not install", result.stderr)
        self.assert_no_installer_called()

    def test_check_reports_only_the_missing_tool(self):
        self.command("ffmpeg", "exit 0")
        result = self.run_script("--check")
        self.assertEqual(result.returncode, 3)
        self.assertIn("dependencies: mlx_whisper", result.stderr)
        self.assert_no_installer_called()

    def test_unknown_or_extra_arguments_fail_before_installing(self):
        for arguments in (("--unknown",), ("--check", "extra"), ("",)):
            with self.subTest(arguments=arguments):
                result = self.run_script(*arguments)
                self.assertEqual(result.returncode, 64)
                self.assertIn("Usage:", result.stderr)
                self.assert_no_installer_called()

    def test_unsupported_platform_fails_without_installing(self):
        self.env["FAKE_PLATFORM"] = "Linux"
        result = self.run_script("--check")
        self.assertEqual(result.returncode, 2)
        self.assert_no_installer_called()

    def test_legacy_no_argument_command_still_uses_install_path(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 97)
        self.assertEqual(self.install_log.read_text(encoding="utf-8"), "brew install ffmpeg\n")


if __name__ == "__main__":
    unittest.main()
