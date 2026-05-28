# docstream-cli

Command-line interface for **DocStream** — convert PDFs to LaTeX from your terminal.

```bash
docstream convert paper.pdf --template ieee --output ./out
docstream extract paper.pdf --output blocks.json
docstream templates list
```

Wraps the [`docstream-core`](../../packages/core-python/) library and exposes it as a friendly CLI.

> Part of the [DocStream monorepo](../../README.md). Under active development.

## Installation (from monorepo root)

```bash
make install
```

Or standalone, in editable mode:

```bash
pip install -e ../../packages/core-python
pip install -e .
```

## License

MIT — see the root [`LICENSE`](../../LICENSE).
