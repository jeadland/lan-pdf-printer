from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import tomllib


DEFAULT_CONFIG_PATH = Path("config.toml")


@dataclass(frozen=True)
class AppConfig:
    config_path: Path
    printer_name: str
    output_dir: Path
    spool_dir: Path
    port: int
    location: str
    log_file: Path

    @property
    def launch_agent_label(self) -> str:
        return "com.printtopdf.remote-printer"


def resolve_path(raw: str) -> Path:
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return Path(expanded).expanduser().resolve()


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path or os.environ.get("PRINTTOPDF_CONFIG", DEFAULT_CONFIG_PATH)).expanduser().resolve()
    with config_path.open("rb") as handle:
        data = tomllib.load(handle)

    return AppConfig(
        config_path=config_path,
        printer_name=_required_string(data, "printer_name"),
        output_dir=resolve_path(_required_string(data, "output_dir")),
        spool_dir=resolve_path(_required_string(data, "spool_dir")),
        port=_required_int(data, "port"),
        location=_required_string(data, "location"),
        log_file=resolve_path(_required_string(data, "log_file")),
    )


def _required_string(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"config key '{key}' must be a non-empty string")
    return value


def _required_int(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise ValueError(f"config key '{key}' must be an integer")
    return value

