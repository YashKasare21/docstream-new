"""End-to-end tests for the batch ZIP conversion endpoint.

Mirrors the fixture pattern in ``test_jobs.py``: a throwaway SQLite
file plus a reloaded module graph so the lifespan guard sees the
test env. The real ``docstream.convert`` pipeline is replaced with
an async stub that writes a small PDF to ``tmp_path``.
"""

from __future__ import annotations

import importlib
import io
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_rate_limiter_batch(monkeypatch):
    """Bypass the slowapi limiter for batch tests."""
    from slowapi.extension import Limiter

    def _noop_limit(*_args, **_kwargs):  # type: ignore[no-untyped-def]
        def _decorator(func):
            return func

        return _decorator

    monkeypatch.setattr(Limiter, "limit", _noop_limit)
    yield


@pytest.fixture
def fresh_batch_db(tmp_path: Path, monkeypatch):
    """Point the SQLAlchemy engine at a fresh DB and reload modules."""
    db_path = tmp_path / "batch_jobs.db"
    monkeypatch.setenv("DOCSTREAM_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCSTREAM_ENV", "test")

    import docstream_api.database as db_module

    importlib.reload(db_module)
    import docstream_api.routes.jobs as jobs_module

    importlib.reload(jobs_module)
    import docstream_api.routes.convert as convert_module

    importlib.reload(convert_module)
    import docstream_api.routes.batch as batch_module

    importlib.reload(batch_module)
    import docstream_api.main as main_module

    importlib.reload(main_module)

    db_module.init_jobs_db()
    yield db_module, main_module, convert_module, batch_module, tmp_path

    importlib.reload(batch_module)
    importlib.reload(convert_module)
    importlib.reload(jobs_module)
    importlib.reload(main_module)
    importlib.reload(db_module)


def _build_zip(members: list[tuple[str, bytes]]) -> bytes:
    """Helper: build a zip archive in memory from (name, bytes) pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members:
            zf.writestr(name, data)
    return buf.getvalue()


def test_batch_endpoint_accepts_valid_zip(fresh_batch_db, tmp_path):
    """A zip with PDF + TeX entries should return 202 + queued Job rows."""
    _db_module, main_module, convert_module, _batch_module, _ = fresh_batch_db

    output_pdf = tmp_path / "result.pdf"
    output_pdf.write_bytes(b"%PDF-1.4\nfake\n%%EOF\n")

    async def fake_convert(*_args, **_kwargs):
        return {
            "success": True,
            "job_id": "ignored",
            "output_path": str(output_pdf),
            "output_format": "pdf",
            "processing_time": 0.1,
        }

    zip_bytes = _build_zip(
        [
            ("doc1.pdf", b"%PDF-1.4\nhi\n%%EOF\n"),
            ("notes/latex.tex", b"\\documentclass{article}\\begin{document}hi\\end{document}"),
        ]
    )

    client = TestClient(main_module.app)
    with patch.object(convert_module, "convert_document", new=fake_convert):
        resp = client.post(
            "/api/v2/batch",
            headers={"x-user-id": "batch-tester@example.com"},
            files={"file": ("batch.zip", io.BytesIO(zip_bytes), "application/zip")},
        )

    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["queued"] == 2
    assert len(body["job_ids"]) == 2
    assert body["skipped"] == []

    # The history endpoint should now show both queued jobs tagged
    # to the signed-in user.
    listing = client.get("/api/v2/jobs?user_id=batch-tester@example.com").json()
    assert listing["count"] == 2
    filenames = sorted(j["input_filename"] for j in listing["jobs"])
    assert filenames == ["doc1.pdf", "notes/latex.tex"]


def test_batch_endpoint_skips_unsupported_files(fresh_batch_db, tmp_path):
    """Non-PDF/TeX files are skipped, not rejected."""
    _db_module, main_module, convert_module, _batch_module, _ = fresh_batch_db

    output_pdf = tmp_path / "result.pdf"
    output_pdf.write_bytes(b"%PDF-1.4\nfake\n%%EOF\n")

    async def fake_convert(*_args, **_kwargs):
        return {
            "success": True,
            "job_id": "ignored",
            "output_path": str(output_pdf),
            "output_format": "pdf",
            "processing_time": 0.1,
        }

    zip_bytes = _build_zip(
        [
            ("doc1.pdf", b"%PDF-1.4\nhi\n%%EOF\n"),
            ("readme.txt", b"hello"),
            ("image.png", b"\x89PNG\r\n"),
        ]
    )

    client = TestClient(main_module.app)
    with patch.object(convert_module, "convert_document", new=fake_convert):
        resp = client.post(
            "/api/v2/batch",
            files={"file": ("batch.zip", io.BytesIO(zip_bytes), "application/zip")},
        )

    assert resp.status_code == 202
    body = resp.json()
    assert body["queued"] == 1
    assert sorted(body["skipped"]) == ["image.png", "readme.txt"]
    assert len(body["job_ids"]) == 1


def test_batch_endpoint_rejects_non_zip(fresh_batch_db):
    """Uploads with a non-.zip extension are rejected at the edge."""
    _db_module, main_module, _convert_module, _batch_module, _ = fresh_batch_db
    client = TestClient(main_module.app)
    resp = client.post(
        "/api/v2/batch",
        files={"file": ("not-a-zip.pdf", io.BytesIO(b"%PDF-1.4 hi"), "application/pdf")},
    )
    assert resp.status_code == 400
    assert ".zip" in resp.json()["detail"]


def test_batch_endpoint_rejects_path_traversal(fresh_batch_db):
    """Entries with ``..`` in the path are refused before extraction."""
    _db_module, main_module, _convert_module, _batch_module, _ = fresh_batch_db
    client = TestClient(main_module.app)
    zip_bytes = _build_zip(
        [("../escape.pdf", b"%PDF-1.4\nhi\n%%EOF\n")],
    )
    resp = client.post(
        "/api/v2/batch",
        files={"file": ("evil.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert resp.status_code == 400
    assert "Unsafe path" in resp.json()["detail"]


def test_batch_endpoint_rejects_too_many_files(fresh_batch_db):
    """A zip with more than 20 entries is rejected (zip-bomb guard)."""
    _db_module, main_module, _convert_module, _batch_module, _ = fresh_batch_db
    client = TestClient(main_module.app)
    # 21 tiny PDF files.
    members = [(f"d{i}.pdf", b"%PDF-1.4\nhi\n%%EOF\n") for i in range(21)]
    zip_bytes = _build_zip(members)
    resp = client.post(
        "/api/v2/batch",
        files={"file": ("many.zip", io.BytesIO(zip_bytes), "application/zip")},
    )
    assert resp.status_code == 400
    assert "batch limit" in resp.json()["detail"]
