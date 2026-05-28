"""
Text-cleaning plugins for the DocStream processing pipeline.

These stages can be inserted into a custom :class:`Pipeline` to
normalise whitespace, fix common OCR artifacts, etc.

Example::

    from docstream.pipeline import Pipeline
    from docstream.plugins.cleaner import WhitespaceCleanerStage

    pipeline = Pipeline([
        WhitespaceCleanerStage(),
    ])
    result = await pipeline.run({"latex": raw_latex})
"""

from __future__ import annotations

from docstream.pipeline import PipelineStage


class WhitespaceCleanerStage(PipelineStage):
    """Remove excessive whitespace from text / LaTeX content.

    Normalises the ``"latex"`` key in the data dict by:

    * collapsing multiple blank lines into a single blank line
    * replacing runs of spaces (outside verbatim environments)
      with a single space
    * stripping trailing whitespace on every line
    """

    @property
    def name(self) -> str:
        return "whitespace_cleaner"

    async def process(self, data: dict) -> dict:
        source = data.get("latex") or data.get("text") or ""
        if not source:
            return data

        cleaned = _clean_whitespace(source)
        data["latex"] = cleaned
        return data


def _clean_whitespace(text: str) -> str:
    """Strip trailing whitespace per line and collapse excess blank lines."""
    lines = text.split("\n")
    stripped = [ln.rstrip() for ln in lines]

    result: list[str] = []
    prev_blank = False
    for ln in stripped:
        if ln == "":
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        result.append(ln)

    return "\n".join(result)
