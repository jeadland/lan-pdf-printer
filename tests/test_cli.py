from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from printtopdf.cli import _write_hook_launcher
from printtopdf.config import AppConfig


class CliTests(unittest.TestCase):
    def test_hook_launcher_forwards_spooled_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = AppConfig(
                config_path=root / "config.toml",
                printer_name="Printer",
                output_dir=root / "output",
                spool_dir=root / "spool",
                port=8631,
                location="Desk",
                log_file=root / "logs" / "printer.log",
            )
            config.spool_dir.mkdir(parents=True, exist_ok=True)
            launcher = _write_hook_launcher(config)
            contents = launcher.read_text(encoding="utf-8")
            self.assertIn('"$@"', contents)


if __name__ == "__main__":
    unittest.main()
