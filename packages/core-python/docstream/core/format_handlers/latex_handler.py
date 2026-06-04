"""
LaTeX Handler — parses LaTeX/``.tex`` source files.

Uses ``pylatexenc.latexwalker.LatexWalker`` to walk the LaTeX AST and
maps common structural elements (sections, math, tables, figures,
lists, quotes) to ``Block`` objects so they can flow through the
existing ``SemanticAnalyzer`` → ``TemplateMatcher`` → ``generator``
pipeline.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from docstream.exceptions import ExtractionError
from docstream.models.document import Block, BlockType

logger = logging.getLogger(__name__)

try:  # pylatexenc is required for this handler
    from pylatexenc.latexwalker import (
        LatexCharsNode,
        LatexCommentNode,
        LatexEnvironmentNode,
        LatexGroupNode,
        LatexMacroNode,
        LatexMathNode,
        LatexNode,
        LatexSpecialsNode,
        LatexWalker,
        get_default_latex_context_db,
    )
    from pylatexenc.macrospec import std_macro as _std_macro
except ImportError as exc:  # pragma: no cover - import guard
    raise ImportError(
        "pylatexenc is required for LaTeXHandler. Install with: pip install pylatexenc>=2.10"
    ) from exc


def _build_latex_context():
    """Build a ``LatexContextDb`` enriched with article/book-class macros.

    pylatexenc's default context already understands ``\\section``,
    ``\\chapter``, ``\\subsection`` and ``\\includegraphics`` (with
    their ``*`` variants and optional ``[opts]`` args).  We add only
    the macros that are missing from the default context but that we
    want to walk as structural nodes.

    Note: ``filter_context`` *replaces* the active category list, so
    we have to re-list the default categories we want to keep
    (``latex-base`` etc.) alongside our own.
    """
    db = get_default_latex_context_db()
    category = "docstream_latex_handler"
    try:
        db.add_context_category(
            category,
            [
                # Article-class body macros not in the default context
                _std_macro("paragraph", "{"),
                _std_macro("subparagraph", "{"),
                _std_macro("part", "{"),
                # Preamble / formatting
                _std_macro("maketitle", ""),
                _std_macro("input", "{"),
                _std_macro("include", "{"),
                _std_macro("bibliography", "{"),
                _std_macro("bibliographystyle", "{"),
                _std_macro("pagestyle", "{"),
                _std_macro("thispagestyle", "{"),
                _std_macro("tableofcontents", ""),
                _std_macro("textbf", "{"),
                _std_macro("textit", "{"),
                _std_macro("emph", "{"),
                _std_macro("textrm", "{"),
                _std_macro("textsf", "{"),
                _std_macro("texttt", "{"),
                _std_macro("textcolor", "{{"),
                _std_macro("href", "{"),
                _std_macro("url", "{"),
                _std_macro("mbox", "{"),
            ],
        )
    except ValueError:
        # Category already registered (e.g. via a previous import).
        pass
    # Re-list the default categories we want to keep, plus ours.
    return db.filter_context(
        ["latex-base", "nonascii-specials", "verbatim", category]
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mapping tables
# ─────────────────────────────────────────────────────────────────────────────

# Section commands → heading level (matches IEEE / article / report classes)
_SECTION_MACROS: dict[str, int] = {
    "chapter": 1,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
    "paragraph": 4,
    "subparagraph": 4,
}

# Environment name → set of "structured" handlers
_MATH_ENVS: frozenset[str] = frozenset({
    "equation",
    "equation*",
    "align",
    "align*",
    "gather",
    "gather*",
    "multline",
    "multline*",
    "eqnarray",
    "eqnarray*",
})

_CODE_ENVS: frozenset[str] = frozenset({
    "verbatim",
    "Verbatim",
    "lstlisting",
    "minted",
})

_TABLE_ENVS: frozenset[str] = frozenset({
    "tabular",
    "tabular*",
    "tabularx",
    "longtable",
})

_LIST_ENVS: frozenset[str] = frozenset({
    "itemize",
    "enumerate",
    "description",
})

_QUOTE_ENVS: frozenset[str] = frozenset({
    "quote",
    "quotation",
    "verse",
})

# Macros we silently drop (formatting / cross-references)
_IGNORED_MACROS: frozenset[str] = frozenset({
    "maketitle",
    "label",
    "ref",
    "cite",
    "input",
    "include",
    "bibliography",
    "bibliographystyle",
    "pagestyle",
    "thispagestyle",
    "tableofcontents",
    "noindent",
    "par",
    "newline",
    "linebreak",
    "bigskip",
    "medskip",
    "smallskip",
    "vspace",
    "hspace",
    "clearpage",
    "newpage",
    "footnote",
    "footnotetext",
})

# Macros we just inline-replace with their text content
_INLINE_MACROS: frozenset[str] = frozenset({
    "textbf",
    "textit",
    "emph",
    "textrm",
    "textsf",
    "texttt",
    "textcolor",
    "href",
    "url",
    "mbox",
})

# Headings get a `level` field; everything else is `Block` with `metadata`.
_FONT_SIZE_FOR_HEADING: dict[int, float] = {
    1: 24.0,
    2: 20.0,
    3: 16.0,
    4: 14.0,
}

_FONT_SIZE_DEFAULT = 12.0


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _node_text(node: LatexNode | None) -> str:
    """Return the plain-text representation of a single walker node.

    Used to extract group arguments (``\\section{...}``) and to collapse
    nested macros (``\\textbf{bold}``) into the surrounding text.
    """
    if node is None:
        return ""
    if isinstance(node, LatexCharsNode):
        return node.chars
    if isinstance(node, LatexGroupNode):
        return _nodes_text(node.nodelist)
    if isinstance(node, LatexMacroNode):
        # \command[opt]{arg1}{arg2} → join readable parts
        parts: list[str] = []
        if node.nodeargs:
            for arg in node.nodeargs:
                if arg is None:
                    continue
                if isinstance(arg, LatexGroupNode):
                    parts.append(_nodes_text(arg.nodelist))
                elif isinstance(arg, LatexCharsNode):
                    parts.append(arg.chars)
        if node.macroname in _INLINE_MACROS:
            return "".join(parts)
        # e.g. \LaTeX, \today
        return "".join(parts)
    if isinstance(node, LatexEnvironmentNode):
        return _nodes_text(node.nodelist)
    if isinstance(node, LatexCommentNode):
        return ""
    if isinstance(node, LatexMathNode):
        delim = node.delimiters
        body = _nodes_text(node.nodelist)
        return f"{delim[0]}{body}{delim[1]}"
    if isinstance(node, LatexSpecialsNode):
        return node.specials_chars
    return ""


def _nodes_text(nodes) -> str:
    """Concatenate the plain-text form of an iterable of walker nodes."""
    if not nodes:
        return ""
    return "".join(_node_text(n) for n in nodes)


def _trim(text: str) -> str:
    """Collapse whitespace and strip — used to clean up walker output."""
    return re.sub(r"\s+", " ", text).strip()


def _tabular_to_markdown_from_nodes(nodelist) -> str:
    """Convert a tabular env's nodelist directly to a Markdown table.

    Walks the nodelist treating ``&`` (LatexSpecialsNode) as column
    separator and ``\\\\`` (LatexMacroNode with macroname ``\\n``) as
    row terminator.  Strips ``\\hline``, ``\\cline``, ``\\multicolumn``
    and similar table-decorating macros.
    """
    rows: list[list[str]] = []
    current_row: list[str] = []
    current_cell: list[str] = []

    def flush_cell() -> None:
        current_row.append(_trim("".join(current_cell)))
        current_cell.clear()

    def flush_row() -> None:
        flush_cell()
        # Drop empty trailing cells caused by an extra ``&`` separator.
        while current_row and current_row[-1] == "":
            current_row.pop()
        if current_row:
            # Append a snapshot — we'll re-use ``current_row`` for the
            # next row, so we must not let the clear() below mutate the
            # stored reference.
            rows.append(list(current_row))
        current_row.clear()

    for n in nodelist or []:
        if isinstance(n, LatexSpecialsNode) and n.specials_chars == "&":
            flush_cell()
        elif isinstance(n, LatexMacroNode) and _is_row_terminator(n):
            # The ``\\`` row terminator is parsed either as a literal
            # ``\\`` macroname (with our custom context) or as a
            # newline macroname (default context).
            flush_row()
        elif isinstance(n, LatexMacroNode) and (n.macroname or "").strip() in {
            "hline",
            "cline",
            "toprule",
            "midrule",
            "bottomrule",
        }:
            # Row decorators — drop on the floor.
            continue
        elif isinstance(n, LatexMacroNode) and (n.macroname or "").strip() == "multicolumn":
            # \multicolumn{n}{spec}{text} — keep just the text.
            if n.nodeargs and isinstance(n.nodeargs[2], LatexGroupNode):
                current_cell.append(_nodes_text(n.nodeargs[2].nodelist))
        else:
            current_cell.append(_node_text(n))

    flush_row()

    if not rows:
        return ""

    width = max(len(r) for r in rows)
    if width < 1 or width > 20:
        return ""

    for r in rows:
        while len(r) < width:
            r.append("")

    header = rows[0]
    sep = ["---"] * width
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(sep) + " |"]
    for r in rows[1:]:
        lines.append("| " + " | ".join(r) + " |")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Handler
# ─────────────────────────────────────────────────────────────────────────────


class LaTeXHandler:
    """Parse ``.tex`` / ``.latex`` LaTeX source files into ``Block`` objects.

    Maps the common LaTeX structural elements to the same ``BlockType``
    vocabulary used by the other v2 format handlers, so a ``.tex`` file
    can be re-templated through the same pipeline as a ``.pdf`` or
    ``.docx`` file.
    """

    def extract(self, file_path: Path) -> list[Block]:
        """Extract blocks from a LaTeX source file.

        Args:
            file_path: Path to the ``.tex`` or ``.latex`` file.

        Returns:
            Ordered list of ``Block`` objects.

        Raises:
            ExtractionError: If the file cannot be read or parsed.
        """
        try:
            if not file_path.exists():
                raise ExtractionError(f"File not found: {file_path}")
            source = file_path.read_text(encoding="utf-8")
        except ExtractionError:
            raise
        except UnicodeDecodeError as exc:
            raise ExtractionError(
                f"Could not read LaTeX file '{file_path.name}'. Please ensure the file is UTF-8 encoded."
            ) from exc
        except Exception as exc:
            raise ExtractionError(
                f"Could not read LaTeX file '{file_path.name}': {exc}"
            ) from exc

        try:
            walker = LatexWalker(source, latex_context=_build_latex_context())
            nodes, _, _ = walker.get_latex_nodes()
        except Exception as exc:
            raise ExtractionError(
                f"pylatexenc could not parse LaTeX file '{file_path.name}': {exc}"
            ) from exc

        blocks: list[Block] = []
        # Find the document body so we ignore the preamble macros.
        body_nodes = _extract_document_body(nodes)

        self._walk_nodes(body_nodes, blocks, source)

        return blocks

    # ── Internal walking ────────────────────────────────────────────────────

    def _walk_nodes(self, nodes, blocks: list[Block], source: str) -> None:
        """Walk a list of top-level nodes, emitting blocks as we go."""
        para_buffer: list[str] = []

        def flush_paragraph() -> None:
            text = _trim("".join(para_buffer))
            para_buffer.clear()
            if text:
                blocks.append(
                    self._make_text_block(
                        text,
                        page_number=1,
                        font_size=_FONT_SIZE_DEFAULT,
                    )
                )

        for node in nodes:
            if isinstance(node, LatexEnvironmentNode):
                flush_paragraph()
                self._handle_environment(node, blocks, source)
            elif isinstance(node, LatexMathNode):
                flush_paragraph()
                self._handle_math(node, blocks)
            elif isinstance(node, LatexMacroNode):
                # Headings / structural macros (sections, title, etc.)
                # break the current paragraph.
                if _is_structural_macro(node):
                    flush_paragraph()
                if self._handle_macro(node, blocks, para_buffer):
                    continue
                # Anything else — try to fold the text into the buffer.
                text = _node_text(node)
                if text:
                    para_buffer.append(text)
            elif isinstance(node, LatexCharsNode):
                # Treat blank lines (a chars node that is only whitespace)
                # as a paragraph break so we don't merge across them.
                if not node.chars.strip():
                    flush_paragraph()
                else:
                    para_buffer.append(node.chars)
            elif isinstance(node, LatexCommentNode):
                # comments are silently stripped.
                continue
            elif isinstance(node, LatexSpecialsNode):
                text = node.specials_chars
                if text:
                    para_buffer.append(text)
            # LatexGroupNode at top level is unusual; ignore it.

        flush_paragraph()

    # ── Environment dispatch ────────────────────────────────────────────────

    def _handle_environment(
        self,
        node: LatexEnvironmentNode,
        blocks: list[Block],
        source: str,
    ) -> None:
        env = (node.environmentname or "").strip()

        if env in _MATH_ENVS:
            self._emit_math_env(node, blocks)
        elif env in _CODE_ENVS:
            self._emit_code_env(node, blocks)
        elif env in _TABLE_ENVS:
            self._emit_table_env(node, blocks, source)
        elif env in _LIST_ENVS:
            self._emit_list_env(node, blocks)
        elif env in _QUOTE_ENVS:
            self._emit_quote_env(node, blocks)
        elif env == "abstract":
            self._emit_abstract_env(node, blocks)
        elif env == "document":
            # Already entered when we found the body — recurse so we
            # don't miss nested content if the user gave us a fragment.
            self._walk_nodes(node.nodelist, blocks, source)
        else:
            # Unknown env — recurse and try to pick up content inside.
            logger.debug("LaTeXHandler: unhandled environment '%s', recursing", env)
            self._walk_nodes(node.nodelist, blocks, source)

    def _emit_math_env(self, node: LatexEnvironmentNode, blocks: list[Block]) -> None:
        body_text = _nodes_text(node.nodelist).strip()
        env_name = node.environmentname or "equation"
        raw = f"\\begin{{{env_name}}}\n{body_text}\n\\end{{{env_name}}}"
        blocks.append(
            self._make_code_block(
                raw,
                metadata={"language": "latex", "is_math": True, "is_inline_math": False},
                font_size=_FONT_SIZE_DEFAULT,
            )
        )

    def _emit_code_env(self, node: LatexEnvironmentNode, blocks: list[Block]) -> None:
        env = (node.environmentname or "").strip()
        # For ``verbatim``/``Verbatim`` the walker doesn't expose body
        # text in the nodelist (the package opts out of parsing).  Fall
        # back to the original source range.
        if env in {"verbatim", "Verbatim"}:
            body_text = _extract_env_body_from_source(node)
        else:
            body_text = _nodes_text(node.nodelist)
            # pylatexenc absorbs the ``[language=foo]`` package option
            # of ``lstlisting``/``minted`` into the first chars node —
            # strip that leading option line so the body is clean.
            body_text = _strip_leading_options(body_text)
        language = _detect_code_language(env, node)
        metadata: dict = {}
        if language:
            metadata["language"] = language
        if body_text.strip():
            blocks.append(
                self._make_code_block(
                    body_text,
                    metadata=metadata,
                    font_size=_FONT_SIZE_DEFAULT,
                )
            )

    def _emit_table_env(
        self,
        node: LatexEnvironmentNode,
        blocks: list[Block],
        source: str,
    ) -> None:
        body_text = _nodes_text(node.nodelist)
        # Walk the nodelist directly to handle ``&`` and ``\\`` row
        # terminators that pylatexenc represents as ``LatexSpecialsNode``
        # and ``LatexMacroNode`` (macroname ``\\n``) — text extraction
        # alone loses those.
        markdown = _tabular_to_markdown_from_nodes(node.nodelist)
        if markdown:
            blocks.append(
                self._make_table_block(
                    markdown,
                    font_size=_FONT_SIZE_DEFAULT,
                )
            )
        else:
            # Lossy — preserve raw LaTeX so downstream can recover.
            blocks.append(
                self._make_table_block(
                    body_text,
                    font_size=_FONT_SIZE_DEFAULT,
                    metadata={"raw_latex": True},
                )
            )

    def _emit_list_env(self, node: LatexEnvironmentNode, blocks: list[Block]) -> None:
        items = _collect_list_items(node.nodelist)
        if not items:
            return
        content = "\n".join(items)
        blocks.append(
            self._make_list_block(
                content,
                font_size=_FONT_SIZE_DEFAULT,
            )
        )

    def _emit_quote_env(self, node: LatexEnvironmentNode, blocks: list[Block]) -> None:
        text = _trim(_nodes_text(node.nodelist))
        if not text:
            return
        blocks.append(
            self._make_quote_block(
                text,
                font_size=_FONT_SIZE_DEFAULT,
            )
        )

    def _emit_abstract_env(self, node: LatexEnvironmentNode, blocks: list[Block]) -> None:
        text = _trim(_nodes_text(node.nodelist))
        if not text:
            return
        blocks.append(
            self._make_text_block(
                text,
                page_number=1,
                font_size=_FONT_SIZE_DEFAULT,
                metadata={"is_abstract": True},
            )
        )

    # ── Inline math ─────────────────────────────────────────────────────────

    def _handle_math(self, node: LatexMathNode, blocks: list[Block]) -> None:
        body = _trim(_nodes_text(node.nodelist))
        delim = node.delimiters
        is_inline = node.displaytype == "inline"
        if not body:
            return
        # Wrap the content with the delimiters the user actually used,
        # so the round-trip preserves the original form.
        content = f"{delim[0]}{body}{delim[1]}"
        blocks.append(
            self._make_code_block(
                content,
                metadata={
                    "language": "latex",
                    "is_math": True,
                    "is_inline_math": is_inline,
                },
                font_size=_FONT_SIZE_DEFAULT,
            )
        )

    # ── Macro dispatch ──────────────────────────────────────────────────────

    def _handle_macro(
        self,
        node: LatexMacroNode,
        blocks: list[Block],
        para_buffer: list[str],
    ) -> bool:
        """Return True if the macro was structurally handled."""
        name = (node.macroname or "").strip("\\").lower()

        if name in _SECTION_MACROS:
            # Extract the *first* group argument (the title) — it is
            # always the first LatexGroupNode in `nodeargs`.
            title = _macro_first_arg(node)
            level = _SECTION_MACROS[name]
            # Starred variant (e.g. \section*) is detected by inspecting
            # the verbatim LaTeX for a trailing ``*`` before the ``{``.
            is_unnumbered = _is_starred_macro(node)
            if title:
                blocks.append(
                    self._make_heading_block(
                        title,
                        level=level,
                        page_number=1,
                        font_size=_FONT_SIZE_FOR_HEADING.get(level, _FONT_SIZE_DEFAULT),
                        metadata={"is_unnumbered": is_unnumbered},
                    )
                )
            return True

        if name == "title":
            title = _macro_first_arg(node)
            if title:
                blocks.append(
                    self._make_heading_block(
                        title,
                        level=1,
                        page_number=1,
                        font_size=_FONT_SIZE_FOR_HEADING[1],
                        metadata={"is_title": True},
                    )
                )
            return True

        if name == "author":
            # Author can be a single arg or a multi-line body — emit as TEXT.
            text = _trim(_node_text(node))
            if text:
                blocks.append(
                    self._make_text_block(
                        text,
                        page_number=1,
                        font_size=_FONT_SIZE_DEFAULT,
                        metadata={"is_author": True},
                    )
                )
            return True

        if name == "date":
            text = _trim(_node_text(node))
            if text:
                blocks.append(
                    self._make_text_block(
                        text,
                        page_number=1,
                        font_size=_FONT_SIZE_DEFAULT,
                        metadata={"is_date": True},
                    )
                )
            return True

        if name == "includegraphics":
            path = _macro_first_arg(node)
            opts = _macro_optional_arg(node)
            if path:
                metadata: dict = {}
                if opts:
                    if "width=" in opts:
                        width = _extract_key(opts, "width")
                        if width:
                            metadata["width"] = width
                # Look back / forward for an adjacent \caption{...}.
                caption = _adjacent_caption(node, blocks)
                if caption:
                    metadata["caption"] = caption
                blocks.append(
                    self._make_image_block(
                        path,
                        font_size=_FONT_SIZE_DEFAULT,
                        metadata=metadata,
                    )
                )
            return True

        if name in _IGNORED_MACROS:
            logger.debug("LaTeXHandler: skipping ignored macro '\\%s'", name)
            return True

        return False

    # ── Block factories ─────────────────────────────────────────────────────

    @staticmethod
    def _make_text_block(
        content: str,
        *,
        page_number: int = 1,
        font_size: float = _FONT_SIZE_DEFAULT,
        metadata: dict | None = None,
    ) -> Block:
        return Block(
            type=BlockType.TEXT,
            content=content,
            page_number=page_number,
            font_size=font_size,
            metadata=metadata or {},
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_heading_block(
        content: str,
        *,
        level: int,
        page_number: int = 1,
        font_size: float = _FONT_SIZE_DEFAULT,
        metadata: dict | None = None,
    ) -> Block:
        md = dict(metadata or {})
        md.setdefault("level", level)
        return Block(
            type=BlockType.HEADING,
            content=content,
            page_number=page_number,
            font_size=font_size,
            is_bold=True,
            metadata=md,
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_code_block(
        content: str,
        *,
        metadata: dict | None = None,
        font_size: float = _FONT_SIZE_DEFAULT,
    ) -> Block:
        return Block(
            type=BlockType.CODE,
            content=content,
            page_number=1,
            font_size=font_size,
            metadata=metadata or {},
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_table_block(
        content: str,
        *,
        font_size: float = _FONT_SIZE_DEFAULT,
        metadata: dict | None = None,
    ) -> Block:
        return Block(
            type=BlockType.TABLE,
            content=content,
            page_number=1,
            font_size=font_size,
            metadata=metadata or {},
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_list_block(
        content: str,
        *,
        font_size: float = _FONT_SIZE_DEFAULT,
    ) -> Block:
        return Block(
            type=BlockType.LIST,
            content=content,
            page_number=1,
            font_size=font_size,
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_quote_block(
        content: str,
        *,
        font_size: float = _FONT_SIZE_DEFAULT,
    ) -> Block:
        return Block(
            type=BlockType.QUOTE,
            content=content,
            page_number=1,
            font_size=font_size,
            bbox=(0.0, 0.0, 0.0, 0.0),
        )

    @staticmethod
    def _make_image_block(
        content: str,
        *,
        font_size: float = _FONT_SIZE_DEFAULT,
        metadata: dict | None = None,
    ) -> Block:
        return Block(
            type=BlockType.IMAGE,
            content=content,
            page_number=1,
            font_size=font_size,
            metadata=metadata or {},
            bbox=(0.0, 0.0, 0.0, 0.0),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level helpers
# ─────────────────────────────────────────────────────────────────────────────


def _extract_document_body(nodes) -> list:
    """Return the nodelist of the outer ``document`` environment, if any.

    The preamble lives before ``\\begin{document}`` and contains macros
    like ``\\usepackage`` and ``\\title`` that we do not want to walk
    as paragraph content.  When there is a ``document`` env, we walk
    its children instead of the top-level nodes.
    """
    for node in nodes:
        if isinstance(node, LatexEnvironmentNode) and (node.environmentname or "") == "document":
            return list(node.nodelist or [])
    return list(nodes or [])


def _macro_first_arg(node: LatexMacroNode) -> str:
    """Return the trimmed text of a macro's first ``{...}`` argument."""
    if not node.nodeargs:
        return ""
    for arg in node.nodeargs:
        if arg is None:
            continue
        if isinstance(arg, LatexGroupNode):
            return _trim(_nodes_text(arg.nodelist))
        if isinstance(arg, LatexCharsNode):
            return _trim(arg.chars)
    return ""


