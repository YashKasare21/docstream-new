# DocStream v2.0

> Privacy-first document processing platform that converts unstructured documents into professional LaTeX/PDF output.

[![CI](https://github.com/YashKasare21/docstream-new/actions/workflows/ci.yml/badge.svg)](https://github.com/YashKasare21/docstream-new/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

Privacy-first document processing platform that converts unstructured documents into professional LaTeX/PDF output.

<!-- TODO: Insert demo GIF here -->
<!-- ![Demo GIF](assets/demo.gif) -->

---

## Features ✅

- Bidirectional PDF ↔ LaTeX conversion
- AI-powered structuring with 4-provider fallback chain (Gemini Flash → Groq Llama → Kimi → Ollama)
- 5 LaTeX templates: Report, IEEE, Resume, AltaCV, ModernCV
- Multi-format export: PDF, DOCX, HTML, Markdown, EPUB via Pandoc
- Real-time SSE streaming with live progress
- Live Monaco editor with inline PDF preview
- Batch ZIP conversion with background processing
- Google OAuth authentication + JWT-secured API
- IDOR protection on all user-scoped endpoints
- Stripe subscriptions (Free: 5/month, Pro: unlimited)
- Monthly usage reset + subscription cancellation handling
- Job history with redownload
- Plugin architecture (PipelineStage ABC) for custom processing
- Docker Compose one-command local setup
- Alembic database migrations

---

## Architecture

![Architecture Diagram](assets/architecture_diagram.jpeg)

DocStream implements a strict three-stage pipeline — **Extract → Structure → Render** — where each stage has a single responsibility, a typed input/output contract, and is independently testable.

### Extraction Layer
PyMuPDF extracts text with full font metadata (size, bold, italic, bounding boxes). When extracted text falls below 100 chars per page (scanned documents), OCR fallback via Tesseract takes over. Table detection via PyMuPDF `find_tables()` and image extraction complete the layer. Output: `List[Block]`.

### Structuring Layer (AI)
Blocks are serialized to JSON and sent through a multi-provider LLM chain with exponential-backoff retry. Gemini 1.5 Flash (primary) → Groq Llama 3.1 70B → Kimi → Ollama (local). The model returns a validated `DocumentAST` — a typed hierarchy of title, sections, metadata, tables, and images. Invalid JSON responses are caught by Pydantic v2 schema validation.

### Rendering Layer
`DocumentAST` is serialized to Pandoc JSON, then passed through a Lua custom writer that emits LaTeX. XeLaTeX runs a two-pass compilation (for cross-references and ToC). The `.log` file is parsed for `!` error lines. For non-PDF output, Pandoc routes to DOCX, HTML, Markdown, or EPUB.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16, TypeScript (strict), Tailwind CSS v4, shadcn/ui, Framer Motion |
| Backend | FastAPI (Python 3.11+), Pydantic v2, SQLAlchemy, Alembic |
| Core Engine | PyMuPDF, Pandoc 3.x Lua writers, XeLaTeX, Tesseract OCR |
| AI Providers | Gemini 1.5 Flash, Groq Llama 3.1 70B, Kimi, Ollama |
| LaTeX Engine | XeLaTeX (texlive-xetex) with two-pass compilation |
| Database | SQLite (dev) / PostgreSQL 16 (prod) |
| Auth | NextAuth.js v4 with Google OAuth + JWT Bearer tokens |
| Payments | Stripe Checkout + Webhooks (Free / Pro plans) |
| Infrastructure | Docker Compose, Railway (backend), Vercel (frontend) |

---

## Project Structure

```
docstream-new/
├── packages/
│   └── core-python/        # Shared conversion engine — importable as `docstream`
│       ├── docstream/      # Pipeline stages, models, templates, providers
│       └── tests/          # Core pytest suite
├── apps/
│   ├── api-python/         # FastAPI backend — REST + SSE endpoints (deployed on Railway)
│   │   ├── docstream_api/  # Routes, services, database models, Stripe integration
│   │   └── tests/          # API integration tests
│   ├── cli-python/         # CLI interface — `docstream convert`, `docstream extract`
│   └── web-node/           # Next.js 16 frontend (deployed on Vercel)
│       ├── src/
│       │   ├── app/        # App Router pages (convert, preview, stats, billing, history)
│       │   ├── components/ # Landing, convert, preview, feedback, ui (shadcn)
│       │   └── lib/        # API client, auth helpers, utilities
│       └── public/
├── docker/                 # Dockerfiles for API and Web
├── docs/                   # Documentation (architecture, templates, API reference)
├── assets/                 # Screenshots, architecture diagram
├── Makefile                # Monorepo orchestrator (install, dev, test, lint)
└── .github/workflows/      # CI/CD pipelines (pytest, ruff, mypy)
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- XeLaTeX (`sudo apt install texlive-xetex texlive-latex-extra texlive-fonts-recommended`)
- Docker (optional, for containerized setup)

### Clone and Setup

```bash
git clone https://github.com/YashKasare21/docstream-new.git
cd docstream-new
```

### Backend Setup

Create `apps/api-python/.env`:

```env
GROQ_API_KEY=gsk_your_key_here
GEMINI_API_KEY=AIza_your_key_here
HOST=0.0.0.0
PORT=8000
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
NEXTAUTH_SECRET=generate-a-random-secret

# Stripe (required for billing)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_SUCCESS_URL=http://localhost:3000/billing?success=true
STRIPE_CANCEL_URL=http://localhost:3000/billing?canceled=true
```

```bash
cd apps/api-python
python3 -m venv .venv
source .venv/bin/activate
pip install -e ../../packages/core-python
pip install -e .
uvicorn docstream_api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

Create `apps/web-node/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=same-secret-as-backend
GOOGLE_CLIENT_ID=your-google-oauth-client-id
GOOGLE_CLIENT_SECRET=your-google-oauth-client-secret
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

```bash
cd apps/web-node
npm install
npm run dev
```

### Run with Docker

```bash
docker compose up --build
```

### Open

Visit [http://localhost:3000](http://localhost:3000) — API docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## API Reference

All endpoints live under the `/api/v2/` prefix (except `/compile` and webhook). All authenticated endpoints require `Authorization: Bearer <jwt>` header.

| Method | Path | Description | Auth |
|---|---|---|---|
| `POST` | `/api/v2/convert` | Full document conversion — accepts PDF, DOCX, PPTX, images, Markdown, plain text | Yes |
| `POST` | `/api/v2/stream` | SSE streaming conversion — real-time LaTeX generation with progress events | Yes |
| `POST` | `/api/v2/compile` | Direct `.tex` → `.pdf` via XeLaTeX (bypasses AI) | No |
| `POST` | `/api/v2/batch` | ZIP batch processing — fans out multiple documents in the background | Yes |
| `GET` | `/api/v2/jobs` | Job history — list past conversions with download URLs | Yes |
| `GET` | `/api/v2/billing/usage` | Current plan and monthly usage | Yes |
| `POST` | `/api/v2/billing/checkout` | Create Stripe Checkout session for Pro upgrade | Yes |

Query parameters for `/convert` and `/stream`:
- `?template=` — one of `report`, `ieee`, `resume`, `altacv`, `moderncv` (default: `report`)
- `?output_format=` — `pdf`, `docx`, `html`, `md`, `epub` (default: `pdf`)
- `?enable_equation_ocr=true` — opt-in LaTeX-OCR for equation images

---

## Templates

| Template | Use Case |
|---|---|
| `report` | Academic reports, technical documentation — article class, 1-inch margins, lmodern serif |
| `ieee` | Conference papers, research articles — IEEEtran class, two-column, 10pt |
| `resume` | Professional resumes — compact 0.6in margins, no section numbers |
| `altacv` | Academic CVs — AltaCV class with publication lists and funding sections |
| `moderncv` | Modern curriculum vitae — ModernCV class with multiple style variants (casual, classic, banking) |

---

## Monetization / Pricing

| Plan | Price | Conversions | Templates | Batch |
|---|---|---|---|---|
| Free | $0 | 5/month | All | No |
| Pro | $9.99/month | Unlimited | All | Yes |

Pro users get priority processing, unlimited conversions, batch ZIP support, and priority support. Stripe handles billing with automatic monthly reset and subscription cancellation handling via webhooks.

---

## Contributing

We love contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed setup instructions, code style guidelines, and the PR process.

Quick start for contributors:

```bash
git clone https://github.com/YashKasare21/docstream-new.git
cd docstream-new
make install        # Install all dependencies (venvs + npm)
make dev            # Run API + Web concurrently
make test           # Run all Python tests
make lint           # Lint Python + TypeScript
```

---

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## Author

**Yash Kasare**

- GitHub: [github.com/YashKasare21](https://github.com/YashKasare21)
- LinkedIn: [linkedin.com/in/yash-kasare-ai](https://linkedin.com/in/yash-kasare-ai)
