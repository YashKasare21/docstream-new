"""
Equation OCR plugin for the DocStream processing pipeline.

Extracts mathematical equations from ``IMAGE`` blocks and converts them
to LaTeX strings using the open-source :mod:`pix2tex` library (also
known as LaTeX-OCR). Each detected equation is replaced in-place with
a ``CODE`` block whose ``content`` is the predicted LaTeX wrapped in
``$...$`` (display-style uses ``$$...$$``) and whose ``metadata``
carries ``{"math": True, "is_display": bool}`` for downstream
generators.

The pix2tex model is loaded lazily and cached at the instance level
so a long pipeline run that processes many images does not reload
the ~200 MB PyTorch model between images. If the model fails to
initialise (e.g. no internet on first run, or PyTorch not installed)
the stage logs a warning and leaves blocks untouched instead of
crashing the pipeline.

Example::

    from docstream.pipeline import Pipeline
    from docstream.plugins import EquationOCRStage

    pipeline = Pipeline([EquationOCRStage()])
    result = pipeline.run({"blocks": blocks})
"""

from __future__ import annotations

import logging
from typing import Any

from docstream.pipeline import PipelineStage

logger = logging.getLogger(__name__)

# Image block discriminators — Pydantic BlockType value or plain string.
_IMAGE_TYPE_VALUES = {"image", "IMAGE"}
# Block types that already represent code/math — never re-run OCR on them.
_NON_IMAGE_TYPE_VALUES = {"code", "CODE", "text", "TEXT", "heading", "HEADING"}


