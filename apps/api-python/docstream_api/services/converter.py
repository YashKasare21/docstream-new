"""
Converter service — wraps docstream v2 library.

Delegates all conversion logic to docstream.convert().
This service only handles job management and file paths.
"""

import asyncio
import logging
import subprocess
from pathlib import Path

from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY / GROQ_API_KEY are available
load_dotenv()

logger = logging.getLogger(__name__)

VALID_TEMPLATES = {"report", "ieee", "resume", "altacv", "moderncv"}
MAX_FILE_SIZE_MB = 20

# Output format registry.
# Maps public format names -> (pandoc target name, file extension, media_type).
OUTPUT_FORMAT_MAP: dict[str, tuple[str, str, str]] = {
    "pdf": ("pdf", "pdf", "application/pdf"),
    "docx": ("docx", "docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "html": ("html", "html", "text/html; charset=utf-8"),
    "md": ("markdown", "md", "text/markdown; charset=utf-8"),
    "markdown": ("markdown", "md", "text/markdown; charset=utf-8"),
    "epub": ("epub", "epub", "application/epub+zip"),
}
PANDOC_TIMEOUT_SECONDS = 60


async def convert_with_pandoc(
    tex_path: Path,
    output_dir: Path,
    output_format: str,
) -> Path:
    """
    Convert a ``.tex`` file to a non-PDF format using Pandoc.

    Runs the Pandoc subprocess inside ``asyncio.to_thread`` so the event
    loop is never blocked. The compiled PDF is unused for non-PDF
    outputs — only the generated ``.tex`` is fed to Pandoc.

    Args:
        tex_path: Path to the generated ``.tex`` file.
        output_dir: Directory to write the converted file into.
        output_format: One of ``"docx"``, ``"html"``, ``"md"``,
                       ``"markdown"``, ``"epub"``.

    Returns:
        Path to the converted output file.

    Raises:
        RenderingError: If Pandoc is missing, fails, or times out.
    """
    from docstream.exceptions import RenderingError

    if output_format not in OUTPUT_FORMAT_MAP:
        raise RenderingError(
            f"Unsupported output format for Pandoc: {output_format!r}. "
            f"Supported: {sorted(OUTPUT_FORMAT_MAP)}"
        )

    target_format, file_ext, _ = OUTPUT_FORMAT_MAP[output_format]
    output_path = output_dir / f"document.{file_ext}"

    def _run_pandoc() -> None:
        try:
            proc = subprocess.run(
                [
                    "pandoc",
                    "-f", "latex",
                    "-t", target_format,
                    "-o", str(output_path),
                    str(tex_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=PANDOC_TIMEOUT_SECONDS,
            )
            logger.debug("Pandoc stdout: %s", proc.stdout)
        except FileNotFoundError as exc:
            raise RenderingError(
                "Pandoc is not installed on the server. "
                "Install with: sudo apt install pandoc"
            ) from exc
        except subprocess.CalledProcessError as exc:
            logger.error("Pandoc failed (rc=%s): %s", exc.returncode, exc.stderr)
            raise RenderingError(
                f"Pandoc conversion failed: {exc.stderr.strip() or exc}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise RenderingError(
                f"Pandoc conversion timed out after {PANDOC_TIMEOUT_SECONDS}s"
            ) from exc

    await asyncio.to_thread(_run_pandoc)
    return output_path


async def convert_document(
    file_path: Path,
    template: str,
    job_id: str,
    output_dir: Path,
    output_format: str = "pdf",
) -> dict:
    """
    Convert a document using docstream v2 pipeline.

    Runs in a thread pool since conversion is CPU/IO bound.
    Always returns a dict — never raises.

    When ``output_format`` is not ``"pdf"``, the generated ``.tex`` is
    post-processed through Pandoc to produce the requested format. The
    returned ``output_path`` points to the file the route should serve.
    """
    import docstream

    logger.info(
        f"[{job_id}] Starting conversion: file={file_path.name} "
        f"template={template} output_format={output_format}"
    )

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: docstream.convert(
                str(file_path),
                template=template,
                output_dir=str(output_dir),
            ),
        )

        if not result.success:
            logger.error(f"[{job_id}] Failed: {result.error}")
            return {
                "success": False,
                "job_id": job_id,
                "error": result.error or "Conversion failed.",
            }

        tex_path = Path(result.tex_path)
        pdf_path = Path(result.pdf_path)

        # Non-PDF output: convert via Pandoc.
        if output_format != "pdf":
            try:
                final_path = await convert_with_pandoc(tex_path, output_dir, output_format)
            except Exception as exc:
                logger.error(f"[{job_id}] Pandoc conversion failed: {exc}")
                return {
                    "success": False,
                    "job_id": job_id,
                    "error": str(exc),
                }
        else:
            final_path = pdf_path

        logger.info(
            f"[{job_id}] Complete in {result.processing_time}s -> {final_path.name}"
        )

        return {
            "success": True,
            "job_id": job_id,
            "output_path": str(final_path),
            "output_format": output_format,
            "tex_url": f"/api/v2/files/{job_id}/{tex_path.name}",
            "pdf_url": f"/api/v2/files/{job_id}/{pdf_path.name}",
            "processing_time": result.processing_time,
            "template_used": template,
            "document_type": None,
            "quality_score": None,
        }

    except Exception as e:
        logger.error(
            f"[{job_id}] Unexpected error: {e}",
            exc_info=True,
        )
        return {
            "success": False,
            "job_id": job_id,
            "error": ("An unexpected error occurred. Please try again."),
        }


async def stream_document(
    file_path: Path,
    template: str,
    job_id: str,
    output_dir: Path,
):
    """
    Convert a document and stream the result chunk-by-chunk via SSE.

    Wraps ``docstream.stream_convert``, mapping output paths to
    download URLs so the frontend can link to the generated files.

    Yields JSON-serialisable dicts with ``chunk``, ``progress``, and
    ``step`` keys suitable for ``data: {...}\n\n`` SSE framing.
    """

    import docstream

    logger.info(f"[{job_id}] Starting streaming conversion: file={file_path.name} template={template}")

    try:
        async for event in docstream.stream_convert(
            str(file_path),
            template=template,
            output_dir=str(output_dir),
        ):
            if event.get("step") == "done":
                tex_url = f"/api/v2/files/{job_id}/{Path(event['tex_url']).name}" if event.get("tex_url") else None
                pdf_url = f"/api/v2/files/{job_id}/{Path(event['pdf_url']).name}" if event.get("pdf_url") else None
                event["tex_url"] = tex_url
                event["pdf_url"] = pdf_url
            yield event

    except Exception as e:
        logger.error(f"[{job_id}] Streaming error: {e}", exc_info=True)
        yield {
            "chunk": f"Error: {e}",
            "progress": 1.0,
            "step": "error",
        }
