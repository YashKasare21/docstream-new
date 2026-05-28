"""
Pipeline architecture for DocStream — a pluggable stage-based processing model.

A :class:`Pipeline` runs a sequence of :class:`PipelineStage` instances,
passing a mutable ``data`` dict through each stage in order.  This allows
the community to inject custom behaviour (cleaners, formatters, validators,
etc.) without modifying the core library.

Usage::

    from docstream.pipeline import Pipeline, PipelineStage

    class MyStage(PipelineStage):
        name = "my_stage"

        async def process(self, data):
            data["greeting"] = "Hello, world!"
            return data

    pipeline = Pipeline([MyStage()])
    result = await pipeline.run({"file_path": "paper.pdf"})
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Abstract base for a single processing stage in a :class:`Pipeline`.

    Subclasses **must** override :meth:`process` and set the :attr:`name`
    attribute (or override the ``name`` property).
    """

    @property
    def name(self) -> str:
        """Human-readable name of this stage (used in logging / events)."""
        return type(self).__name__

    @abstractmethod
    async def process(self, data: dict) -> dict:
        """Transform *data* and return the (possibly mutated) dictionary.

        Args:
            data: Mutable dictionary carrying document content, metadata,
                and intermediate results from earlier stages.

        Returns:
            The updated ``data`` dict (may be the same object, mutated).
        """
        ...


class Pipeline:
    """Run a sequence of :class:`PipelineStage` instances in order.

    Each stage receives the ``data`` dict produced by the previous stage.
    The pipeline also logs progress and can later be hooked for streaming.
    """

    def __init__(self, stages: list[PipelineStage]) -> None:
        self.stages = list(stages)

    async def run(self, initial_data: dict) -> dict:
        """Execute all stages sequentially and return the final data dict.

        Args:
            initial_data: Starting state (e.g. ``{"file_path": "..."}``).

        Returns:
            Data dict after all stages have run.
        """
        data = dict(initial_data)
        total = len(self.stages)

        for idx, stage in enumerate(self.stages, start=1):
            stage_name = stage.name
            logger.info("[Pipeline] Stage %d/%d: %s", idx, total, stage_name)
            data = await stage.process(data)

        logger.info("[Pipeline] All %d stages completed", total)
        return data


# ---------------------------------------------------------------------------
# Built-in stages
# ---------------------------------------------------------------------------


class LatexExtractionStage(PipelineStage):
    """Full document conversion: extract, generate LaTeX, and compile.

    Expects the following keys in ``data``:

    * ``file_path`` — path to the input document
    * ``template`` — ``"report"`` or ``"ieee"`` (default ``"report"``)
    * ``output_dir`` — output directory (default ``"./docstream_output"``)
    * ``ai_provider`` — optional custom AI provider chain

    On success the following keys are added to ``data``:

    * ``latex`` — generated LaTeX source
    * ``tex_path`` — path to the ``.tex`` file
    * ``pdf_path`` — path to the ``.pdf`` file
    * ``processing_time`` — total wall-clock seconds
    * ``template_used`` — template name
    * ``success`` — ``True``
    * ``n_images`` — number of embedded images

    On failure ``data["success"]`` is ``False`` and ``data["error"]``
    is set.
    """

    @property
    def name(self) -> str:
        return "latex_extraction"

    async def process(self, data: dict) -> dict:
        import shutil
        import time

        from docstream.core.compiler import compile_latex
        from docstream.core.extractor_v2 import extract_structured
        from docstream.core.generator import generate_latex
        from docstream.exceptions import DocstreamError

        pdf_path = data["file_path"]
        template = data.get("template", "report")
        output_dir = Path(data.get("output_dir", "./docstream_output"))
        ai_provider = data.get("ai_provider")

        start_time = time.time()
        output_dir.mkdir(parents=True, exist_ok=True)
        image_dir = output_dir / "images"

        try:
            logger.info("Extracting from %s", Path(pdf_path).name)
            document = extract_structured(pdf_path, image_output_dir=image_dir)
            n_images = len(document.get("images", []))
            logger.info("Extracted %d blocks and %d images", len(document["structure"]), n_images)

            logger.info("Generating LaTeX (%s template)", template)
            latex = generate_latex(
                document,
                template,
                ai_provider,
                image_dir=image_dir,
            )
            logger.info("Generated %d chars of LaTeX", len(latex))

            logger.info("Compiling with XeLaTeX")
            tex_path, pdf_path_out = compile_latex(
                latex,
                output_dir,
                image_dir=image_dir if n_images > 0 else None,
            )

            if n_images > 0 and image_dir.exists():
                for img_file in image_dir.glob("fig_p*.*"):
                    dest = output_dir / img_file.name
                    if not dest.exists():
                        shutil.copy2(str(img_file), str(dest))

            processing_time = round(time.time() - start_time, 1)
            logger.info("Conversion complete in %ss", processing_time)

            data.update({
                "success": True,
                "latex": latex,
                "tex_path": str(tex_path),
                "pdf_path": str(pdf_path_out),
                "processing_time": processing_time,
                "template_used": template,
                "n_images": n_images,
            })

        except DocstreamError as e:
            processing_time = round(time.time() - start_time, 1)
            logger.error("Conversion failed: %s", e)
            data.update({
                "success": False,
                "error": str(e),
                "processing_time": processing_time,
                "template_used": template,
            })

        except Exception as e:
            processing_time = round(time.time() - start_time, 1)
            logger.error("Unexpected error: %s", e, exc_info=True)
            data.update({
                "success": False,
                "error": f"Unexpected error: {e}",
                "processing_time": processing_time,
                "template_used": template,
            })

        return data