class EquationOCRStage(PipelineStage):
    """Run pix2tex (LaTeX-OCR) on every IMAGE block in the data dict.

    Mutates the input ``data`` dict in place:

    * ``data["blocks"]``  (preferred — Pydantic :class:`Block` list) and
    * ``data["structure"]``  (legacy — plain dict list, used by the v2
      extractor) are both scanned. Whichever key is present is updated.

    Each IMAGE block that can be resolved to a readable image file is
    replaced (in the same position of the list) with a CODE block
    containing the predicted LaTeX. The original block is preserved in
    the new block's ``metadata["source_image_path"]`` for traceability.
    """

    def __init__(self, *, model_kwargs: dict[str, Any] | None = None) -> None:
        self._ocr_model: Any = None  # LatexOCR instance (or None if load failed)
        self._model_load_failed: bool = False
        self._model_kwargs = model_kwargs or {}

    @property
    def name(self) -> str:
        return "equation_ocr"

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> Any:
        """Return a cached :class:`pix2tex.cli.LatexOCR` instance, loading
        it on first call. On failure, returns ``None`` and leaves the
        stage in a no-op state.
        """
        if self._ocr_model is not None:
            return self._ocr_model
        if self._model_load_failed:
            return None

        try:
            from pix2tex.cli import LatexOCR  # type: ignore[import-untyped]
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[EquationOCRStage] pix2tex is not importable (%s) — equation "
                "OCR will be skipped. Install with `pip install pix2tex`.",
                exc,
            )
            self._model_load_failed = True
            return None

        try:
            logger.info("[EquationOCRStage] Loading pix2tex LaTeX-OCR model (one-time)…")
            self._ocr_model = LatexOCR(**self._model_kwargs)
            logger.info("[EquationOCRStage] Model ready.")
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[EquationOCRStage] Failed to initialise pix2tex model (%s) — "
                "equation OCR will be skipped. This often means the model "
                "weights could not be downloaded on first run.",
                exc,
            )
            self._model_load_failed = True
            self._ocr_model = None

        return self._ocr_model

    # ------------------------------------------------------------------
    # Image resolution + OCR
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_image_path(block: Any) -> str | None:
        """Pull a filesystem path out of a Block/dict in any common shape."""
        # Pydantic Block (or anything with .metadata)
        meta: dict[str, Any] = {}
        content: str = ""
        if hasattr(block, "metadata"):
            meta = dict(getattr(block, "metadata", {}) or {})
            content = getattr(block, "content", "") or ""
        elif isinstance(block, dict):
            meta = dict(block.get("metadata", {}) or {})
            content = block.get("content", "") or block.get("text", "") or ""

        # Common keys for the image path
        for key in ("image_path", "path", "file_path", "src", "url"):
            val = meta.get(key)
            if val and isinstance(val, str):
                return val
        # Fall back to the content itself
        if isinstance(content, str) and content and content[0] == "/":
            return content
        return None

    @staticmethod
    def _is_image_block(block: Any) -> bool:
        """Return True if the block should be considered an IMAGE block."""
        btype = None
        if hasattr(block, "type"):
            btype = getattr(block, "type", None)
        elif isinstance(block, dict):
            btype = block.get("type")

        if btype is None:
            return False
        btype_str = str(btype)
        return btype_str in _IMAGE_TYPE_VALUES or btype_str.lower() == "image"

    def _predict_latex(self, image_path: str) -> str | None:
        """Run pix2tex on a single image. Returns the predicted LaTeX
        or ``None`` if the model isn't available or inference failed.
        """
        model = self._ensure_model()
        if model is None:
            return None

        try:
            from PIL import Image  # noqa: F401  (validated here, used below)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[EquationOCRStage] Pillow is required for pix2tex but is "
                "not importable (%s). Skipping equation.",
                exc,
            )
            return None

        try:
            image = Image.open(image_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[EquationOCRStage] Could not open image %s (%s) — skipping.",
                image_path,
                exc,
            )
            return None

        try:
            return model(image)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "[EquationOCRStage] pix2tex inference failed for %s (%s) — "
                "leaving the original IMAGE block in place.",
                image_path,
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Block rewriting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_math_block(
        original: Any,
        latex: str,
        image_path: str,
        *,
        is_display: bool = False,
    ) -> dict[str, Any]:
        """Build a CODE-shaped replacement block carrying the OCR'd math.

        The shape mirrors the rest of the pipeline: a plain dict with
        ``type``/``content``/``metadata`` so the conversion to a
        Pydantic :class:`Block` (or whatever downstream stage) is
        trivial. The original block's identity fields are copied across
        when present.
        """
        wrapper = "$$" if is_display else "$"
        content = f"{wrapper}{latex}{wrapper}"

        new_block: dict[str, Any] = {
            "type": "code",
            "content": content,
            "metadata": {
                "math": True,
                "is_display": is_display,
                "language": "latex",
                "ocr_source": "pix2tex",
                "source_image_path": image_path,
            },
        }

        # Carry across page/position hints if present.
        for key in ("page", "page_number", "bbox", "font_size", "is_bold", "is_italic"):
            if hasattr(original, key):
                new_block[key] = getattr(original, key)
            elif isinstance(original, dict) and key in original:
                new_block[key] = original[key]

        return new_block

    # ------------------------------------------------------------------
    # Public PipelineStage API
    # ------------------------------------------------------------------

    def process(self, data: dict) -> dict:
        blocks = data.get("blocks")
        if not blocks and isinstance(data.get("structure"), list):
            blocks = data["structure"]

        if not blocks:
            return data

        rewritten = 0
        skipped = 0
        new_blocks: list[Any] = []
        for block in blocks:
            if not self._is_image_block(block):
                new_blocks.append(block)
                continue

            image_path = self._resolve_image_path(block)
            if not image_path:
                logger.debug(
                    "[EquationOCRStage] IMAGE block has no resolvable path — "
                    "leaving it unchanged."
                )
                new_blocks.append(block)
                skipped += 1
                continue

            latex = self._predict_latex(image_path)
            if latex is None:
                new_blocks.append(block)
                skipped += 1
                continue

            display = bool(
                (getattr(block, "metadata", None) or {}).get("is_display_math")
                or (isinstance(block, dict) and (block.get("metadata") or {}).get("is_display_math"))
            )
            new_block = self._make_math_block(
                block,
                latex.strip(),
                image_path,
                is_display=display,
            )
            new_blocks.append(new_block)
            rewritten += 1

        # Write back to whichever key we found the blocks in.
        if "blocks" in data and data["blocks"] is blocks:
            data["blocks"] = new_blocks
        elif "structure" in data and data["structure"] is blocks:
            data["structure"] = new_blocks

        if rewritten or skipped:
            logger.info(
                "[EquationOCRStage] OCR'd %d equation(s); left %d block(s) "
                "untouched (missing model or unreadable image).",
                rewritten,
                skipped,
            )
        return data