def _macro_optional_arg(node: LatexMacroNode) -> str:
    """Return the macro's optional ``[...]`` argument, if present.

    pylatexenc exposes a single optional argument via ``node.nodeoptarg``
    (a ``LatexGroupNode`` for ``[...]`` or ``None``).
    """
    if node.nodeoptarg is None:
        return ""
    if isinstance(node.nodeoptarg, LatexGroupNode):
        return _trim(_nodes_text(node.nodeoptarg.nodelist))
    if isinstance(node.nodeoptarg, LatexCharsNode):
        return _trim(node.nodeoptarg.chars)
    return ""


def _is_starred_macro(node: LatexMacroNode) -> bool:
    """Return True if the macro is the starred variant (``\\section*``)."""
    try:
        verbatim = node.latex_verbatim() or ""
    except Exception:
        return False
    return bool(re.search(rf"\\{re.escape(node.macroname)}\s*\*", verbatim))


_STRUCTURAL_MACRO_NAMES: frozenset[str] = frozenset({
    "chapter",
    "section",
    "subsection",
    "subsubsection",
    "paragraph",
    "subparagraph",
    "title",
    "part",
    "appendix",
})


def _is_structural_macro(node: LatexMacroNode) -> bool:
    """Return True for macros that break the current paragraph."""
    name = (node.macroname or "").strip("\\").lower()
    return name in _STRUCTURAL_MACRO_NAMES


