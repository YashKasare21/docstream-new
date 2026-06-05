"""
Job-history endpoints.

Exposes the persistent ``Job`` rows created during conversion so the
frontend can render a dashboard of past runs.

* ``GET /api/v2/jobs``             — list all jobs, newest first.
* ``GET /api/v2/jobs/{job_id}``    — single job detail with download
                                     URLs (only present when the job
                                     is completed and the file still
                                     exists on disk).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from docstream_api.database import get_db
from docstream_api.db_models import Job

router = APIRouter()


def _build_download_urls(job: Job) -> dict[str, str | None]:
    """Return ``pdf_url`` / ``tex_url`` if the on-disk file still exists."""
    pdf_url: str | None = None
    tex_url: str | None = None
    if job.output_pdf_path:
        if Path(job.output_pdf_path).exists():
            pdf_url = f"/api/v2/files/{job.id}/{Path(job.output_pdf_path).name}"
    if job.output_tex_path:
        if Path(job.output_tex_path).exists():
            tex_url = f"/api/v2/files/{job.id}/{Path(job.output_tex_path).name}"
    return {"pdf_url": pdf_url, "tex_url": tex_url}


@router.get("/api/v2/jobs", summary="List recent conversion jobs")
def list_jobs(
    limit: int = 50,
    user_id: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    """Return up to ``limit`` jobs ordered by ``created_at`` descending.

    Args:
        limit: Maximum number of rows to return (default 50, capped at 200).
        user_id: Optional filter — when provided, only jobs whose
            ``user_id`` column matches are returned. The frontend
            passes the logged-in user's email here so each user sees
            their own history.
        db: FastAPI-injected SQLAlchemy session.
    """
    capped_limit = max(1, min(limit, 200))
    stmt = select(Job).order_by(Job.created_at.desc()).limit(capped_limit)
    if user_id:
        stmt = (
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
            .limit(capped_limit)
        )
    rows = db.execute(stmt).scalars().all()
    jobs = []
    for row in rows:
        payload = row.to_dict()
        payload.update(_build_download_urls(row))
        jobs.append(payload)
    return {
        "count": len(rows),
        "jobs": jobs,
    }


@router.get("/api/v2/jobs/{job_id}", summary="Get a single job by ID")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
) -> dict:
    """Return details for one job, including download URLs if available."""
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found.")
    payload = job.to_dict()
    payload.update(_build_download_urls(job))
    return payload


__all__ = ["router"]
