import io

import pytest
from docstream_api.main import app
from docstream_api.utils.rate_limit import limiter
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear the slowapi in-memory limiter between tests so the
    ``5/minute`` cap on the convert endpoint doesn't trip when several
    test cases exercise it in a row."""
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


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
