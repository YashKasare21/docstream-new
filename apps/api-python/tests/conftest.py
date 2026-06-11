import importlib
import io
import os
from pathlib import Path

import jwt
import pytest
from fastapi.testclient import TestClient

# CI runners don't ship XeLaTeX. The lifespan guard in
# ``docstream_api.main`` treats ``DOCSTREAM_ENV=test`` as a "soft
# start" signal so the FastAPI app boots even when xelatex is
# missing. Set it once at import time so every TestClient (including
# the ones in test_jobs.py) bypasses the hard stop.
os.environ.setdefault("DOCSTREAM_ENV", "test")

# Shared test secret for JWT auth — matches ``docstream_api.auth.get_current_user``.
TEST_SECRET = "test-secret-for-ci-do-not-use-in-production"
os.environ["NEXTAUTH_SECRET"] = TEST_SECRET


def make_token(email: str) -> str:
    """Create a signed HS256 JWT for the given email."""
    return jwt.encode({"email": email}, TEST_SECRET, algorithm="HS256")


@pytest.fixture(autouse=True)
def _disable_rate_limiter_for_tests(monkeypatch):
    """Replace ``Limiter.limit`` with a no-op so rate limits don't affect tests."""
    from slowapi.extension import Limiter as _SlowLimiter

    def _noop_limit(*_args, **_kwargs):
        def _decorator(func):
            return func
        return _decorator

    monkeypatch.setattr(_SlowLimiter, "limit", _noop_limit)
    yield


@pytest.fixture
def client(tmp_path: Path, monkeypatch):
    """FastAPI test client with a throwaway SQLite DB.

    Reloads ``database`` and ``main`` modules so the engine points at
    a fresh file, ensuring the ``users`` and ``jobs`` tables are
    created from the current ``Base.metadata``.
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DOCSTREAM_DB_PATH", str(db_path))
    monkeypatch.setenv("DOCSTREAM_ENV", "test")
    monkeypatch.setenv("NEXTAUTH_SECRET", TEST_SECRET)

    import docstream_api.database as db_module
    importlib.reload(db_module)

    import docstream_api.routes.convert as convert_module
    importlib.reload(convert_module)

    import docstream_api.routes.batch as batch_module
    importlib.reload(batch_module)

    import docstream_api.main as main_module
    importlib.reload(main_module)

    db_module.init_jobs_db()

    # Attach rate limiter to app state (normally done in lifespan)
    from docstream_api.utils.rate_limit import limiter as _limiter
    main_module.app.state.limiter = _limiter

    yield TestClient(main_module.app)

    importlib.reload(batch_module)
    importlib.reload(convert_module)
    importlib.reload(main_module)
    importlib.reload(db_module)


@pytest.fixture
def auth_header() -> dict:
    """Standard ``Authorization: Bearer <token>`` header."""
    token = make_token("test@example.com")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\n"
        b"xref\n0 3\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"trailer\n<< /Size 3 /Root 1 0 R >>\n"
        b"startxref\n109\n%%EOF\n"
    )


@pytest.fixture
def sample_pdf_upload(sample_pdf_bytes) -> dict:
    """A file-like object suitable for TestClient uploads."""
    return {"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}


@pytest.fixture
def mock_convert_result():
    """A mock ConvertResult with success=True."""

    class MockResult:
        success = True
        tex_path = "/tmp/docstream/test/output/document.tex"
        pdf_path = "/tmp/docstream/test/output/document.pdf"
        processing_time = 4.2
        error = None

    return MockResult()
