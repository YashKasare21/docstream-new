"""
Tests for the LaTeX/TeX format handler.

Each test writes a small ``.tex`` file to a ``tmp_path`` fixture and
asserts the extracted ``Block`` objects carry the right ``BlockType``,
``metadata`` and content.  The handler is exercised end-to-end — no
mocks — because ``pylatexenc`` is pure-Python and the tests are fast.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from docstream.core.format_handlers.latex_handler import LaTeXHandler
from docstream.exceptions import ExtractionError
from docstream.models.document import BlockType

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _write_tex(tmp_path: Path, name: str, body: str) -> Path:
    """Write ``body`` to ``tmp_path / name`` and return the path."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _blocks_of_type(blocks, block_type: BlockType):
    """Filter ``blocks`` to only those matching ``block_type``."""
    return [b for b in blocks if b.type == block_type]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Headings — section / subsection / subsubsection / paragraph / chapter
# ─────────────────────────────────────────────────────────────────────────────


def test_extracts_headings_with_correct_levels(tmp_path: Path):
    """\\section → level 1, \\subsection → 2, \\subsubsection → 3."""
    tex = _write_tex(
        tmp_path,
        "headings.tex",
        r"""
\begin{document}
\section{Top}
Body of top section.
\subsection{Sub}
Body of sub.
\subsubsection{Deep}
Body of deep.
\paragraph{Para}
Body of paragraph.
\chapter{Chapter One}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    headings = _blocks_of_type(blocks, BlockType.HEADING)

    # Build a list of (level, content) for easy assertions.
    by_level = {h.metadata.get("level"): h.content for h in headings}

    assert by_level.get(1) in {"Top", "Chapter One"}
    assert by_level.get(2) == "Sub"
    assert by_level.get(3) == "Deep"
    assert by_level.get(4) == "Para"

    # Font size mapping from the spec.
    sizes = {h.metadata.get("level"): h.font_size for h in headings}
    assert sizes.get(1) == 24.0
    assert sizes.get(2) == 20.0
    assert sizes.get(3) == 16.0
    assert sizes.get(4) == 14.0

    # All headings are bold.
    assert all(h.is_bold for h in headings)


# ─────────────────────────────────────────────────────────────────────────────
# 2. Math — equation, align, and inline $...$
# ─────────────────────────────────────────────────────────────────────────────


def test_extracts_equation_and_align_as_code_with_math_metadata(tmp_path: Path):
    """equation/align → CODE with is_math=True; $...$ → inline math."""
    tex = _write_tex(
        tmp_path,
        "math.tex",
        r"""
\begin{document}
Some text $a + b = c$ with inline math.

\begin{equation}
E = mc^2
\end{equation}

\begin{align}
x &= 1 \\
y &= 2
\end{align}

\begin{equation*}
F = ma
\end{equation*}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    code_blocks = _blocks_of_type(blocks, BlockType.CODE)

    # 1 inline + 1 equation + 1 align + 1 equation* = 4 code blocks
    assert len(code_blocks) == 4

    math_blocks = [b for b in code_blocks if b.metadata.get("is_math")]
    assert len(math_blocks) == 4

    # Every math block has language=latex
    assert all(b.metadata.get("language") == "latex" for b in math_blocks)

    # Exactly one inline math block
    inline = [b for b in code_blocks if b.metadata.get("is_inline_math")]
    assert len(inline) == 1
    assert inline[0].content == "$a + b = c$"

    # The align content should include \begin{align}...\end{align}
    align = [b for b in math_blocks if "\\begin{align}" in b.content]
    assert len(align) == 1
    assert "\\end{align}" in align[0].content

    # The equation* is also math.
    eqn_star = [b for b in math_blocks if "equation*" in b.content]
    assert len(eqn_star) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 3. Tabular — converted to TABLE block
# ─────────────────────────────────────────────────────────────────────────────


def test_extracts_tabular_as_table_block(tmp_path: Path):
    """A ``tabular`` env is converted to a TABLE block (Markdown or raw)."""
    tex = _write_tex(
        tmp_path,
        "table.tex",
        r"""
\begin{document}
\begin{tabular}{|l|c|r|}
\hline
A & B & C \\
\hline
1 & 2 & 3 \\
4 & 5 & 6 \\
\hline
\end{tabular}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    tables = _blocks_of_type(blocks, BlockType.TABLE)
    assert len(tables) == 1

    table = tables[0]
    content = table.content
    # Either a clean Markdown table or a raw_latex fallback — both are valid.
    if table.metadata.get("raw_latex"):
        assert "A" in content and "B" in content and "C" in content
    else:
        # Markdown table markers
        assert "| A |" in content or "| A " in content
        assert "---" in content
        assert "| 1 |" in content or "| 1 " in content


# ─────────────────────────────────────────────────────────────────────────────
# 4. \includegraphics — IMAGE block with path in content
# ─────────────────────────────────────────────────────────────────────────────


def test_extracts_includegraphics_as_image_block(tmp_path: Path):
    """\\includegraphics{path} → IMAGE with content=path."""
    tex = _write_tex(
        tmp_path,
        "img.tex",
        r"""
\begin{document}
\includegraphics{figure.png}
\includegraphics[width=0.5\textwidth]{another.jpg}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    images = _blocks_of_type(blocks, BlockType.IMAGE)
    assert len(images) == 2

    paths = [i.content for i in images]
    assert "figure.png" in paths
    assert "another.jpg" in paths

    # The width= variant should have width metadata
    width_img = next(i for i in images if i.content == "another.jpg")
    assert width_img.metadata.get("width") == "0.5"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Lists — itemize and enumerate → LIST
# ─────────────────────────────────────────────────────────────────────────────


def test_extracts_itemize_and_enumerate_as_list_blocks(tmp_path: Path):
    """itemize/enumerate → LIST blocks with newline-joined items."""
    tex = _write_tex(
        tmp_path,
        "lists.tex",
        r"""
\begin{document}
\begin{itemize}
\item First bullet
\item Second bullet
\item Third bullet
\end{itemize}

\begin{enumerate}
\item First numbered
\item Second numbered
\end{enumerate}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    lists = _blocks_of_type(blocks, BlockType.LIST)
    assert len(lists) == 2

    itemize, enumerate = lists
    assert "First bullet" in itemize.content
    assert "Second bullet" in itemize.content
    assert "Third bullet" in itemize.content
    assert itemize.content.count("\n") == 2  # 3 items → 2 newlines

    assert "First numbered" in enumerate.content
    assert "Second numbered" in enumerate.content


# ─────────────────────────────────────────────────────────────────────────────
# 6. Strips comments + \input / \include commands
# ─────────────────────────────────────────────────────────────────────────────


def test_strips_comments_and_input_include(tmp_path: Path):
    """Comments and \\input/\\include are silently dropped."""
    tex = _write_tex(
        tmp_path,
        "stripped.tex",
        r"""
\begin{document}
% This is a comment that should not appear in output
Visible text starts here.
\input{somefile.tex}
\include{another.tex}
After the includes, still visible.
% Final comment
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)
    text_blocks = _blocks_of_type(blocks, BlockType.TEXT)
    full_text = " ".join(b.content for b in text_blocks)

    assert "comment" not in full_text
    assert "somefile" not in full_text
    assert "another" not in full_text
    assert "Visible text" in full_text
    assert "still visible" in full_text

    # The ``\input{...}`` and ``\include{...}`` commands themselves
    # must not produce any standalone block (their filename arguments
    # are not present in the output).
    for b in blocks:
        assert "somefile" not in b.content
        assert "another.tex" not in b.content
    # No block should be a raw \input/\include source fragment.
    assert not any(b.content.strip().startswith("\\input") for b in blocks)
    assert not any(b.content.strip().startswith("\\include") for b in blocks)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Nested environments (e.g. tabular inside a table float)
# ─────────────────────────────────────────────────────────────────────────────


def test_handles_nested_environments(tmp_path: Path):
    """A ``tabular`` inside a ``table`` float still extracts the table."""
    tex = _write_tex(
        tmp_path,
        "nested.tex",
        r"""
\begin{document}
\begin{table}[h]
\centering
\caption{Sample table}
\begin{tabular}{|l|l|}
\hline
Col1 & Col2 \\
\hline
A & B \\
C & D \\
\hline
\end{tabular}
\end{table}
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)

    # The tabular inside the table env should be extracted as a TABLE.
    tables = _blocks_of_type(blocks, BlockType.TABLE)
    assert len(tables) >= 1
    table = tables[0]
    if not table.metadata.get("raw_latex"):
        assert "Col1" in table.content or "Col 1" in table.content
        assert "---" in table.content


# ─────────────────────────────────────────────────────────────────────────────
# 8. ExtractionError on non-existent file
# ─────────────────────────────────────────────────────────────────────────────


def test_raises_extraction_error_on_missing_file(tmp_path: Path):
    """Non-existent path → ExtractionError."""
    missing = tmp_path / "does_not_exist.tex"
    with pytest.raises(ExtractionError):
        LaTeXHandler().extract(missing)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Round-trip: minimal valid document produces a non-empty list[Block]
# ─────────────────────────────────────────────────────────────────────────────


def test_minimal_document_round_trip(tmp_path: Path):
    """A bare-bones document produces a non-empty list[Block]."""
    tex = _write_tex(
        tmp_path,
        "minimal.tex",
        r"""
\documentclass{article}
\begin{document}
\section{Hello}
This is a minimal paragraph.
\end{document}
""",
    )

    blocks = LaTeXHandler().extract(tex)

    assert isinstance(blocks, list)
    assert len(blocks) > 0

    # The section heading should be there
    headings = _blocks_of_type(blocks, BlockType.HEADING)
    assert any(h.content == "Hello" and h.metadata.get("level") == 1 for h in headings)

    # The paragraph should be there
    text_blocks = _blocks_of_type(blocks, BlockType.TEXT)
    assert any("minimal paragraph" in b.content for b in text_blocks)


# ─────────────────────────────────────────────────────────────────────────────
# Bonus tests — keep the suite robust against regressions
# ─────────────────────────────────────────────────────────────────────────────


def test_quote_environment(tmp_path: Path):
    """``quote`` env → QUOTE block."""
    tex = _write_tex(
        tmp_path,
        "quote.tex",
        r"""
\begin{document}
\begin{quote}
To be or not to be.
\end{quote}
\end{document}
""",
    )
    blocks = LaTeXHandler().extract(tex)
    quotes = _blocks_of_type(blocks, BlockType.QUOTE)
    assert len(quotes) == 1
    assert "To be" in quotes[0].content


def test_abstract_environment(tmp_path: Path):
    """``abstract`` env → TEXT with is_abstract metadata."""
    tex = _write_tex(
        tmp_path,
        "abstract.tex",
        r"""
\begin{document}
\begin{abstract}
The abstract body.
\end{abstract}
\end{document}
""",
    )
    blocks = LaTeXHandler().extract(tex)
    abstracts = [b for b in blocks if b.metadata.get("is_abstract")]
    assert len(abstracts) == 1
    assert "abstract body" in abstracts[0].content


def test_unnumbered_section(tmp_path: Path):
    """\\section*{...} → HEADING with is_unnumbered=True."""
    tex = _write_tex(
        tmp_path,
        "star.tex",
        r"""
\begin{document}
\section*{Hidden section}
Content of hidden section.
\end{document}
""",
    )
    blocks = LaTeXHandler().extract(tex)
    headings = _blocks_of_type(blocks, BlockType.HEADING)
    unnumbered = [h for h in headings if h.metadata.get("is_unnumbered")]
    assert len(unnumbered) == 1
    assert unnumbered[0].content == "Hidden section"
    assert unnumbered[0].metadata.get("level") == 1


def test_verbatim_block_preserves_content(tmp_path: Path):
    """``verbatim`` env yields a CODE block with the raw body."""
    tex = _write_tex(
        tmp_path,
        "verb.tex",
        r"""
\begin{document}
\begin{verbatim}
def f(x):
    return x + 1
\end{verbatim}
\end{document}
""",
    )
    blocks = LaTeXHandler().extract(tex)
    code_blocks = _blocks_of_type(blocks, BlockType.CODE)
    # Find the verbatim block by content
    matching = [b for b in code_blocks if "def f" in b.content]
    assert len(matching) == 1
    assert "return x + 1" in matching[0].content