def _adjacent_caption(node: LatexMacroNode, blocks: list[Block]) -> str | None:
    """Look in the most recent block for a ``caption`` field.

    Used so that ``\\includegraphics{...}`` can pick up a
    ``\\caption{...}`` placed right before it (typical ``figure`` pattern).
    """
    if not blocks:
        return None
    last = blocks[-1]
    if last.metadata and "caption" in last.metadata:
        return str(last.metadata["caption"])
    return None


def _extract_key(opts: str, key: str) -> str | None:
    """Pull a key=value (e.g. ``width=0.5\\textwidth``) out of an option list."""
    m = re.search(rf"{re.escape(key)}\s*=\s*([^,\s\]]+)", opts)
    return m.group(1) if m else None


def _detect_code_language(env: str, node: LatexEnvironmentNode) -> str | None:
    """Return the language for a ``lstlisting``/``minted`` env, if specified."""
    nodelist = node.nodelist or []
    if env == "lstlisting":
        # Look for a `language=foo` macro in the body OR in the
        # environment's optional arg (e.g. \begin{lstlisting}[language=python]).
        opt = node.nodeoptarg if hasattr(node, "nodeoptarg") else None
        if isinstance(opt, LatexGroupNode):
            text = _trim(_nodes_text(opt.nodelist))
            m = re.search(r"language\s*=\s*([A-Za-z0-9_+\-]+)", text)
            if m:
                return m.group(1)
        for n in nodelist:
            if isinstance(n, LatexMacroNode) and n.macroname in {"language", "lstset"}:
                text = _trim(_nodes_text(_macro_arg_nodes(n)))
                if "=" in text:
                    val = text.split("=", 1)[1].strip()
                    if val:
                        return val
    if env == "minted":
        # First group arg of the \begin{minted}{lang} call.
        if node.args:
            first = node.args[0]
            if isinstance(first, LatexGroupNode):
                lang = _trim(_nodes_text(first.nodelist))
                if lang:
                    return lang
        for n in nodelist:
            if isinstance(n, LatexMacroNode) and n.nodeargs:
                first = n.nodeargs[0]
                if isinstance(first, LatexGroupNode):
                    return _trim(_nodes_text(first.nodelist))
    return None


