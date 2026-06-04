# 📄 DocStream

> High-performance, AI-powered document processing engine with real-time streaming and a modular plugin architecture.

[![CI](https://github.com/YashKasare21/docstream-new/actions/workflows/ci.yml/badge.svg)](https://github.com/YashKasare21/docstream-new/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-16-black.svg)](https://nextjs.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 🚀 Demo

| Upload & Configure | Real-Time AI Streaming (Dark Mode) |
| :---: | :---: |
| ![DocStream Upload Screen](./assets/upload-screen.png) | ![DocStream Streaming Dark Mode](./assets/streaming-dark-mode.png) |

*Watch DocStream process documents chunk-by-chunk in real-time using Server-Sent Events (SSE).*

---

## 🎯 Why DocStream?

DocStream isn't just a document converter—it's a blueprint for modern full-stack architecture. Built to demonstrate **system design, decoupled modularity, and real-time streaming**, it separates a high-performance Python processing core from dual interfaces (CLI & Web).

---

## ✨ Key Features

- **Real-Time Streaming:** Watch documents process chunk-by-chunk via Server-Sent Events (SSE), enabling chunk-by-chunk document delivery and real-time progress tracking.
- **AI-Powered Extraction:** Leverages LLMs (Gemini/Groq) to intelligently structure complex PDFs into LaTeX.
- **Dual Interface:** Powerful CLI for automation + Intuitive Next.js Web UI for end-users.
- **Plugin Architecture:** Extensible pipeline system. Write a Python class and inject it into the processing stream without touching core code.
- **LaTeX Input & Re-templating:** Upload `.tex` files to parse, re-structure, and apply new templates (e.g., convert a report to a modern CV).
- **Standalone Compile API:** Direct `/api/v2/compile` endpoint to turn `.tex` files into PDFs via XeLaTeX.
- **Multi-Format Export:** Export converted documents to DOCX, HTML, Markdown, or EPUB via Pandoc.
- **Equation OCR Plugin:** Extract mathematical equations from images using the open-source `pix2tex` library via a drop-in Pipeline Stage.
- **Five Built-In Templates:** `report`, `ieee`, `resume`, `altacv`, and `moderncv` — pick the layout that fits the document.
- **Hybrid Monorepo:** Python core engine + Next.js frontend, managed seamlessly together.
- **One-Command Deploy:** Fully containerized with Docker Compose for zero-friction local deployment.

---

## 🏗️ Architecture

DocStream is built on a decoupled, service-oriented architecture where the Python core engine is entirely independent of the interfaces that consume it.

```mermaid
graph TD
    A[Next.js Web UI] -->|SSE / REST| B(FastAPI Backend)
    C[Python CLI] -->|Local Import| B
    B --> D[DocStream Core Engine]
    D --> E[Pipeline Stage 1: Parser]
    D --> F[Pipeline Stage 2: AI Structurer]
    D --> G[Pipeline Stage 3: Custom Plugin]
    D --> H[Format Router - PDF, LaTeX, DOCX, MD, ...]
    D --> I[Pandoc Multi-Format Exporter]
    F --> J[LLM Providers: Groq / Gemini / Ollama]
    G --> K[EquationOCRStage - pix2tex]
```

---

## 🐳 Quick Start (Docker)

The fastest way to get DocStream running locally:

```bash
git clone https://github.com/YashKasare21/docstream-new.git
cd docstream-new
```

Add your AI API keys to a root `.env` file ([Get a free Groq key here](https://console.groq.com/)):

```env
GROQ_API_KEY=your_key_here
```

Start the stack:

```bash
make docker-up
```

Access the **Web UI** at [http://localhost:3000](http://localhost:3000) and the **API docs** at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## 🛠️ Local Development

| Command | Description |
|---|---|
| `make install` | Install Python dependencies + npm modules |
| `make dev` | Run API + Web concurrently |
| `make test-python` | Run all Python tests |
| `make lint-python` | Lint Python sources with Ruff |
| `make docker-up` | Spin up full stack via Docker Compose |
| `make docker-down` | Tear down Docker services |

---

## 🧩 Creating a Plugin

DocStream uses a simple pipeline architecture. Drop a custom stage into the processing stream and DocStream will pass every block of content through it. Here is a real-world example — the **equation OCR** stage that ships with DocStream v1.1.0:

```python
from docstream.plugins import EquationOCRStage
from docstream.pipeline import Pipeline

# Walk every IMAGE block in the document, run pix2tex, and emit a CODE
# block carrying the predicted LaTeX (wrapped in $...$ or $$...$$).
pipeline = Pipeline([EquationOCRStage()])
result = pipeline.run({"blocks": extracted_blocks})
```

Or build your own from scratch:

```python
from docstream.pipeline import PipelineStage

class MyCustomStage(PipelineStage):
    @property
    def name(self) -> str:
        return "my_custom_stage"

    async def process(self, data: dict) -> dict:
        text = data.get("text", "")
        # Do something with the text
        data["text"] = text.upper()
        return data
```

---

## 🌐 API Endpoints

All endpoints live under the `/api/v2` prefix and are documented in OpenAPI at `/docs`.

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v2/convert` | Convert a document to LaTeX + final output. Accepts **PDF, `.tex`, `.latex`** input. `?output_format=pdf \| docx \| html \| md \| markdown \| epub` controls the returned file. |
| `POST` | `/api/v2/stream` | Real-time **SSE** streaming of the LaTeX generation (PDF output only). |
| `POST` | `/api/v2/compile` | Standalone **`.tex` → `.pdf`** compilation via XeLaTeX — no AI step. |
| `GET`  | `/api/v2/files/{job_id}/{filename}` | Download a previously-generated `.tex` or `.pdf` artifact. |
| `GET`  | `/api/v2/formats` | List supported input formats. |
| `POST` | `/api/v2/feedback` | Submit a 👍/👎 rating for a finished job. |
| `GET`  | `/api/v2/providers` | List configured AI providers. |
| `GET`  | `/api/health` | Liveness probe. |

---

## 🗺️ Roadmap

### v1.1.0 — Shipped
- [x] **LaTeX Input & Re-templating** — `.tex` / `.latex` parsing via the format router
- [x] **Standalone Compile API** — `/api/v2/compile`
- [x] **Multi-Format Export** — Pandoc-backed DOCX / HTML / MD / EPUB routing
- [x] **Equation OCR Plugin** — pix2tex-backed `EquationOCRStage`
- [x] **Resume / AltaCV / ModernCV templates** — unlocked end-to-end

### v2.0 — Next Major
- [ ] **Authentication & Job History:** Integrate NextAuth.js and SQLAlchemy to persist conversion history and allow users to redownload past jobs.

---

## 📁 Project Structure

```
docstream/
├── packages/
│   └── core-python/      # The shared processing engine (PDF -> AI -> LaTeX)
├── apps/
│   ├── cli-python/       # CLI interface (consumes core)
│   ├── api-python/       # FastAPI backend (consumes core)
│   └── web-node/         # Next.js 16 frontend (consumes API via SSE)
├── docker/               # Dockerfiles for API and Web
├── Makefile              # The orchestrator
└── .github/workflows/    # CI/CD pipelines
```

---

## 🤝 Contributing

We love contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.
