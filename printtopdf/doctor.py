from __future__ import annotations

from contextlib import suppress
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time

from .config import AppConfig
from .runtime import ensure_runtime_paths, printer_uri, required_command


def run_doctor(config: AppConfig, timeout: float = 6.0) -> int:
    ensure_runtime_paths(config)
    ippeveprinter = required_command("ippeveprinter")
    required_command("dns-sd")
    ipptool = shutil.which("ipptool")

    print(f"Config:      {config.config_path}")
    print(f"Printer:     {config.printer_name}")
    print(f"Output dir:  {config.output_dir}")
    print(f"Spool dir:   {config.spool_dir}")
    print(f"Log file:    {config.log_file}")
    print(f"IPP URI:     {printer_uri(config)}")
    print(f"ipptool:     {ipptool or 'not found'}")

    if _printer_is_discoverable(config.printer_name, timeout=timeout):
        print("DNS-SD:      visible")
        return 0

    if _port_is_open(config.port):
        print("DNS-SD:      not visible; port is already in use, so no probe was started")
        return 1

    print("DNS-SD:      probing temporary advertisement")
    exit_code = _probe_dns_sd(config, ippeveprinter, timeout=timeout)
    if exit_code == 0:
        print("DNS-SD:      visible")
    else:
        print("DNS-SD:      probe failed")
    return exit_code


def _printer_is_discoverable(printer_name: str, timeout: float) -> bool:
    browse = subprocess.Popen(
        ["dns-sd", "-B", "_ipp._tcp", "local."],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        try:
            output, _ = browse.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            browse.terminate()
            output, _ = browse.communicate(timeout=2)
        return printer_name in output
    finally:
        with suppress(ProcessLookupError):
            browse.terminate()
        with suppress(subprocess.TimeoutExpired):
            browse.wait(timeout=2)


def _probe_dns_sd(config: AppConfig, ippeveprinter: str, timeout: float) -> int:
    probe_dir = Path(tempfile.mkdtemp(prefix="doctor-", dir=config.spool_dir))
    process = subprocess.Popen(
        [
            ippeveprinter,
            "-2",
            "-f",
            "application/pdf",
            "-F",
            "application/pdf",
            "-d",
            str(probe_dir),
            "-c",
            "/usr/bin/true",
            "-k",
            "-l",
            config.location,
            "-p",
            str(config.port),
            "-s",
            "20,20",
            config.printer_name,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        time.sleep(1.5)
        return 0 if _printer_is_discoverable(config.printer_name, timeout=timeout) else 1
    finally:
        with suppress(ProcessLookupError):
            process.terminate()
        with suppress(subprocess.TimeoutExpired):
            process.wait(timeout=2)


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0
