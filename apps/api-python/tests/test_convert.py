import io
from unittest.mock import AsyncMock, patch

import docstream

# ── 1. Health endpoint ──


def test_health_endpoint_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# ── 2. Invalid file type ──


def test_convert_unsupported_extension_rejected(client, auth_header):
    files = {"file": ("test.doc", io.BytesIO(b"hello world"), "application/msword")}
    resp = client.post("/api/v2/convert", files=files, data={"template": "report"}, headers=auth_header)
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert "Unsupported file type" in data["error"]


# ── 3. Valid PDF calls docstream and returns the compiled PDF file ──


def test_convert_valid_pdf_returns_pdf_file(
    client, auth_header, sample_pdf_upload, mock_convert_result, tmp_path
):
    # Point the mock at a real on-disk file so FileResponse can serve it.
    fake_pdf = tmp_path / "document.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake")
    mock_convert_result.pdf_path = str(fake_pdf)
    mock_convert_result.tex_path = str(tmp_path / "document.tex")

    with patch("docstream.convert", return_value=mock_convert_result) as mock_fn:
        resp = client.post(
            "/api/v2/convert",
            files=sample_pdf_upload,
            data={"template": "report"},
            headers=auth_header,
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-1.4 fake"
    mock_fn.assert_called_once()


# ── 4. Extraction error returns clean message ──


def test_convert_error_returns_clean_message(client, auth_header, sample_pdf_upload):
    with patch(
        "docstream.convert",
        side_effect=docstream.ExtractionError("raw error"),
    ):
        resp = client.post("/api/v2/convert", files=sample_pdf_upload, data={"template": "report"}, headers=auth_header)
    # Service swallows exceptions and returns success=False with 500
    assert resp.status_code == 500
    data = resp.json()
    assert data["success"] is False
    assert "unexpected error" in data["error"]
    assert "raw error" not in data["error"]


# ── 5. Unknown template rejected ──


def test_convert_unknown_template_rejected(client, auth_header, sample_pdf_upload):
    resp = client.post("/api/v2/convert", files=sample_pdf_upload, data={"template": "unknown"}, headers=auth_header)
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    assert "Unknown template" in data["error"]


# ── 6. Non-PDF output_format runs Pandoc and returns the converted file ──


def test_convert_docx_output_invokes_pandoc_and_returns_docx(
    client, auth_header, sample_pdf_upload, mock_convert_result, tmp_path
):
    from docstream_api.services import converter as svc

    fake_tex = tmp_path / "document.tex"
    fake_tex.write_text(r"\documentclass{article}\begin{document}Hi\end{document}")
    fake_docx = tmp_path / "document.docx"
    fake_docx.write_bytes(b"PK fake-docx-bytes")
    mock_convert_result.tex_path = str(fake_tex)
    mock_convert_result.pdf_path = str(tmp_path / "document.pdf")

    with patch("docstream.convert", return_value=mock_convert_result), \
         patch.object(
             svc,
             "convert_with_pandoc",
             AsyncMock(return_value=fake_docx),
         ) as mock_pandoc:
        resp = client.post(
            "/api/v2/convert?output_format=docx",
            files=sample_pdf_upload,
            data={"template": "report"},
            headers=auth_header,
        )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert resp.content == b"PK fake-docx-bytes"
    mock_pandoc.assert_called_once()
    args, _ = mock_pandoc.call_args
    assert str(args[0]).endswith(".tex")
    assert args[2] == "docx"


# ── 7. Pandoc missing -> 501 ──


def test_convert_docx_returns_501_when_pandoc_missing(
    client, auth_header, sample_pdf_upload, mock_convert_result, tmp_path
):
    from docstream.exceptions import RenderingError
    from docstream_api.services import converter as svc

    fake_tex = tmp_path / "document.tex"
    fake_tex.write_text(r"\documentclass{article}")
    mock_convert_result.tex_path = str(fake_tex)
    mock_convert_result.pdf_path = str(tmp_path / "document.pdf")

    with patch("docstream.convert", return_value=mock_convert_result), \
         patch.object(
             svc,
             "convert_with_pandoc",
             AsyncMock(side_effect=RenderingError("Pandoc is not installed on the server.")),
         ):
        resp = client.post(
            "/api/v2/convert?output_format=docx",
            files=sample_pdf_upload,
            data={"template": "report"},
            headers=auth_header,
        )

    assert resp.status_code == 501
    data = resp.json()
    assert data["success"] is False
    assert "Pandoc" in data["error"]


# ── 8. Invalid output_format rejected by query pattern (422) ──


def test_convert_invalid_output_format_rejected(client, auth_header, sample_pdf_upload):
    resp = client.post(
        "/api/v2/convert?output_format=mp4",
        files=sample_pdf_upload,
        data={"template": "report"},
        headers=auth_header,
    )
    # FastAPI returns 422 for Query pattern violations
    assert resp.status_code == 422


# ── 9. Stream endpoint restricted to PDF ──


def test_stream_rejects_non_pdf_output_format(client, auth_header, sample_pdf_upload):
    resp = client.post(
        "/api/v2/stream?output_format=docx",
        files=sample_pdf_upload,
        data={"template": "report"},
        headers=auth_header,
    )
    # FastAPI returns 422 for Query pattern violations (^(pdf)$)
    assert resp.status_code == 422
