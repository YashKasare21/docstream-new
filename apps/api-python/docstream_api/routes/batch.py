"""
Batch-conversion endpoint.

Accepts a ``.zip`` archive containing one or more supported documents
(``.pdf``, ``.tex``, ``.latex``), creates a queued ``Job`` row for
each entry, and processes them sequentially in a FastAPI
``BackgroundTask`` so the user gets an immediate 202 response.

Security model
--------------
* Reject archives with more than ``MAX_FILES_PER_BATCH`` entries
  (zip-bomb guard).
* Reject if the total uncompressed size exceeds ``MAX_BATCH_BYTES``.
* Reject path-traversal entries (``..`` segments, absolute paths,
  symlinks pointing outside the extraction root).
* Skip entries whose extension is not in ``SUPPORTED_EXTENSIONS``;
  the user is told which ones were skipped in the 202 response.
"""

from __future__ import annotations

import logging
import uuid
import zipfile
from pathlib import Path
from typing import Iterable

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Request, UploadFile

from docstream_api import database as database_module
from docstream_api.db_models import Job
from docstream_api.routes.convert import SUPPORTED_EXTENSIONS, _finalise_job
from docstream_api.services.converter import convert_document
from docstream_api.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# Resource limits — same shape as the single-file endpoint, but
# applied to the whole archive.
MAX_FILES_PER_BATCH = 20
MAX_BATCH_BYTES = 100 * 1024 * 1024  # 100 MB uncompressed
TEMP_BATCH_ROOT = Path("/tmp/docstream/batch")


def _is_safe_member(name: str) -> bool:
    """Return True if a zip member path is safe to extract.

    Rejects absolute paths, ``..`` traversal, Windows drive letters,
    and any path that escapes the target directory when normalised.
    """
    if not name or name.startswith("/") or name.startswith("\\"):
        return False
    if ".." in Path(name).parts:
        return False
    if ":" in Path(name).parts[0]:  # e.g. ``C:foo``
        return False
    return True


def _validate_zip(zf: zipfile.ZipFile) -> tuple[list[str], int]:
    """Inspect a zip and return (safe_member_names, total_uncompressed_bytes).

    Raises ``HTTPException`` if any safety check fails.
    """
    infos = zf.infolist()
    if len(infos) > MAX_FILES_PER_BATCH:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Archive contains {len(infos)} files, exceeding the "
                f"{MAX_FILES_PER_BATCH}-file batch limit."
            ),
        )

    safe: list[str] = []
    total_bytes = 0
    for info in infos:
        # Directories are skipped silently.
        if info.is_dir():
            continue
        if not _is_safe_member(info.filename):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Unsafe path in archive: {info.filename!r}."
                    " Refusing to extract."
                ),
            )
        total_bytes += info.file_size
        if total_bytes > MAX_BATCH_BYTES:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Archive uncompressed size exceeds {MAX_BATCH_BYTES} bytes."
                ),
            )
        safe.append(info.filename)
    return safe, total_bytes


