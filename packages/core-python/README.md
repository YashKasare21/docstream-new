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

## Plugin Architecture (Pipeline)

DocStream ships with a pluggable **Pipeline** system.  The built-in
`convert()` function is just a shorthand for:

```python
from docstream import Pipeline, LatexExtractionStage

pipeline = Pipeline([LatexExtractionStage()])
data = await pipeline.run({
    "file_path": "paper.pdf",
    "template": "ieee",
    "output_dir": "./out",
})
```

You can inject custom stages between or around the built-in ones.
For example, to clean whitespace after generation:

```python
from docstream import Pipeline, LatexExtractionStage
from docstream.plugins.cleaner import WhitespaceCleanerStage

pipeline = Pipeline([
    LatexExtractionStage(),
    WhitespaceCleanerStage(),
])
data = await pipeline.run({"file_path": "paper.pdf"})
```

To write your own stage, subclass `PipelineStage`:

```python
from docstream.pipeline import PipelineStage

class MyCustomStage(PipelineStage):
    name = "my_custom_stage"

    async def process(self, data: dict) -> dict:
        data["greeting"] = "Hello, world!"
        return data
```

All stages receive and return a mutable `data` dict, allowing them to
inspect and modify document state at any point in the pipeline.

## License

MIT — see the root [`LICENSE`](../../LICENSE).
