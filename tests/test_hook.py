from __future__ import annotations

from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


FIXTURE = Path(__file__).parent / "fixtures" / "minimal.pdf"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


class HookTests(unittest.TestCase):
    def test_hook_saves_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = tmp_path / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        'printer_name = "Test Printer"',
                        f'output_dir = "{tmp_path / "output"}"',
                        f'spool_dir = "{tmp_path / "spool"}"',
                        "port = 8631",
                        'location = "Desk"',
                        f'log_file = "{tmp_path / "logs" / "printer.log"}"',
                    ]
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PACKAGE_ROOT)
            env["CONTENT_TYPE"] = "application/pdf"
            env["IPP_JOB_ID"] = "99"
            env["IPP_JOB_NAME"] = "Saved By Hook"
            result = subprocess.run(
                [sys.executable, "-m", "printtopdf", "hook", "--config", str(config)],
                input=FIXTURE.read_bytes(),
                env=env,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            output_dir = tmp_path / "output"
            saved = list(output_dir.glob("*.pdf"))
            self.assertEqual(len(saved), 1)
            self.assertTrue(saved[0].read_bytes().startswith(b"%PDF-"))

    def test_hook_rejects_non_pdf_content_type(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = tmp_path / "config.toml"
            config.write_text(
                "\n".join(
                    [
                        'printer_name = "Test Printer"',
                        f'output_dir = "{tmp_path / "output"}"',
                        f'spool_dir = "{tmp_path / "spool"}"',
                        "port = 8631",
                        'location = "Desk"',
                        f'log_file = "{tmp_path / "logs" / "printer.log"}"',
                    ]
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PACKAGE_ROOT)
            env["CONTENT_TYPE"] = "application/postscript"
            env["IPP_JOB_ID"] = "100"
            env["IPP_JOB_NAME"] = "Rejected"
            result = subprocess.run(
                [sys.executable, "-m", "printtopdf", "hook", "--config", str(config)],
                input=FIXTURE.read_bytes(),
                env=env,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(list((tmp_path / "output").glob("*.pdf")), [])


if __name__ == "__main__":
    unittest.main()