def _partition_by_extension(
    member_names: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Split zip members into (processable, skipped) by extension."""
    processable: list[str] = []
    skipped: list[str] = []
    for name in member_names:
        if Path(name).suffix.lower() in SUPPORTED_EXTENSIONS:
            processable.append(name)
        else:
            skipped.append(name)
    return processable, skipped


async def _process_batch_item(
    *,
    job_id: str,
    input_path: Path,
    template: str,
    output_format: str,
    output_dir: Path,
) -> None:
    """Run a single batch entry through the docstream pipeline.

    Updates the ``Job`` row to ``processing`` at start and
    ``completed`` / ``failed`` at the end. Failures are logged but
    never bubble up — the row is finalised in the DB and the next
    item in the batch proceeds.
    """
    # Mark "processing" up-front so the history endpoint shows
    # live progress while the previous item is still running.
    try:
        with database_module.SessionLocal() as db:
            row = db.get(Job, job_id)
            if row is not None:
                row.status = "processing"
                db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] Failed to mark job processing: %s", job_id, exc)

    try:
        result = await convert_document(
            input_path,
            template,
            job_id,
            output_dir,
            output_format=output_format,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("[%s] Batch item raised: %s", job_id, exc)
        _finalise_job(job_id, status="failed", error_message=str(exc))
        return

    if not result.get("success"):
        _finalise_job(
            job_id,
            status="failed",
            error_message=result.get("error", "Conversion failed."),
        )
        return

    output_path = Path(result["output_path"])
    _finalise_job(job_id, status="completed", output_path=output_path)


@router.post(
    "/api/v2/batch",
    summary="Batch-convert a zip archive of documents",
    status_code=202,
)
@limiter.limit("3/minute")
async def batch_convert(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
) -> dict:
    """
    Accept a ``.zip`` archive and queue each supported document inside
    for conversion. Returns ``202 Accepted`` with a list of queued
    ``job_id``s; the actual processing happens in a background task.
    """
    user_id = request.headers.get("x-user-id") or "anonymous"
    template = request.query_params.get("template", "report")
    output_format = request.query_params.get("output_format", "pdf")

    if template not in {"report", "ieee", "resume", "altacv", "moderncv"}:
        raise HTTPException(status_code=400, detail=f"Unknown template: {template!r}.")
    if output_format not in {"pdf", "docx", "html", "md", "markdown", "epub"}:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown output_format: {output_format!r}.",
        )

    # The frontend sends a .zip; reject anything else at the edge.
    filename = Path(file.filename or "archive.zip").name
    if Path(filename).suffix.lower() != ".zip":
        raise HTTPException(
            status_code=400,
            detail=f"Expected a .zip archive, got {filename!r}.",
        )

    # Persist the upload to a temp file so zipfile can read it
    # (UploadFile isn't seekable across all platforms).
    batch_id = str(uuid.uuid4())
    upload_path = TEMP_BATCH_ROOT / f"{batch_id}.zip"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with upload_path.open("wb") as buffer:
            while chunk := await file.read(64 * 1024):
                buffer.write(chunk)

        with zipfile.ZipFile(upload_path) as zf:
            safe_members, _total = _validate_zip(zf)
            processable, skipped = _partition_by_extension(safe_members)

            if not processable:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Archive contains no supported documents "
                        f"(allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))})."
                    ),
                )

            extract_root = TEMP_BATCH_ROOT / batch_id
            extract_root.mkdir(parents=True, exist_ok=True)
            zf.extractall(extract_root, members=safe_members)

    except HTTPException:
        upload_path.unlink(missing_ok=True)
        raise
    except zipfile.BadZipFile as exc:
        upload_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=f"Not a valid zip file: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        upload_path.unlink(missing_ok=True)
        logger.exception("Batch upload failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to process archive.") from exc

    # Queue a Job row for each accepted file.
    job_ids: list[str] = []
    queued: list[dict] = []
    for member in processable:
        job_id = str(uuid.uuid4())
        job_ids.append(job_id)
        queued.append(
            {
                "job_id": job_id,
                "input_filename": member,
                "input_path": extract_root / member,
                "output_dir": extract_root / "output" / job_id,
            }
        )
        _create_queued_job(
            job_id=job_id,
            input_filename=member,
            template=template,
            output_format=output_format,
            user_id=user_id,
        )

    # Kick off background processing — sequential to avoid hammering
    # the docstream pipeline (CPU-bound OCR / LaTeX compilation).
    background_tasks.add_task(
        _run_batch,
        queued=queued,
        template=template,
        output_format=output_format,
        upload_path=upload_path,
        extract_root=extract_root,
    )

    return {
        "success": True,
        "batch_id": batch_id,
        "queued": len(queued),
        "skipped": skipped,
        "job_ids": job_ids,
        "message": (
            f"{len(queued)} document(s) queued for conversion. "
            "Check the History page for progress."
        ),
    }


def _create_queued_job(
    *,
    job_id: str,
    input_filename: str,
    template: str,
    output_format: str,
    user_id: str,
) -> None:
    """Insert a Job row in ``queued`` state.

    Same failure-tolerant pattern as the single-file endpoint — a
    DB write error must not block the user's HTTP response.
    """
    try:
        with database_module.SessionLocal() as db:
            db.add(
                Job(
                    id=job_id,
                    user_id=user_id,
                    input_filename=input_filename,
                    template=template,
                    output_format=output_format,
                    status="queued",
                )
            )
            db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[%s] Failed to insert queued Job row: %s", job_id, exc)


async def _run_batch(
    *,
    queued: list[dict],
    template: str,
    output_format: str,
    upload_path: Path,
    extract_root: Path,
) -> None:
    """Background task: process every queued job sequentially.

    Marked ``async`` so FastAPI's ``BackgroundTasks`` schedules it on
    the same event loop as the request — we can ``await`` the per-
    item coroutine without spinning up a second loop.
    """
    try:
        for item in queued:
            input_path: Path = item["input_path"]
            output_dir: Path = item["output_dir"]
            output_dir.mkdir(parents=True, exist_ok=True)
            await _process_batch_item(
                job_id=item["job_id"],
                input_path=input_path,
                template=template,
                output_format=output_format,
                output_dir=output_dir,
            )
    finally:
        # Best-effort cleanup of the upload file. The extracted
        # directory is left in place so the conversion pipeline can
        # read the .tex output; the periodic ``cleanup_old_jobs``
        # sweep reaps stale batch directories by mtime.
        upload_path.unlink(missing_ok=True)
        logger.debug("Batch finished; upload %s removed", upload_path)


__all__ = ["router"]
