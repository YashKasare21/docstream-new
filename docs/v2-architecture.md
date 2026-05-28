# Docstream v2 — Technical Architecture

## Overview

v2 extends the original PDF-only pipeline to support **6 input formats** and introduces
semantic document understanding, template-aware content mapping, a multi-provider AI
fallback chain, PDF preview in the browser, and a user feedback system.

---

## Pipeline Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT FILE                               │
│   (.pdf | .docx | .pptx | .jpg/.png | .md | .txt)              │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   FormatRouter     │  Detect extension,
                    │                   │  return handler name
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
   ┌──────▼──────┐   ┌────────▼───────┐  ┌───────▼────────┐
   │ PDFHandler  │   │  DOCXHandler   │  │  PPTXHandler   │
   │ ImageHandler│   │MarkdownHandler │  │  TextHandler   │
   └──────┬──────┘   └────────┬───────┘  └───────┬────────┘
          └───────────────────┼───────────────────┘
                              │
                    List[Block] (common format)
                              │
                    ┌─────────▼──────────┐
                    │  SemanticAnalyzer  │  Detect DocumentType,
                    │                   │  create SemanticChunks,
                    │                   │  extract entities
                    └─────────┬──────────┘
                              │
                    SemanticDocument
                              │
                    ┌─────────▼──────────┐
                    │  TemplateMatcher   │  Map SemanticChunks
                    │                   │  to template fields,
                    │                   │  score compatibility
                    └─────────┬──────────┘
                              │
                    TemplateData
                              │
                    ┌─────────▼──────────┐
                    │  AIProviderChain   │  Generate LaTeX
                    │  (Gemini → Groq    │  from TemplateData
                    │   → Ollama)        │
                    └─────────┬──────────┘
                              │
                    LaTeX source string
                              │
                    ┌─────────▼──────────┐
                    │  QualityChecker    │  Technical check
                    │                   │  (compiles?) +
                    │                   │  Professional check
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │      OUTPUT        │
                    │  document.tex      │
                    │  document.pdf      │
                    └────────────────────┘
```

---

## Stage Details

### Stage 1 — FormatRouter

**Module:** `docstream/core/format_router.py`

Reads the file extension and returns the handler name. Raises `ValueError` for unsupported types.

| Extension | Handler |
|---|---|
| `.pdf` | `pdf` |
| `.docx` | `docx` |
| `.pptx` | `pptx` |
| `.jpg` / `.jpeg` / `.png` | `image` |
| `.md` | `markdown` |
| `.txt` | `text` |

---

### Stage 2 — Format Handlers

**Module:** `docstream/core/format_handlers/`

Each handler converts a raw file into `List[Block]` — the common intermediate
format shared by all downstream stages.

| Handler | Library | Notes |
|---|---|---|
| `PDFHandler` | PyMuPDF + pytesseract | Wraps existing `PDFExtractor`; auto-detects scanned PDFs |
| `DOCXHandler` | python-docx | Preserves heading levels (H1–H6) and table structure |
| `PPTXHandler` | python-pptx | Per-slide: title → body → speaker notes → tables |
| `ImageHandler` | Pillow + pytesseract | Pre-processes image (grayscale, denoise) before OCR |
| `MarkdownHandler` | mistune v3 | Converts AST nodes to Block types |
| `TextHandler` | stdlib | Blank-line paragraph split + heading heuristics |

---

### Stage 3 — SemanticAnalyzer

**Module:** `docstream/core/semantic_analyzer.py`

The core intelligence of v2. Uses AI (via `AIProviderChain`) with a specialized
prompt to understand document meaning — not just structure.

**Outputs:**
- `DocumentType` — enum value (RESUME, RESEARCH_PAPER, ACADEMIC_REPORT, etc.)
- `List[SemanticChunk]` — meaningful content units with `importance` scores and `template_hints`
- `entities` dict — extracted metadata (person name, org, date, etc.)

---

### Stage 4 — TemplateMatcher

**Module:** `docstream/core/template_matcher.py`

Maps `SemanticChunk` objects to named fields in the target template's `TemplateSchema`.
Warns about missing required fields rather than failing silently.

**Supported templates and their schemas:**

| Template | Required Fields | Best For |
|---|---|---|
| `report` | title, abstract, sections | ACADEMIC_REPORT, TECHNICAL_REPORT |
| `ieee` | title, authors, abstract, keywords, sections | RESEARCH_PAPER |
| `resume` | name, contact, experience, education | RESUME |
| `altacv` | same as resume | RESUME |
| `moderncv` | same as resume | RESUME |

---

### Stage 5 — AIProviderChain

**Module:** `docstream/core/ai_provider.py`

Unified interface across all AI providers with automatic fallback.

```
Request → GeminiProvider (Gemini 1.5 Flash)
              ↓ on failure
          GroqProvider (Llama 3.1 70B)
              ↓ on failure
          OllamaProvider (local / Colab ngrok)
              ↓ on failure
          AIUnavailableError
```

All providers implement the same `AIProvider.complete(prompt, system)` interface.

---

### Stage 6 — QualityChecker

**Module:** `docstream/core/quality_checker.py`

Two independent quality dimensions:

**Technical score (0–1):**
- LaTeX compiles without errors (runs XeLaTeX in temp dir)
- All packages available
- No undefined commands
- Balanced `\begin` / `\end` environments

**Professional score (0–1):**
- Consistent heading hierarchy
- No empty sections
- Bibliography formatted correctly
- Content fills template meaningfully

A `QualityReport` with `passed: bool` gates the final output.

---

## New API Endpoints (v2)

All v2 endpoints live under `/api/v2/`. v1 endpoints are untouched.

| Method | Path | Description | Status |
|---|---|---|---|
| `POST` | `/api/v2/convert` | Multi-format upload → `job_id` | Phase 8 |
| `GET` | `/api/v2/preview/{job_id}` | Base64 PDF for PDF.js | Phase 12 |
| `POST` | `/api/v2/feedback` | Emoji + comment feedback | Phase 14 |
| `GET` | `/api/v2/formats` | Supported format list | Phase 8 |

---

## New Frontend Components (v2)

| Path | Purpose | Phase |
|---|---|---|
| `src/app/preview/page.tsx` | PDF.js viewer + download buttons | 12 |
| `src/components/convert/FormatSelector.tsx` | Format icon picker | 8 |
| `src/components/feedback/FeedbackWidget.tsx` | Emoji + text feedback | 14 |

---

## Dependency Changes

New dependencies added to `docstream/pyproject.toml`:

| Package | Version | Used By |
|---|---|---|
| `python-docx` | ≥1.1.0 | `DOCXHandler` |
| `python-pptx` | ≥1.0.0 | `PPTXHandler` |
| `mistune` | ≥3.0.0 | `MarkdownHandler` |
| `ollama` | ≥0.3.0 | `OllamaProvider` |
| `Pillow` | ≥10.0.0 | `ImageHandler` |
