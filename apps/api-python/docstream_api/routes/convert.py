"""
Conversion endpoints — PDF to LaTeX via docstream v2.
"""

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from docstream_api.models.schemas import ConvertResponse
from docstream_api.services.converter import (
    MAX_FILE_SIZE_MB,
    VALID_TEMPLATES,
    convert_document,
    stream_document,
)

router = APIRouter()

SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".png",
    ".jpg",
    ".jpeg",
    ".md",
    ".txt",
}


@router.post(
    "/api/v2/convert",
    response_model=ConvertResponse,
    summary="Convert document to LaTeX",
)
async def convert_v2(
    file: UploadFile = File(...),
    template: str = Form(default="report"),
):
    """
    Convert an uploaded document to LaTeX and PDF.

    Supports: PDF, DOCX, PPTX, PNG, JPG, MD, TXT
    Templates: report, ieee
    """
    job_id = str(uuid.uuid4())

    # Validate template
    if template not in VALID_TEMPLATES:
        return ConvertResponse(
            success=False,
            job_id=job_id,
            error=(f"Unknown template '{template}'. Supported: {', '.join(sorted(VALID_TEMPLATES))}"),
        )

    # Validate extension
    filename = file.filename or "document.pdf"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return ConvertResponse(
            success=False,
            job_id=job_id,
            error=(f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"),
        )

    # Read and validate size
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return ConvertResponse(
            success=False,
            job_id=job_id,
            error=(f"File too large: {size_mb:.1f} MB. Maximum is {MAX_FILE_SIZE_MB} MB."),
        )

    # Set up job directories
    job_dir = Path(f"/tmp/docstream/{job_id}")
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save uploaded file
    file_path = input_dir / filename
    file_path.write_bytes(content)

    # Run conversion
    result = await convert_document(file_path, template, job_id, output_dir)
    return ConvertResponse(**result)


@router.post(
    "/api/v2/stream",
    summary="Convert document with real-time SSE streaming",
)
async def stream_v2(
    file: UploadFile = File(...),
    template: str = Form(default="report"),
):
    """
    Convert an uploaded document and stream the LaTeX output
    chunk-by-chunk via Server-Sent Events.

    Returns a ``StreamingResponse`` with ``media_type="text/event-stream"``.
    Each event is a JSON payload following the SSE protocol:

        data: {"chunk": "...", "progress": 0.5}\n\n

    The final event carries ``step="done"`` with download URLs.
    """
    job_id = str(uuid.uuid4())

    if template not in VALID_TEMPLATES:
        error = json.dumps({
            "chunk": f"Unknown template '{template}'. Supported: {', '.join(sorted(VALID_TEMPLATES))}",
            "progress": 1.0,
            "step": "error",
        })
        return StreamingResponse(
            iter([f"data: {error}\n\n"]),
            media_type="text/event-stream",
        )

    filename = file.filename or "document.pdf"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        error = json.dumps({
            "chunk": f"Unsupported file type: {ext}",
            "progress": 1.0,
            "step": "error",
        })
        return StreamingResponse(
            iter([f"data: {error}\n\n"]),
            media_type="text/event-stream",
        )

    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        error = json.dumps({
            "chunk": f"File too large: {size_mb:.1f} MB. Maximum is {MAX_FILE_SIZE_MB} MB.",
            "progress": 1.0,
            "step": "error",
        })
        return StreamingResponse(
            iter([f"data: {error}\n\n"]),
            media_type="text/event-stream",
        )

    job_dir = Path(f"/tmp/docstream/{job_id}")
    input_dir = job_dir / "input"
    output_dir = job_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_path = input_dir / filename
    file_path.write_bytes(content)

    async def event_stream():
        async for event in stream_document(file_path, template, job_id, output_dir):
            payload = json.dumps(event)
            yield f"data: {payload}\n\n"
            if event.get("step") in ("done", "error"):
                yield "data: [DONE]\n\n"
                return

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get(
    "/api/v2/files/{job_id}/{filename}",
    summary="Download converted file",
)
async def serve_file(job_id: str, filename: str):
    """Serve .tex or .pdf output files."""
    # Security: block path traversal
    if "/" in filename or ".." in filename:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Invalid filename.",
        )

    # Only serve known safe types
    allowed_extensions = (".tex", ".pdf", ".png", ".jpg", ".jpeg", ".gif")
    if not any(filename.endswith(ext) for ext in allowed_extensions):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=400,
            detail="Only .tex, .pdf, and image files are served.",
        )

    file_path = Path(f"/tmp/docstream/{job_id}/output/{filename}")
    if not file_path.exists():
        from fastapi import HTTPException

        raise HTTPException(
            status_code=404,
            detail="File not found. Conversion may have expired.",
        )

    if filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".tex"):
        media_type = "text/plain; charset=utf-8"
    elif filename.endswith((".png",)):
        media_type = "image/png"
    elif filename.endswith((".jpg", ".jpeg")):
        media_type = "image/jpeg"
    else:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        filename=filename,
    )


@router.get("/api/v2/formats", summary="List supported formats")
async def list_formats():
    """Return list of supported input file formats."""
    return {
        "formats": [
            {"extension": ".pdf", "name": "PDF Document"},
            {"extension": ".docx", "name": "Word Document"},
            {"extension": ".pptx", "name": "PowerPoint"},
            {"extension": ".png", "name": "PNG Image"},
            {"extension": ".jpg", "name": "JPEG Image"},
            {"extension": ".md", "name": "Markdown"},
            {"extension": ".txt", "name": "Plain Text"},
        ]
    }
