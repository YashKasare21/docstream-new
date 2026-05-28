# docstream-core

Shared core library for **DocStream** — AI-powered document conversion (PDF → LaTeX → PDF).

This package contains all the format handlers, AI provider chain, template matching, semantic
analysis, LaTeX generation and XeLaTeX compilation logic. It is consumed by:

- [`docstream-cli`](../../apps/cli-python/) — terminal interface
- [`docstream-api`](../../apps/api-python/) — FastAPI backend

> Part of the [DocStream monorepo](../../README.md). Under active development.

## Installation (standalone)

```bash
pip install -e .
```

## Usage

```python
import docstream

result = docstream.convert("paper.pdf", template="ieee", output_dir="./out")
if result.success:
    print(result.tex_path, result.pdf_path)
```

## License

MIT — see the root [`LICENSE`](../../LICENSE).
