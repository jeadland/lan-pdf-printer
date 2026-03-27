from __future__ import annotations

from pathlib import Path
import os
import plistlib
import subprocess
import sys

from .config import AppConfig


def install_launch_agent(config: AppConfig, project_root: Path, load: bool = True) -> Path:
    launch_agents = Path.home() / "Library" / "LaunchAgents"
    launch_agents.mkdir(parents=True, exist_ok=True)
    plist_path = launch_agents / f"{config.launch_agent_label}.plist"

    plist = {
        "Label": config.launch_agent_label,
        "ProgramArguments": [
            sys.executable,
            "-m",
            "printtopdf",
            "run",
            "--config",
            str(config.config_path),
        ],
        "EnvironmentVariables": {
            "PYTHONPATH": str(project_root),
        },
        "WorkingDirectory": str(project_root),
        "KeepAlive": True,
        "RunAtLoad": True,
        "StandardOutPath": str(config.log_file),
        "StandardErrorPath": str(config.log_file),
    }

    with plist_path.open("wb") as handle:
        plistlib.dump(plist, handle, sort_keys=True)

    if load:
        _load_launch_agent(plist_path, config.launch_agent_label)

    return plist_path


def _load_launch_agent(plist_path: Path, label: str) -> None:
    uid = str(os.getuid())
    domain = f"gui/{uid}"
    subprocess.run(["launchctl", "bootout", domain, str(plist_path)], check=False, capture_output=True)
    subprocess.run(["launchctl", "bootstrap", domain, str(plist_path)], check=True, capture_output=True)
    subprocess.run(["launchctl", "enable", f"{domain}/{label}"], check=False, capture_output=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{label}"], check=False, capture_output=True)

