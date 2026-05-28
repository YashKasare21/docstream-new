# Contributing to DocStream

Welcome! We're thrilled you're interested in contributing to DocStream — an open-source, FOSS-only document conversion platform.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Set Up Locally](#how-to-set-up-locally)
- [How to Run Tests](#how-to-run-tests)
- [Code Style](#code-style)
- [How to Submit a PR](#how-to-submit-a-pr)
- [Project Structure](#project-structure)

---

## Code of Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/). Be respectful, inclusive, and constructive in all interactions.

---

## How to Set Up Locally

### Prerequisites

| Tool      | Minimum Version | Install                                                           |
| --------- | --------------- | ----------------------------------------------------------------- |
| Python    | 3.11            | [python.org](https://www.python.org/downloads/)                   |
| Node.js   | 20              | [nodejs.org](https://nodejs.org/)                                 |
| XeLaTeX   | —               | `sudo apt install texlive-xetex texlive-latex-extra texlive-fonts-recommended` |
| Tesseract | —               | `sudo apt install tesseract-ocr`                                  |

### Quick Setup

```bash
git clone https://github.com/YashKasare21/docstream-new.git
cd docstream-new
make install
```

`make install` creates two Python virtual environments (`apps/cli-python/.venv` and `apps/api-python/.venv`) with the core library installed editably into both, and runs `npm install` for the web frontend.

### Run the Dev Stack

```bash
# API (port 8000) + Web (port 3000) concurrently:
make dev

# Or individually:
make dev-api
make dev-web
```

### Activate the CLI

```bash
source apps/cli-python/.venv/bin/activate
docstream convert paper.pdf --template ieee --output ./out
```

---

## How to Run Tests

```bash
# Run all Python tests (core + CLI + API):
make test

# Run core + API tests only:
make test-python

# Run a single test file:
cd apps/api-python && ./.venv/bin/pytest tests/test_convert.py -v

# Run a single test:
cd apps/api-python && ./.venv/bin/pytest tests/test_convert.py::test_health_endpoint_returns_ok -v
```

---

## Code Style

DocStream uses **Ruff** for Python and **Prettier + ESLint** for JavaScript/TypeScript.

```bash
# Python lint + format
make lint-python
make format-python

# Web lint + format
make lint-web
npx prettier --write .   # inside apps/web-node
```

**Python rules** (enforced by Ruff):
- `E` / `W` — pycodestyle
- `F` — pyflakes (unused imports, undefined names)
- `I` — isort (import ordering)
- Line length: **120 characters**

**TypeScript rules** (enforced by ESLint):
- Strict mode — no `any` without justification
- All component props must have explicit interfaces
- No unused imports

---

## How to Submit a PR

1. **Fork** the repository and create your branch from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
2. **Make your changes** — keep them focused and atomic.
3. **Run all checks** locally:
   ```bash
   make test-python
   make lint-python
   make lint-web
   ```
4. **Commit** using conventional commits:
   ```
   feat: add support for DOCX output
   fix: handle missing API key gracefully
   docs: update API reference
   ```
5. **Push** and open a Pull Request against `main`.
6. In the PR description, fill out the template — describe what changed, how it was tested, and link any related issues.
7. A maintainer will review your PR. CI must pass before merge.

---

## Project Structure

```
docstream-new/
├── packages/
│   └── core-python/       # Shared library — the conversion engine
│       ├── docstream/     # Importable as `import docstream`
│       └── tests/
├── apps/
│   ├── cli-python/        # Terminal CLI
│   ├── api-python/        # FastAPI backend
│   └── web-node/          # Next.js 16 frontend
├── docker/                # Dockerfiles
├── docs/                  # Documentation
├── Makefile               # Project orchestrator
└── README.md
```
