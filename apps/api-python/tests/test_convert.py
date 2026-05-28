import io
from pathlib import Path
from unittest.mock import patch, MagicMock

import docstream


# ── 1. Health endpoint ──

def test_health_endpoint_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


# ── 2. Invalid file type ──

def test_convert_invalid_file_type_rejected(client):
    files = {"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
    resp = client.post("/api/convert", files=files, data={"template": "report"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "not a valid PDF" in data["error"]


# ── 3. Valid PDF calls docstream ──

def test_convert_valid_pdf_calls_docstream(client, sample_pdf_upload, mock_convert_result):
    with patch("docstream_api.services.converter.docstream.convert", return_value=mock_convert_result) as mock_fn:
        resp = client.post("/api/convert", files=sample_pdf_upload, data={"template": "report"})
        data = resp.json()
        assert data["success"] is True
        assert data["tex_url"] is not None
        assert data["pdf_url"] is not None
        mock_fn.assert_called_once()


# ── 4. Extraction error returns clean message ──

def test_convert_extraction_error_returns_clean_message(client, sample_pdf_upload):
    with patch(
        "docstream_api.services.converter.docstream.convert",
        side_effect=docstream.ExtractionError("raw error"),
    ):
        resp = client.post("/api/convert", files=sample_pdf_upload, data={"template": "report"})
        data = resp.json()
        assert data["success"] is False
        assert "Could not extract content" in data["error"]
        assert "raw error" not in data["error"]


# ── 5. Unknown template rejected ──

def test_convert_unknown_template_rejected(client, sample_pdf_upload):
    resp = client.post("/api/convert", files=sample_pdf_upload, data={"template": "unknown"})
    data = resp.json()
    assert data["success"] is False
    assert "Unknown template" in data["error"]


# ── 6. File served after conversion ──

def test_file_served_after_conversion(client, sample_pdf_upload, mock_convert_result, tmp_path):
    # Create a fake output file
    fake_output = tmp_path / "document.tex"
    fake_output.write_text(r"\documentclass{article}")

    with patch("docstream_api.services.converter.docstream.convert", return_value=mock_convert_result):
        resp = client.post("/api/convert", files=sample_pdf_upload, data={"template": "report"})
        data = resp.json()
        assert data["success"] is True

        # Extract job_id from the tex_url
        job_id = data["tex_url"].split("/")[-2]

        # Place the file where the serve endpoint expects it
        output_dir = Path(f"/tmp/docstream/{job_id}/output")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "document.tex").write_text(r"\documentclass{article}")

        # Fetch the file
        file_resp = client.get(data["tex_url"])
        assert file_resp.status_code == 200
        assert b"documentclass" in file_resp.content
