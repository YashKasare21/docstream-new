# Project Guidelines

## Architecture
- This repo has two apps:
- Frontend in `src/` (Next.js App Router + TypeScript + Tailwind + shadcn/ui).
- Backend in `docstream-api/` (FastAPI + docstream Python library).
- Keep boundaries clear:
- UI/page composition in `src/app/**` and `src/components/**`.
- Frontend API helpers in `src/lib/api.ts`.
- HTTP route definitions in `docstream-api/routes/**`.
- Conversion/business logic in `docstream-api/services/**`.
- Schemas in `docstream-api/models/**`.

## Build And Test
- Frontend (run from repo root):
- `npm run dev`
- `npm run lint`
- `npm run build`
- Backend (run from `docstream-api/`):
- `source .venv/bin/activate`
- `uvicorn main:app --reload`
- `pytest`
- If you add backend features, run backend tests before finishing.
- If you change frontend code, run `npm run lint` and `npm run build` before finishing.

## Conventions
- Use strict TypeScript. Avoid implicit `any`.
- Keep component files in PascalCase and utility files in camelCase.
- Prefer typed API contracts; keep response shapes explicit.
- Do not edit `src/components/ui/**` unless explicitly requested (treat as shared UI primitives).
- Keep user-facing error messages clean. Do not expose raw backend/internal exception text.
- Do not hardcode secrets or keys. Use environment variables.
- Preserve existing branch discipline if doing git work: `feature/*` or `fix/*` into `dev`, never direct to `main`.

## Pitfalls
- Frontend `src/lib/api.ts` currently includes mocked conversion behavior; verify whether a task expects real backend calls before changing flow logic.
- Local backend runtime may require system tools (`pandoc`, TeX packages, `tesseract`) for full document rendering; container setup already installs them.
- Keep changes scoped to this repo. Do not introduce breaking assumptions about the external `docstream` library from this codebase.

## Key Reference Files
- `src/app/convert/page.tsx` for conversion flow/state pattern.
- `src/components/convert/DropZone.tsx` for upload UX and validation behavior.
- `docstream-api/routes/convert.py` for API route shape and response contract.
- `docstream-api/tests/test_convert.py` and `docstream-api/tests/conftest.py` for backend test patterns.
