from __future__ import annotations

import argparse
from pathlib import Path
import shlex
import signal
import subprocess
import sys

from .config import load_config
from .doctor import run_doctor
from .hook import main as hook_main
from .launchd import install_launch_agent
from .runtime import append_log, ensure_runtime_paths, printer_uri, required_command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="printtopdf")
    parser.add_argument("--config", default=None, help="Path to config.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run", help="Run the IPP printer service")
    subparsers.add_parser("doctor", help="Validate the config and DNS-SD visibility")

    install = subparsers.add_parser("install-launch-agent", help="Install and load a LaunchAgent")
    install.add_argument("--no-load", action="store_true", help="Write the plist without loading it")

    hook = subparsers.add_parser("hook", help=argparse.SUPPRESS)
    hook.add_argument("--config", required=True, help=argparse.SUPPRESS)
    hook.add_argument("document_path", nargs="?", help=argparse.SUPPRESS)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "hook":
        hook_args = ["--config", args.config]
        if args.document_path:
            hook_args.append(args.document_path)
        return hook_main(hook_args)

    config = load_config(args.config)

    if args.command == "run":
        return run_service(config)
    if args.command == "doctor":
        return run_doctor(config)
    if args.command == "install-launch-agent":
        project_root = Path(__file__).resolve().parent.parent
        plist_path = install_launch_agent(config, project_root=project_root, load=not args.no_load)
        print(plist_path)
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def run_service(config) -> int:
    ensure_runtime_paths(config)
    hook_launcher = _write_hook_launcher(config)
    ippeveprinter = required_command("ippeveprinter")
    command = [
        ippeveprinter,
        "-2",
        "-f",
        "application/pdf",
        "-F",
        "application/pdf",
        "-c",
        str(hook_launcher),
        "-d",
        str(config.spool_dir),
        "-k",
        "-l",
        config.location,
        "-p",
        str(config.port),
        "-s",
        "20,20",
        "-v",
        config.printer_name,
    ]

    append_log(
        config.log_file,
        "service_starting",
        command=command,
        printer_name=config.printer_name,
        printer_uri=printer_uri(config),
    )
    print(f"Starting {config.printer_name}")
    print(f"IPP URI: {printer_uri(config)}")
    print(f"Saving PDFs to: {config.output_dir}")
    process = subprocess.Popen(command)

    def forward(signum, _frame):
        if process.poll() is None:
            process.send_signal(signum)

    signal.signal(signal.SIGINT, forward)
    signal.signal(signal.SIGTERM, forward)
    try:
        return process.wait()
    finally:
        append_log(config.log_file, "service_stopped", return_code=process.returncode)


def _write_hook_launcher(config) -> Path:
    launcher = config.spool_dir / "printtopdf-hook"
    package_root = Path(__file__).resolve().parent.parent
    contents = [
        "#!/bin/sh",
        f"export PYTHONPATH={shlex.quote(str(package_root))}${{PYTHONPATH:+:${{PYTHONPATH}}}}",
        f"exec {shlex.quote(sys.executable)} -m printtopdf hook --config {shlex.quote(str(config.config_path))} \"$@\"",
        "",
    ]
    launcher.write_text("\n".join(contents), encoding="utf-8")
    launcher.chmod(0o755)
    return launcher
