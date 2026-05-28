# docstream-api

FastAPI backend for **DocStream** — exposes document conversion as an HTTP service.

```bash
# From monorepo root:
make dev-api

# Then hit:
curl http://localhost:8000/api/health
```

Endpoints:

| Method | Path                        | Description                  |
|--------|-----------------------------|------------------------------|
| `POST` | `/api/v2/convert`           | Upload a document, get LaTeX |
| `GET`  | `/api/v2/files/{id}/{name}` | Download converted output    |
| `GET`  | `/api/v2/formats`           | List supported input formats |
| `POST` | `/api/v2/feedback`          | Submit feedback              |
| `GET`  | `/api/v2/feedback/stats`    | Aggregated feedback stats    |
| `GET`  | `/api/health`               | Health check                 |
| `GET`  | `/api/v2/providers`         | AI provider status           |

Wraps the [`docstream-core`](../../packages/core-python/) library.

> Part of the [DocStream monorepo](../../README.md). Under active development.

## Installation (from monorepo root)

```bash
make install
```

## Environment variables

| Variable           | Default                          | Description                                    |
|--------------------|----------------------------------|------------------------------------------------|
| `GEMINI_API_KEY`   | —                                | Gemini API key (recommended primary provider)  |
| `GROQ_API_KEY`     | —                                | Groq API key (fallback)                        |
| `ALLOWED_ORIGINS`  | `http://localhost:3000`          | Comma-separated CORS allow-list                |
| `DB_PATH`          | `/tmp/docstream/feedback.db`     | SQLite path for feedback storage               |

## License

MIT — see the root [`LICENSE`](../../LICENSE).