def _macro_arg_nodes(node: LatexMacroNode):
    """Yield the inner nodelist of each group argument of a macro."""
    for arg in node.nodeargs or []:
        if isinstance(arg, LatexGroupNode):
            yield arg.nodelist


def _collect_list_items(nodelist) -> list[str]:
    """Collect ``\\item`` contents from an ``itemize``/``enumerate`` body.

    Each ``\\item`` may be followed by a ``[...]`` optional label (used
    in ``description``) and then the item body, which is everything up
    to the next ``\\item`` or the end of the env.
    """
    items: list[str] = []
    current: list[str] | None = None

    for n in nodelist or []:
        if isinstance(n, LatexMacroNode) and (n.macroname or "").strip() == "item":
            if current is not None:
                text = _trim("".join(current))
                if text:
                    items.append(text)
            current = []
            # \item[label] for description envs
            if n.nodeargs:
                first = n.nodeargs[0]
                if isinstance(first, LatexGroupNode):
                    label = _trim(_nodes_text(first.nodelist))
                    if label and current is not None:
                        current.append(f"{label}: ")
        elif current is not None:
            text = _node_text(n)
            if text:
                current.append(text)

    if current is not None:
        text = _trim("".join(current))
        if text:
            items.append(text)
    return items


def _extract_env_body_from_source(node: LatexEnvironmentNode) -> str:
    """Extract the body of a ``verbatim``/``Verbatim`` env from source.

    pylatexenc doesn't expose verbatim body content in the AST — the
    package's `verbatim` category opts out of normal parsing.  We work
    around this by slicing the source string between ``\\begin{env}``
    and ``\\end{env}`` using the node's ``pos`` and ``len``.
    """
    # Use the latex_verbatim output to get the full original source
    # range, then strip the begin/end wrappers.
    try:
        raw = node.latex_verbatim() or ""
    except Exception:
        raw = ""
    env = (node.environmentname or "").strip()
    begin = f"\\begin{{{env}}}"
    end = f"\\end{{{env}}}"
    # Trim leading/trailing whitespace plus the begin/end lines.
    if raw.startswith(begin):
        raw = raw[len(begin):]
    if raw.rstrip().endswith(end):
        idx = raw.rstrip().rfind(end)
        raw = raw[:idx]
    return raw.strip("\n")


_LEADING_OPTIONS_RE = re.compile(r"^\s*\[[^\]]*\]\s*", re.MULTILINE)


def _strip_leading_options(body: str) -> str:
    """Drop a leading ``[language=foo]``/``[style=...]`` line from a code env body."""
    return _LEADING_OPTIONS_RE.sub("", body, count=1)


def _is_row_terminator(node: LatexMacroNode) -> bool:
    """Return True if the macro is the ``\\\\`` row terminator inside a tabular."""
    name = node.macroname or ""
    if name == "\n":  # default context substitutes ``\\`` with a newline
        return True
    if name == "\\":  # custom context keeps the literal backslash
        return True
    if name in {"\\\\", "tabularnewline", "newline"}:
        return True
    return False
