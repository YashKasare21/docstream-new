"""
Tests for the EquationOCRStage plugin.

pix2tex is **always** mocked here — we never want CI to download the
~200 MB PyTorch model weights or run slow GPU/CPU inference. The mocks
exercise every code path in the stage (image resolution, OCR success,
OCR failure, missing model, missing path, non-image blocks) without
touching the real model.

The tests do **not** require ``pix2tex`` to be installed: a stub
``pix2tex.cli`` module is injected into ``sys.modules`` for the cases
that exercise the import path. This keeps the test suite fast and
side-effect-free.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock, patch

import pytest


def _ensure_pix2tex_stub() -> None:
    """Inject a stub ``pix2tex.cli`` module so the plugin's import succeeds
    even when pix2tex isn't installed (it pulls in a 200 MB PyTorch dep).

    Idempotent — safe to call from every test.
    """
    if "pix2tex.cli" in sys.modules:
        return
    pkg = types.ModuleType("pix2tex")
    cli = types.ModuleType("pix2tex.cli")
    cli.LatexOCR = MagicMock()  # type: ignore[attr-defined]
    sys.modules["pix2tex"] = pkg
    sys.modules["pix2tex.cli"] = cli


_ensure_pix2tex_stub()


# ──────────────────────────────────────────────────────────────────────
# 1. Model lazy-loading is cached across calls
# ──────────────────────────────────────────────────────────────────────


def test_model_is_loaded_only_once_across_calls():
    """The ~200 MB PyTorch model must not be reloaded per image."""
    from docstream.plugins.equation_ocr import EquationOCRStage

    with patch("pix2tex.cli.LatexOCR") as mock_cls:
        mock_model = MagicMock(return_value=r"\frac{a}{b}")
        mock_cls.return_value = mock_model

        stage = EquationOCRStage()
        # First call -> triggers lazy load
        stage._ensure_model()
        # Second call -> must reuse the same instance, NOT call LatexOCR() again
        stage._ensure_model()
        stage._ensure_model()

    assert mock_cls.call_count == 1, (
        f"LatexOCR was constructed {mock_cls.call_count} times — should be 1"
    )


# ──────────────────────────────────────────────────────────────────────
# 2. Model load failure -> no-op (pipeline must not crash)
# ──────────────────────────────────────────────────────────────────────


def test_model_load_failure_is_swallowed_and_blocks_unchanged():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = {
        "type": "image",
        "content": "/tmp/eq.png",
        "metadata": {"image_path": "/tmp/eq.png"},
    }
    data = {"blocks": [image_block]}

    with patch(
        "docstream.plugins.equation_ocr.EquationOCRStage._ensure_model",
        return_value=None,
    ):
        result = stage.process(data)

    # Block must be preserved (not replaced with CODE)
    assert result["blocks"][0]["type"] == "image"
    assert result["blocks"][0]["content"] == "/tmp/eq.png"


# ──────────────────────────────────────────────────────────────────────
# 3. Successful OCR: IMAGE block -> CODE block with LaTeX
# ──────────────────────────────────────────────────────────────────────


def test_image_block_is_replaced_with_code_block_containing_latex():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = {
        "type": "image",
        "content": "/tmp/some_eq.png",
        "metadata": {"image_path": "/tmp/some_eq.png"},
        "page": 3,
    }
    data = {"blocks": [image_block, {"type": "text", "content": "intro"}]}

    mock_model = MagicMock(return_value=r"x^{2} + y^{2} = z^{2}")
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    # First block should now be a CODE block, not an IMAGE block
    assert result["blocks"][0]["type"] == "code"
    assert result["blocks"][0]["content"] == "$x^{2} + y^{2} = z^{2}$"
    assert result["blocks"][0]["metadata"]["math"] is True
    assert result["blocks"][0]["metadata"]["ocr_source"] == "pix2tex"
    assert result["blocks"][0]["metadata"]["language"] == "latex"
    assert result["blocks"][0]["metadata"]["source_image_path"] == "/tmp/some_eq.png"
    # Page number carried over
    assert result["blocks"][0]["page"] == 3
    # Second (non-image) block untouched
    assert result["blocks"][1] == {"type": "text", "content": "intro"}


# ──────────────────────────────────────────────────────────────────────
# 4. OCR is called once per image (lazy model reuse)
# ──────────────────────────────────────────────────────────────────────


def test_model_is_invoked_once_per_image():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    data = {
        "blocks": [
            {"type": "image", "content": "/tmp/a.png", "metadata": {"image_path": "/tmp/a.png"}},
            {"type": "image", "content": "/tmp/b.png", "metadata": {"image_path": "/tmp/b.png"}},
            {"type": "image", "content": "/tmp/c.png", "metadata": {"image_path": "/tmp/c.png"}},
        ]
    }
    mock_model = MagicMock(side_effect=[r"\alpha", r"\beta", r"\gamma"])
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    assert mock_model.call_count == 3
    assert result["blocks"][0]["content"] == "$\\alpha$"
    assert result["blocks"][1]["content"] == "$\\beta$"
    assert result["blocks"][2]["content"] == "$\\gamma$"


# ──────────────────────────────────────────────────────────────────────
# 5. OCR inference failure -> block left untouched
# ──────────────────────────────────────────────────────────────────────


def test_ocr_inference_failure_leaves_image_block_untouched():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = {
        "type": "image",
        "content": "/tmp/broken.png",
        "metadata": {"image_path": "/tmp/broken.png"},
    }
    data = {"blocks": [image_block]}

    mock_model = MagicMock(side_effect=RuntimeError("GPU OOM"))
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    # Block must remain an IMAGE block — the failure must not crash
    assert result["blocks"][0]["type"] == "image"


# ──────────────────────────────────────────────────────────────────────
# 6. Block with no resolvable image path is left untouched
# ──────────────────────────────────────────────────────────────────────


def test_image_block_without_path_is_unchanged():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = {"type": "image", "content": "no-path", "metadata": {}}
    data = {"blocks": [image_block]}

    result = stage.process(data)
    assert result["blocks"][0] is image_block


# ──────────────────────────────────────────────────────────────────────
# 7. Display math -> $$...$$ wrapper
# ──────────────────────────────────────────────────────────────────────


def test_display_math_uses_double_dollar_wrapper():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = {
        "type": "image",
        "content": "/tmp/display_eq.png",
        "metadata": {"image_path": "/tmp/display_eq.png", "is_display_math": True},
    }
    data = {"blocks": [image_block]}

    mock_model = MagicMock(return_value=r"\int_{0}^{\infty} e^{-x}\,dx = 1")
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    assert result["blocks"][0]["content"] == (
        "$$\\int_{0}^{\\infty} e^{-x}\\,dx = 1$$"
    )
    assert result["blocks"][0]["metadata"]["is_display"] is True


# ──────────────────────────────────────────────────────────────────────
# 8. Stage works against the legacy `structure` key (v2 extractor)
# ──────────────────────────────────────────────────────────────────────


def test_stage_also_processes_structure_key():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    data = {
        "structure": [
            {"type": "heading", "text": "Title"},
            {"type": "image", "content": "/tmp/eq.png", "metadata": {"image_path": "/tmp/eq.png"}},
        ]
    }
    mock_model = MagicMock(return_value=r"E = mc^{2}")
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    assert result["structure"][0]["type"] == "heading"
    assert result["structure"][1]["type"] == "code"
    assert result["structure"][1]["content"] == "$E = mc^{2}$"


# ──────────────────────────────────────────────────────────────────────
# 9. Non-image blocks pass through untouched
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("block_type", ["text", "heading", "code", "list", "table", "quote"])
def test_non_image_blocks_pass_through(block_type):
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    data = {"blocks": [{"type": block_type, "content": "x"}]}

    # If anything is OCR'd, the test must fail — the model must NOT be called
    with patch.object(stage, "_ensure_model") as ensure:
        result = stage.process(data)

    assert result["blocks"][0]["type"] == block_type
    assert ensure.call_count == 0


# ──────────────────────────────────────────────────────────────────────
# 10. Empty / missing data is a no-op
# ──────────────────────────────────────────────────────────────────────


def test_empty_data_passes_through():
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    assert stage.process({}) == {}
    assert stage.process({"blocks": []}) == {"blocks": []}
    assert stage.process({"structure": []}) == {"structure": []}


# ──────────────────────────────────────────────────────────────────────
# 11. Pydantic Block objects (BlockType enum) work end-to-end
# ──────────────────────────────────────────────────────────────────────


def test_works_with_pydantic_block_objects():
    from docstream.models.document import Block, BlockType
    from docstream.plugins.equation_ocr import EquationOCRStage

    stage = EquationOCRStage()
    image_block = Block(
        type=BlockType.IMAGE,
        content="/tmp/eq.png",
        metadata={"image_path": "/tmp/eq.png"},
    )
    data = {"blocks": [image_block]}

    mock_model = MagicMock(return_value=r"\sum_{i=1}^{n} i = \frac{n(n+1)}{2}")
    with patch.object(stage, "_ensure_model", return_value=mock_model), \
         patch("PIL.Image.open", return_value=MagicMock()):
        result = stage.process(data)

    new_block = result["blocks"][0]
    assert new_block["type"] == "code"
    assert new_block["content"] == (
        "$\\sum_{i=1}^{n} i = \\frac{n(n+1)}{2}$"
    )
    assert new_block["metadata"]["math"] is True


# ──────────────────────────────────────────────────────────────────────
# 12. Plugin is exported from docstream.plugins
# ──────────────────────────────────────────────────────────────────────


def test_plugin_is_exported():
    import docstream.plugins as plugins

    assert hasattr(plugins, "EquationOCRStage")
    assert "EquationOCRStage" in plugins.__all__
