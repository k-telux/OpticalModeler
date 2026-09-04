"""Validation must fail before assertion-disabling interpreter modes can bypass it."""

import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / "scripts/validate_repository.py",
    ROOT / "skills/thorlabs-blender-optical-path/scripts/workflow_ledger.py",
)


class ValidationRuntimeTest(unittest.TestCase):
    def test_optimized_cli_refuses_validation(self):
        for script in SCRIPTS:
            for flag in ("-O", "-OO", None):
                with self.subTest(script=script.name, flag=flag):
                    env = os.environ.copy()
                    env.pop("PYTHONOPTIMIZE", None)
                    if flag is None:
                        env["PYTHONOPTIMIZE"] = "1"
                    command = [sys.executable, "-B"] + ([flag] if flag else []) + [str(script)]
                    result = subprocess.run(command, env=env, capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("validation assertions must remain enabled", result.stderr)
                    self.assertNotIn("PASS", result.stdout)

    def test_optimized_library_load_also_refuses_validation(self):
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    [sys.executable, "-B", "-O", "-c", "import runpy, sys; runpy.run_path(sys.argv[1])", str(script)],
                    capture_output=True, text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("validation assertions must remain enabled", result.stderr)


if __name__ == "__main__":
    unittest.main()
