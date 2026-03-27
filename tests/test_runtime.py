from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
import tempfile
import unittest

from pypdf import PdfReader, PdfWriter

from printtopdf.runtime import build_output_filename, collect_job_context, is_pdf_bytes, reverse_pdf_page_order, sanitize_job_name, write_pdf_atomically


FIXTURE = Path(__file__).parent / "fixtures" / "minimal.pdf"


class RuntimeTests(unittest.TestCase):
    def test_sanitize_job_name(self) -> None:
        self.assertEqual(sanitize_job_name("Quarterly Report (Final).pdf"), "quarterly-report-final-.pdf")
        self.assertEqual(sanitize_job_name("   "), "untitled")
        self.assertEqual(sanitize_job_name("Résumé 2026"), "resume-2026")

    def test_is_pdf_bytes(self) -> None:
        self.assertTrue(is_pdf_bytes(FIXTURE.read_bytes()))
        self.assertFalse(is_pdf_bytes(b"not a pdf"))

    def test_collect_job_context(self) -> None:
        env = {
            "CONTENT_TYPE": "application/pdf",
            "IPP_JOB_ID": "42",
            "IPP_JOB_NAME": "Inbox Label",
            "IPP_MEDIA": "na_letter_8.5x11in",
        }
        job = collect_job_context(env)
        self.assertEqual(job.content_type, "application/pdf")
        self.assertEqual(job.job_id, "42")
        self.assertEqual(job.job_name, "Inbox Label")
        self.assertEqual(job.metadata["IPP_MEDIA"], "na_letter_8.5x11in")

    def test_build_output_filename(self) -> None:
        job = collect_job_context(
            {
                "CONTENT_TYPE": "application/pdf",
                "IPP_JOB_ID": "12",
                "IPP_JOB_NAME": "Print Me",
            }
        )
        self.assertEqual(
            build_output_filename(job, now=datetime(2026, 3, 26, 12, 45, 0)),
            "20260326-124500-12-print-me.pdf",
        )

    def test_write_pdf_atomically_handles_collisions(self) -> None:
        payload = FIXTURE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            first = write_pdf_atomically(output_dir, "sample.pdf", payload)
            second = write_pdf_atomically(output_dir, "sample.pdf", payload)
            self.assertEqual(first.name, "sample.pdf")
            self.assertEqual(second.name, "sample-2.pdf")
            self.assertEqual(first.read_bytes(), payload)
            self.assertEqual(second.read_bytes(), payload)

    def test_reverse_pdf_page_order(self) -> None:
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.add_blank_page(width=200, height=100)
        payload = BytesIO()
        writer.write(payload)

        reversed_payload = reverse_pdf_page_order(payload.getvalue())
        reader = PdfReader(BytesIO(reversed_payload))
        widths = [float(page.mediabox.width) for page in reader.pages]
        self.assertEqual(widths, [200.0, 100.0])


if __name__ == "__main__":
    unittest.main()
