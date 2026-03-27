from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import unicodedata

from pypdf import PdfReader, PdfWriter

from .config import AppConfig


PDF_MAGIC = b"%PDF-"


@dataclass(frozen=True)
class JobContext:
    content_type: str
    job_id: str
    job_name: str
    metadata: dict[str, str]


def required_command(name: str) -> str:
    command = shutil.which(name)
    if not command:
        raise RuntimeError(f"required command not found: {name}")
    return command


def ensure_runtime_paths(config: AppConfig) -> None:
    ensure_directory(config.output_dir)
    ensure_directory(config.spool_dir)
    ensure_directory(config.log_file.parent)


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    if not path.is_dir():
        raise RuntimeError(f"{path} exists but is not a directory")
    if not os.access(path, os.W_OK):
        raise RuntimeError(f"{path} is not writable")


def local_hostname() -> str:
    try:
        result = subprocess.run(
            ["scutil", "--get", "LocalHostName"],
            check=True,
            capture_output=True,
            text=True,
        )
        hostname = result.stdout.strip()
        if hostname:
            return hostname
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    hostname = socket.gethostname().split(".")[0]
    return hostname or "localhost"


def printer_uri(config: AppConfig) -> str:
    return f"ipp://{local_hostname()}.local:{config.port}/ipp/print"


def collect_job_context(env: dict[str, str]) -> JobContext:
    metadata = {key: value for key, value in env.items() if key.startswith("IPP_")}
    content_type = env.get("CONTENT_TYPE", "")
    job_id = env.get("IPP_JOB_ID", "unknown")
    for key in ("IPP_JOB_NAME", "IPP_DOCUMENT_NAME_SUPPLIED", "IPP_JOB_NAME_SUPPLIED"):
        value = env.get(key)
        if value:
            job_name = value
            break
    else:
        job_name = "untitled"

    return JobContext(
        content_type=content_type,
        job_id=job_id,
        job_name=job_name,
        metadata=metadata,
    )


def sanitize_job_name(raw: str, limit: int = 80) -> str:
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("._-")
    if not normalized:
        normalized = "untitled"
    return normalized[:limit].rstrip("._-") or "untitled"


def is_pdf_bytes(payload: bytes) -> bool:
    return payload.startswith(PDF_MAGIC)


def build_output_filename(job: JobContext, now: datetime | None = None) -> str:
    timestamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{job.job_id}-{sanitize_job_name(job.job_name)}.pdf"


def unique_output_path(output_dir: Path, filename: str) -> Path:
    candidate = output_dir / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    counter = 2
    while True:
        alternative = output_dir / f"{stem}-{counter}{suffix}"
        if not alternative.exists():
            return alternative
        counter += 1


def write_pdf_atomically(output_dir: Path, filename: str, payload: bytes) -> Path:
    destination = unique_output_path(output_dir, filename)
    with tempfile.NamedTemporaryFile(dir=output_dir, prefix=".incoming-", suffix=".pdf", delete=False) as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
        tmp_path = Path(handle.name)

    tmp_path.replace(destination)
    return destination


def reverse_pdf_page_order(payload: bytes) -> bytes:
    reader = PdfReader(BytesIO(payload))
    writer = PdfWriter()
    for page in reversed(reader.pages):
        writer.add_page(page)

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


def append_log(log_file: Path, event: str, **fields: object) -> None:
    ensure_directory(log_file.parent)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        **fields,
    }
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
