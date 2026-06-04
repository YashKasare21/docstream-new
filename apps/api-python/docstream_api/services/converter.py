"""
Converter service — wraps docstream v2 library.

Delegates all conversion logic to docstream.convert().
This service only handles job management and file paths.
"""

import asyncio
import logging
from pathlib import Path

from dotenv import load_dotenv

# Load .env so GEMINI_API_KEY / GROQ_API_KEY are available
load_dotenv()

logger = logging.getLogger(__name__)

VALID_TEMPLATES = {"report", "ieee", "resume", "altacv", "moderncv"}
MAX_FILE_SIZE_MB = 20


async def convert_document(
    file_path: Path,
    template: str,
    job_id: str,
    output_dir: Path,
) -> dict:
    """
    Convert a document using docstream v2 pipeline.

    Runs in a thread pool since conversion is CPU/IO bound.
    Always returns a dict — never raises.
    """
    import docstream

    logger.info(f"[{job_id}] Starting conversion: file={file_path.name} template={template}")

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

        logger.info(f"[{job_id}] Complete in {result.processing_time}s")

        return {
            "success": True,
            "job_id": job_id,
            "tex_url": f"/api/v2/files/{job_id}/document.tex",
            "pdf_url": f"/api/v2/files/{job_id}/document.pdf",
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
