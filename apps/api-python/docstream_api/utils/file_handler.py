import shutil
import time
import uuid
from pathlib import Path

from fastapi import UploadFile


TEMP_BASE = Path("/tmp/docstream")

# PDF magic bytes: %PDF
PDF_MAGIC = b"%PDF"


async def save_upload(file: UploadFile) -> tuple[str, Path]:
    """Save an uploaded file to a temp directory.

    Returns (job_id, pdf_path).
    Raises ValueError if the file is not a valid PDF.
    """
    contents = await file.read()

    # Validate magic bytes
    if not contents[:4].startswith(PDF_MAGIC):
        raise ValueError("Uploaded file is not a valid PDF.")

    job_id = uuid.uuid4().hex
    job_dir = TEMP_BASE / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    pdf_path = job_dir / "input.pdf"
    pdf_path.write_bytes(contents)

    return job_id, pdf_path


def get_output_dir(job_id: str) -> Path:
    """Return the output directory for a given job, creating it if needed."""
    output_dir = TEMP_BASE / job_id / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def cleanup_old_jobs(max_age_seconds: int = 3600) -> None:
    """Delete job directories older than max_age_seconds."""
    if not TEMP_BASE.exists():
        return

    now = time.time()
    for job_dir in TEMP_BASE.iterdir():
        if job_dir.is_dir():
            age = now - job_dir.stat().st_mtime
            if age > max_age_seconds:
                shutil.rmtree(job_dir, ignore_errors=True)


def read_file_as_response(path: Path) -> bytes:
    """Read a file and return its bytes."""
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_bytes()
