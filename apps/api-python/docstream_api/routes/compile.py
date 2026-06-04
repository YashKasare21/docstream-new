"""
Direct LaTeX compilation endpoint.

Accepts a ``.tex`` / ``.latex`` upload, runs it through XeLaTeX via the core
``compile_latex`` engine, and returns the compiled ``.pdf``.

This bypasses the AI template generation step so users can iteratively
recompile a hand-authored (or already-generated) LaTeX document.
"""

import asyncio
import logging
from pathlib import Path

from docstream.core.compiler import compile_latex
from docstream.exceptions import CompilationError, RenderingError
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse

from docstream_api.utils.file_handler import get_output_dir, save_text_upload
from docstream_api.utils.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

SUPPORTED_TEX_EXTENSIONS = {".tex", ".latex"}
MAX_TEX_SIZE_MB = 10


@router.post(
    "/api/v2/compile",
    summary="Compile a .tex file to PDF",
)
@limiter.limit("10/minute")
async def compile_tex(
    request: Request,
    file: UploadFile = File(...),
):
    """
    Compile an uploaded LaTeX document to PDF via XeLaTeX.

    Accepts ``.tex`` or ``.latex`` uploads. The compiler runs in a
    background thread so the event loop is never blocked by the
    XeLaTeX subprocess.

    Returns:
        The compiled ``.pdf`` file (``application/pdf``) on success.

    Raises:
        400 — unsupported file extension, empty upload, or file too large.
        422 — LaTeX compilation produced errors (response body contains
              the compiler output for debugging).
        500 — XeLaTeX binary not available or unexpected render error.
    """
    # ----- 1. Validate filename / extension (LFI guard) -----
    filename = Path(file.filename or "input.tex").name
    if not filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_TEX_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {ext!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_TEX_EXTENSIONS))}"
            ),
        )

    # ----- 2. Save upload to disk via shared file handler -----
    try:
        job_id, tex_path = await save_text_upload(file, extension=ext)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to save uploaded .tex file")
        raise HTTPException(status_code=500, detail=f"Failed to save upload: {exc}") from exc

    # ----- 3. Enforce size limit (defence-in-depth; we already streamed) -----
    size_bytes = tex_path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if size_mb > MAX_TEX_SIZE_MB:
        raise HTTPException(
            status_code=400,
            detail=f"File too large: {size_mb:.1f} MB. Maximum is {MAX_TEX_SIZE_MB} MB.",
        )

    # ----- 4. Read .tex content (compile_latex takes a string) -----
    try:
        latex_content = tex_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                "Uploaded file is not valid UTF-8. "
                "LaTeX sources must be saved as UTF-8 text."
            ),
        ) from exc

    # ----- 5. Compile in a thread executor (XeLaTeX is subprocess-bound) -----
    output_dir = get_output_dir(job_id)
    try:
        _, pdf_path = await asyncio.to_thread(
            compile_latex,
            latex_content,
            output_dir,
            tex_path.stem,
        )
    except CompilationError as exc:
        logger.warning("[%s] XeLaTeX compilation failed: %s", job_id, exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "LaTeX compilation failed",
                "message": exc.message if hasattr(exc, "message") else str(exc),
                "compiler_output": exc.compiler_output or "",
                "tex_path": str(tex_path),
            },
        ) from exc
    except RenderingError as exc:
        logger.exception("[%s] Rendering error", job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Rendering error: {exc}",
        ) from exc

    if not pdf_path.exists():
        logger.error("[%s] Compilation reported success but PDF missing: %s", job_id, pdf_path)
        raise HTTPException(
            status_code=500,
            detail="Compilation succeeded but PDF was not produced.",
        )

    logger.info(
        "[%s] Compiled %s -> %s (%d bytes)",
        job_id,
        tex_path.name,
        pdf_path.name,
        pdf_path.stat().st_size,
    )

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{tex_path.stem}.pdf",
    )
