from __future__ import annotations

from pathlib import Path
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest


FIXTURE = Path(__file__).parent / "fixtures" / "minimal.pdf"
PACKAGE_ROOT = Path(__file__).resolve().parent.parent


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@unittest.skipUnless(os.environ.get("RUN_IPP_TESTS") == "1", "set RUN_IPP_TESTS=1 to run IPP integration tests")
class IntegrationTests(unittest.TestCase):
    def test_local_print_job_is_saved(self) -> None:
        if not shutil.which("ipptool"):
            self.skipTest("ipptool is not installed")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            port = find_free_port()
            config = tmp_path / "config.toml"
            output_dir = tmp_path / "output"
            spool_dir = tmp_path / "spool"
            log_file = tmp_path / "logs" / "printer.log"
            config.write_text(
                "\n".join(
                    [
                        'printer_name = "Integration Test Printer"',
                        f'output_dir = "{output_dir}"',
                        f'spool_dir = "{spool_dir}"',
                        f"port = {port}",
                        'location = "Desk"',
                        f'log_file = "{log_file}"',
                    ]
                ),
                encoding="utf-8",
            )
            request = tmp_path / "print-job.test"
            request.write_text(
                "\n".join(
                    [
                        "{",
                        'NAME "Print PDF"',
                        "OPERATION Print-Job",
                        "GROUP operation-attributes-tag",
                        'ATTR charset attributes-charset utf-8',
                        'ATTR language attributes-natural-language en',
                        'ATTR uri printer-uri "$uri"',
                        'ATTR name requesting-user-name "printtopdf-test"',
                        'ATTR mimeMediaType document-format application/pdf',
                        f'FILE "{FIXTURE}"',
                        "STATUS successful-ok",
                        "}",
                    ]
                ),
                encoding="utf-8",
            )

            env = os.environ.copy()
            env["PYTHONPATH"] = str(PACKAGE_ROOT)
            process = subprocess.Popen(
                [sys.executable, "-m", "printtopdf", "--config", str(config), "run"],
                cwd=PACKAGE_ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            try:
                time.sleep(3)
                result = subprocess.run(
                    ["ipptool", "-tv", f"ipp://127.0.0.1:{port}/ipp/print", str(request)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    saved = list(output_dir.glob("*.pdf"))
                    if saved:
                        break
                    time.sleep(0.25)
                else:
                    self.fail("timed out waiting for saved PDF")

                self.assertEqual(len(saved), 1)
                self.assertTrue(saved[0].read_bytes().startswith(b"%PDF-"))
            finally:
                process.terminate()
                process.wait(timeout=5)
                if process.stdout is not None:
                    process.stdout.close()


if __name__ == "__main__":
    unittest.main()
