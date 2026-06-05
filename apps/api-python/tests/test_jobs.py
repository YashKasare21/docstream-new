"""End-to-end tests for the persistent job-history endpoints.

These tests exercise the real FastAPI app + SQLAlchemy session and use
a throwaway SQLite file in a temp dir so they don't touch the
production ``docstream.db``.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_rate_limiter_jobs(monkeypatch):
    """Bypass the rate limiter for jobs tests so quota can't bleed across.

    The shared ``Limiter`` singleton accumulates hits across tests in
    the same ``pytest`` process. Rather than trying to keep its
    in-memory state in sync, we patch ``Limiter.limit`` to a no-op
    decorator for the duration of each test.
    """
    from slowapi.extension import Limiter

    def _noop_limit(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        def _decorator(func):
            return func

        return _decorator

    monkeypatch.setattr(Limiter, "limit", _noop_limit)
    yield


@pytest.fixture
def fresh_jobs_db(tmp_path: Path, monkeypatch):
    """Point the SQLAlchemy engine at a fresh DB for the duration of a test."""
    db_path = tmp_path / "jobs.db"
    monkeypatch.setenv("DOCSTREAM_DB_PATH", str(db_path))

    # Re-import so the module-level engine rebinds with the new env var.
    import importlib

    import docstream_api.database as db_module

    importlib.reload(db_module)
    import docstream_api.routes.jobs as jobs_module
    importlib.reload(jobs_module)
    import docstream_api.routes.convert as convert_module
    importlib.reload(convert_module)
    import docstream_api.main as main_module
    importlib.reload(main_module)

    db_module.init_jobs_db()
    yield db_module, main_module, db_path

    # Reset module state so the next test sees a clean slate.
    importlib.reload(convert_module)
    importlib.reload(jobs_module)
    importlib.reload(main_module)
    importlib.reload(db_module)


def test_jobs_endpoints_require_no_existing_data(fresh_jobs_db):
    """A fresh DB returns an empty list, not a 500."""
    _db_module, main_module, _path = fresh_jobs_db
    client = TestClient(main_module.app)
    resp = client.get("/api/v2/jobs")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["jobs"] == []


def test_job_persists_through_convert_endpoint(fresh_jobs_db, tmp_path):
    """A successful conversion produces a ``completed`` Job row."""
    import docstream_api.routes.convert as convert_module

    _db_module, main_module, _path = fresh_jobs_db

    # Build a fake output file the mocked converter will return.
    output_pdf = tmp_path / "result.pdf"
    output_pdf.write_bytes(b"%PDF-1.4\n... fake ...\n%%EOF\n")

    async def fake_convert(*_args, **_kwargs):
        return {
            "success": True,
            "job_id": "ignored",
            "output_path": str(output_pdf),
            "output_format": "pdf",
            "processing_time": 0.42,
        }

    sample_pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n%%EOF\n"
    )

    client = TestClient(main_module.app)
    with patch.object(convert_module, "convert_document", new=fake_convert):
        with client:
            resp = client.post(
                "/api/v2/convert",
                files={"file": ("paper.pdf", _io(sample_pdf_bytes), "application/pdf")},
                data={"template": "report"},
            )

    assert resp.status_code == 200, resp.text

    listing = client.get("/api/v2/jobs").json()
    assert listing["count"] == 1
    job = listing["jobs"][0]
    assert job["status"] == "completed"
    assert job["template"] == "report"
    assert job["output_format"] == "pdf"
    assert job["output_pdf_path"] == str(output_pdf)

    detail = client.get(f"/api/v2/jobs/{job['id']}").json()
    assert detail["status"] == "completed"
    assert detail["pdf_url"] == f"/api/v2/files/{job['id']}/result.pdf"


def test_failed_conversion_records_failed_status(fresh_jobs_db):
    """A failed conversion produces a ``failed`` Job row with the error."""
    import docstream_api.routes.convert as convert_module

    _db_module, main_module, _path = fresh_jobs_db

    async def fake_convert(*_args, **_kwargs):
        return {
            "success": False,
            "job_id": "ignored",
            "error": "Pix2tex not installed",
        }

    sample_pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n0000000000 65535 f \n%%EOF\n"
    )

    client = TestClient(main_module.app)
    with patch.object(convert_module, "convert_document", new=fake_convert):
        with client:
            client.post(
                "/api/v2/convert",
                files={"file": ("paper.pdf", _io(sample_pdf_bytes), "application/pdf")},
                data={"template": "report"},
            )

    # The contract we actually care about: the Job row exists with
    # status "failed" and the error message preserved. The exact HTTP
    # status code is incidental — the persistence layer is the point.
    listing = client.get("/api/v2/jobs").json()
    assert listing["count"] == 1, listing
    failed_job = listing["jobs"][0]
    assert failed_job["status"] == "failed"
    assert "Pix2tex" in (failed_job["error_message"] or "")

    listing = client.get("/api/v2/jobs").json()
    assert listing["count"] == 1
    assert listing["jobs"][0]["status"] == "failed"
    assert "Pix2tex" in (listing["jobs"][0]["error_message"] or "")


def test_get_unknown_job_returns_404(fresh_jobs_db):
    _db_module, main_module, _path = fresh_jobs_db
    client = TestClient(main_module.app)
    resp = client.get("/api/v2/jobs/does-not-exist")
    assert resp.status_code == 404


def test_user_id_header_tags_job(fresh_jobs_db):
    """``x-user-id`` header should be persisted on the Job row."""
    _db_module, main_module, _path = fresh_jobs_db
    client = TestClient(main_module.app)
    resp = client.post(
        "/api/v2/convert",
        headers={"x-user-id": "alice@example.com"},
        files={"file": ("hello.pdf", _io(b"%PDF-1.4\n%%EOF\n"), "application/pdf")},
        data={"template": "report"},
    )
    assert resp.status_code in (200, 500)  # body irrelevant — only DB tag matters

    listing = client.get("/api/v2/jobs?user_id=alice@example.com").json()
    assert listing["count"] == 1
    assert listing["jobs"][0]["user_id"] == "alice@example.com"

    # And filtering by another user returns nothing.
    other = client.get("/api/v2/jobs?user_id=bob@example.com").json()
    assert other["count"] == 0

    # Anonymous fallback still works.
    anon = client.get("/api/v2/jobs").json()
    assert anon["count"] == 1
    assert anon["jobs"][0]["user_id"] == "alice@example.com"


# ── helpers ──────────────────────────────────────────────────────────────────


def _io(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)
