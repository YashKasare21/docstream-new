"""
Docstream — PDF to LaTeX conversion library.

Simple 3-step pipeline:
1. Extract structured text from PDF
2. AI generates LaTeX from template skeleton
3. XeLaTeX compiles to PDF

Basic usage:
    import docstream
    result = docstream.convert("paper.pdf", template="ieee")
    print(result.tex_path)   # Path to .tex file
    print(result.pdf_path)   # Path to .pdf file
"""

from __future__ import annotations

__version__ = "0.2.0"
__all__ = [
    "convert", "stream_convert", "extract", "generate",
    "ConversionResult", "ExtractionError",
    "Pipeline", "PipelineStage", "LatexExtractionStage",
]

import logging
from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.pipeline import LatexExtractionStage, Pipeline, PipelineStage

logger = logging.getLogger(__name__)


class ConversionResult:
    """Result of a PDF conversion operation."""

    def __init__(
        self,
        success: bool,
        tex_path: Path | None = None,
        pdf_path: Path | None = None,
        error: str | None = None,
        processing_time: float = 0.0,
        template_used: str = "",
    ):
        """Initialize conversion result.

        Args:
            success: Whether the conversion succeeded
            tex_path: Path to the generated .tex file
            pdf_path: Path to the generated .pdf file
            error: Error message if conversion failed
            processing_time: Total processing time in seconds
            template_used: Name of the template used
        """
        self.success = success
        self.tex_path = tex_path
        self.pdf_path = pdf_path
        self.error = error
        self.processing_time = processing_time
        self.template_used = template_used

    def __repr__(self) -> str:
        """Return string representation of conversion result."""
        if self.success:
            return f"ConversionResult(success=True, template={self.template_used!r}, pdf={self.pdf_path})"
        return f"ConversionResult(success=False, error={self.error!r})"


def convert(
    pdf_path: str | Path,
    template: str = "report",
    output_dir: str | Path = "./docstream_output",
    ai_provider=None,
    enable_equation_ocr: bool = False,
) -> ConversionResult:
    """
    Convert a PDF to LaTeX and PDF.

    This is the main entry point for Docstream.

    Pipeline:
    1. (Optional) Run pix2tex equation OCR on embedded equation images
    2. Extract structured text from PDF using PyMuPDF
    3. AI fills LaTeX template skeleton with content
    4. XeLaTeX compiles LaTeX to PDF

    Internally this creates a :class:`Pipeline` with a single
    :class:`LatexExtractionStage` (plus an optional
    :class:`EquationOCRStage` when ``enable_equation_ocr`` is True) and
    runs it synchronously. You can also construct custom pipelines with
    additional stages (see ``docstream.plugins``).

    Args:
        pdf_path: Path to the input PDF file
        template: 'report' | 'ieee' | 'resume' | 'altacv' | 'moderncv' (default: 'report')
        output_dir: Directory for output files
        ai_provider: Optional custom AI provider chain
        enable_equation_ocr: When True, prepend :class:`EquationOCRStage`
            to the pipeline. Equation images are replaced with
            ``$...$`` LaTeX. Adds significant latency on first run
            (~200 MB pix2tex model download).

    Returns:
        ConversionResult with tex_path and pdf_path on success

    Example:
        result = docstream.convert("paper.pdf", template="ieee")
        if result.success:
            print(f"LaTeX: {result.tex_path}")
            print(f"PDF: {result.pdf_path}")
    """
    from docstream.pipeline import LatexExtractionStage, Pipeline
    from docstream.plugins import EquationOCRStage

    stages = []
    if enable_equation_ocr:
        stages.append(EquationOCRStage())
    stages.append(LatexExtractionStage())

    pipeline = Pipeline(stages)
    data = pipeline.run({
        "file_path": str(pdf_path),
        "template": template,
        "output_dir": str(output_dir),
        "ai_provider": ai_provider,
    })

    if data.get("success"):
        return ConversionResult(
            success=True,
            tex_path=Path(data["tex_path"]),
            pdf_path=Path(data["pdf_path"]),
            processing_time=data["processing_time"],
            template_used=data["template_used"],
        )

    return ConversionResult(
        success=False,
        error=data.get("error", "Unknown error"),
        processing_time=data.get("processing_time", 0.0),
        template_used=data.get("template_used", template),
    )


async def stream_convert(
    pdf_path: str | Path,
    template: str = "report",
    output_dir: str | Path = "./docstream_output",
    ai_provider=None,
    enable_equation_ocr: bool = False,
):
    """
    Convert a PDF to LaTeX and yield the result chunk by chunk.

    Runs :func:`convert` in a thread pool, then reads the generated
    ``.tex`` file and yields its content line-by-line as an async
    generator — suitable for Server-Sent Events or other streaming
    transports.

    Each yielded dict has the shape::

        {"chunk": str, "progress": float, "step": str}

    The final yield includes ``tex_url``, ``pdf_url``, and
    ``processing_time`` alongside ``step="done"``.

    When ``enable_equation_ocr`` is True, an :class:`EquationOCRStage`
    is prepended to the pipeline so equation images are converted to
    LaTeX before template generation.
    """
    import asyncio

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    yield {"chunk": "Extracting document content...\n", "progress": 0.0, "step": "extract"}
    await asyncio.sleep(0.05)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        lambda: convert(
            pdf_path,
            template=template,
            output_dir=output_dir,
            ai_provider=ai_provider,
            enable_equation_ocr=enable_equation_ocr,
        ),
    )

    if not result.success:
        yield {
            "chunk": f"Error: {result.error}",
            "progress": 1.0,
            "step": "error",
        }
        return

    yield {
        "chunk": f"Conversion complete in {result.processing_time:.1f}s — streaming output...\n",
        "progress": 0.35,
        "step": "stream",
    }
    await asyncio.sleep(0.05)

    if result.tex_path and result.tex_path.exists():
        text = result.tex_path.read_text(encoding="utf-8")
        lines = text.split("\n")
        total = len(lines)

        for i, line in enumerate(lines):
            progress = 0.35 + 0.60 * (i + 1) / max(total, 1)
            yield {
                "chunk": line + "\n",
                "progress": round(progress, 4),
                "step": "stream",
            }
            await asyncio.sleep(0.01)

    yield {
        "chunk": "",
        "progress": 1.0,
        "step": "done",
        "tex_url": str(result.tex_path) if result.tex_path else None,
        "pdf_url": str(result.pdf_path) if result.pdf_path else None,
        "processing_time": result.processing_time,
        "template_used": template,
    }


def extract(pdf_path: str | Path) -> dict:
    """
    Extract structured content from a PDF.

    Returns raw structured document dict.
    Useful for inspecting extraction quality before converting.
    """
    from docstream.core.extractor_v2 import extract_structured

    return extract_structured(pdf_path)


def generate(
    document: dict,
    template: str = "report",
    ai_provider=None,
) -> str:
    """
    Generate LaTeX from extracted document content.

    Returns complete LaTeX string.
    Useful for inspecting AI output before compiling.
    """
    from docstream.core.generator import generate_latex

    return generate_latex(document, template, ai_provider)
