from __future__ import annotations

from pathlib import Path
import plistlib
import tempfile
import unittest
from unittest.mock import patch

from printtopdf.config import AppConfig
from printtopdf.launchd import install_launch_agent


class LaunchdTests(unittest.TestCase):
    def test_install_launch_agent_writes_expected_plist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            project_root = home / "project"
            project_root.mkdir()
            config = AppConfig(
                config_path=project_root / "config.toml",
                printer_name="LAN PDF Printer",
                output_dir=project_root / "output",
                spool_dir=project_root / "spool",
                port=8631,
                location="Desk",
                log_file=project_root / "logs" / "printer.log",
            )
            with patch("pathlib.Path.home", return_value=home):
                plist_path = install_launch_agent(config, project_root=project_root, load=False)

            self.assertTrue(plist_path.exists())
            with plist_path.open("rb") as handle:
                payload = plistlib.load(handle)
            self.assertEqual(payload["Label"], "com.printtopdf.remote-printer")
            self.assertEqual(payload["WorkingDirectory"], str(project_root))
            self.assertEqual(payload["EnvironmentVariables"]["PYTHONPATH"], str(project_root))
            self.assertEqual(payload["ProgramArguments"][3:], ["run", "--config", str(config.config_path)])


if __name__ == "__main__":
    unittest.main()
