"""Community plugins for the DocStream processing pipeline."""

from docstream.plugins.cleaner import WhitespaceCleanerStage
from docstream.plugins.equation_ocr import EquationOCRStage

__all__ = ["EquationOCRStage", "WhitespaceCleanerStage"]
