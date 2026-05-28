# DocStream

> AI-powered document conversion (PDF → LaTeX → PDF) — open source, FOSS-only stack.

[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/next.js-16-black)](https://nextjs.org/)
[![Status](https://img.shields.io/badge/status-active%20development-orange)]()

> ⚠️ **Active development.** APIs, paths, and packaging are still moving — pin a commit if you depend on this.

---

## What is DocStream?

DocStream converts documents (PDF, DOCX, PPTX, images, Markdown) into publication-quality **LaTeX**
using a fallback chain of AI providers (Gemini → Groq → NVIDIA NIM → Ollama), then compiles them
with XeLaTeX. It ships as:

- A **Python library** (`docstream-core`) — the actual conversion engine
- A **CLI** (`docstream`) — for terminal use and scripts
- A **FastAPI backend** — exposes the engine as an HTTP service
- A **Next.js 16 web frontend** — the user-facing app

---

## 🏛️ Repository structure

This is a **hybrid monorepo** — Python packages glued together with local-path installs, plus a
standalone Next.js app. No Nx, Turborepo, Pants, or Bazel — just standard tooling and a `Makefile`.

```
docstream-new/
├── packages/
│   └── core-python/          # Shared library (docstream)
│       ├── pyproject.toml    # name = "docstream-core"
│       ├── docstream/        # Importable as `import docstream`
│       └── tests/
├── apps/
│   ├── cli-python/           # Terminal interface
│   │   ├── pyproject.toml    # depends on docstream-core (local path)
│   │   ├── docstream_cli/
│   │   └── tests/
│   ├── api-python/           # FastAPI backend
│   │   ├── pyproject.toml    # depends on docstream-core (local path)
│   │   ├── docstream_api/
│   │   └── tests/
│   └── web-node/             # Next.js 16 frontend
│       ├── package.json
│       └── src/
├── docker/                   # Dockerfiles
├── docs/                     # Project documentation
├── Makefile                  # The orchestrator
├── LICENSE                   # MIT
└── README.md
```

### Why this layout?

- **Standard Python packaging** — `pip install -e .` with local-path dependencies, no custom publishing.
- **Zero friction for Next.js** — the web app stays in its own Node environment and only talks to the
  API over HTTP. It doesn't need to know Python exists.
- **Make is the glue** — contributors run `make install` and `make dev`, that's it.

---

## 🚀 Quick start

### Prerequisites

- Python **3.11+**
- Node.js **20+** with `npm`
- XeLaTeX (for compilation): `sudo apt install texlive-xetex texlive-latex-extra texlive-fonts-recommended`
- An API key for at least one AI provider (Gemini recommended — free tier, 1500 req/day)

### Install everything

```bash
git clone https://github.com/YashKasare21/docstream-new.git
cd docstream-new
make install
```

This creates two Python venvs (`apps/cli-python/.venv`, `apps/api-python/.venv`) with the core
library installed editably into both, and runs `npm install` for the web app.

### Run the dev stack

```bash
# In one terminal — runs both API (port 8000) and Web (port 3000):
make dev

# Or run them individually:
make dev-api   # FastAPI backend at http://localhost:8000
make dev-web   # Next.js frontend at http://localhost:3000
```

### Use the CLI

```bash
source apps/cli-python/.venv/bin/activate
docstream convert paper.pdf --template ieee --output ./out
docstream templates list
```

---

## 🔑 Configuration

Create a `.env` file at the repo root (or per-app):

```env
GEMINI_API_KEY=your_gemini_key
GROQ_API_KEY=your_groq_key            # optional fallback
NVIDIA_API_KEY=your_nvidia_key        # optional fallback
OLLAMA_BASE_URL=http://localhost:11434  # optional local fallback
ALLOWED_ORIGINS=http://localhost:3000   # CORS for the API
```

All providers are optional — DocStream falls back automatically.

---

## 🧪 Testing & linting

```bash
make test     # Run pytest across core, cli, and api
make lint     # Ruff (Python) + ESLint (Web)
make format   # Auto-format Python with ruff
make clean    # Nuke venvs and caches
```

---

## 📦 Per-package READMEs

- [`packages/core-python/README.md`](packages/core-python/README.md) — the conversion library
- [`apps/cli-python/README.md`](apps/cli-python/README.md) — the CLI
- [`apps/api-python/README.md`](apps/api-python/README.md) — the FastAPI backend
- [`apps/web-node/README.md`](apps/web-node/README.md) — the Next.js frontend

---

## 🤝 Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). All contributions welcome — the project is FOSS-only;
please don't add proprietary or paid services to the stack.

---

## 📄 License

[MIT](LICENSE) — © 2024–2026 Yash Kasare and contributors.
