from __future__ import annotations

import argparse
import os
import sys

from .config import load_config
from .runtime import append_log, build_output_filename, collect_job_context, ensure_runtime_paths, is_pdf_bytes, reverse_pdf_page_order, write_pdf_atomically


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="printtopdf hook")
    parser.add_argument("--config", required=True, help="Path to config.toml")
    parser.add_argument("document_path", nargs="?", help=argparse.SUPPRESS)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    ensure_runtime_paths(config)
    job = collect_job_context(dict(os.environ))
    if args.document_path:
        with open(args.document_path, "rb") as handle:
            payload = handle.read()
    else:
        payload = sys.stdin.buffer.read()

    if job.content_type != "application/pdf":
        append_log(
            config.log_file,
            "job_rejected",
            reason="unsupported_content_type",
            content_type=job.content_type,
            job_id=job.job_id,
            job_name=job.job_name,
            metadata=job.metadata,
        )
        return 1

    if not is_pdf_bytes(payload):
        append_log(
            config.log_file,
            "job_rejected",
            reason="invalid_pdf_payload",
            content_type=job.content_type,
            job_id=job.job_id,
            job_name=job.job_name,
            metadata=job.metadata,
        )
        return 1

    reordered = False
    if job.metadata.get("IPP_OUTPUT_BIN") == "face-up":
        payload = reverse_pdf_page_order(payload)
        reordered = True

    destination = write_pdf_atomically(config.output_dir, build_output_filename(job), payload)
    append_log(
        config.log_file,
        "job_saved",
        content_type=job.content_type,
        destination=str(destination),
        job_id=job.job_id,
        job_name=job.job_name,
        metadata=job.metadata,
        page_order_normalized=reordered,
        size_bytes=len(payload),
    )
    return 0
