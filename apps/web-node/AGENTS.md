# Docstream Web — Agent Guidelines

## Project Overview

Docstream is an AI-powered PDF → LaTeX/PDF conversion system.
- **Frontend**: Next.js 16 App Router, TypeScript (strict), Tailwind CSS v4, shadcn/ui, Framer Motion
- **Backend**: FastAPI (Python 3.11+), `docstream` library
- **Deploy**: Vercel (frontend), Railway (backend)
- **Design**: Dark mode first, glass morphism, Linear.app aesthetic

---

## Build Commands

### Frontend (run from repo root)
```bash
npm run dev          # Development server at http://localhost:3000
npm run build        # Production build — MUST pass before merging
npm run lint         # ESLint check
npx tsc --noEmit    # TypeScript type check — zero errors required
```

### Backend (run from `docstream-api/`)
```bash
source .venv/bin/activate              # Activate virtual environment
uvicorn main:app --reload            # Dev server at http://localhost:8000
pytest                                 # Run all tests
pytest tests/test_file.py             # Run single test file
pytest tests/test_file.py::test_name   # Run single test function
pytest tests/ -k "pattern"           # Run tests matching pattern
```

---

## Code Style

### TypeScript (Frontend)
- **Strict mode**: No `implicit any`, no `any` without justification comment
- **Props interfaces**: All component props must have explicit interfaces
- **API types**: All API responses must be typed with interfaces
- **Naming**: Components in `PascalCase`, hooks/utils in `camelCase`, constants in `UPPER_SNAKE_CASE`
- **Imports**: Use path aliases (`@/` for `src/`). Sort: built-ins → external → internal → relative
- **No unused imports**: ESLint enforces this

### Python (Backend)
- **Type hints**: Mandatory on all function signatures
- **Pydantic models**: Required for all request/response schemas
- **Custom exceptions**: Use docstream's typed exceptions (`ExtractionError`, `RenderingError`, etc.)
- **No bare except**: Never let raw exceptions bubble to HTTP responses
- **Error mapping**: Map exceptions to appropriate HTTP status codes (never raw 500s for expected errors)

### General
- **No console.log**: Use proper logging instead
- **No hardcoded secrets**: Use environment variables exclusively
- **No TODO comments**: File a GitHub issue instead
- **Functions**: Break down if over 40 lines
- **New files**: Include module docstring explaining purpose

---

## Architecture & Boundaries

```
Frontend (src/)
├── app/                    ← Next.js App Router pages
│   ├── page.tsx           ← Landing page
│   ├── convert/page.tsx   ← Conversion flow (state machine pattern)
│   ├── preview/page.tsx   ← PDF preview with PDF.js
│   ├── stats/page.tsx     ← Feedback statistics
│   └── api/v2/           ← Proxy routes to backend
├── components/
│   ├── landing/           ← Landing page components
│   ├── convert/           ← Conversion flow components
│   ├── preview/           ← PDF preview components
│   ├── feedback/          ← Feedback widget
│   └── ui/                ← shadcn/ui primitives (do NOT edit)
└── lib/
    ├── api.ts             ← Backend API calls
    └── utils.ts           ← Utility functions (cn helper)

Backend (docstream-api/)
├── main.py                ← FastAPI entry point
├── routes/               ← Endpoint definitions (keep thin)
├── services/             ← Business logic (calls docstream)
├── models/              ← Pydantic schemas
├── utils/               ← File handling, cleanup
├── database.py          ← SQLite feedback storage
└── tests/               ← pytest tests + conftest.py
```

---

## Git & Branching

- `main`: Production only — never push directly
- `dev`: Integration branch — all PRs target here
- Branch prefixes: `feature/`, `fix/`, `chore/`

**Commit format**: `<type>(<scope>): <short summary>`

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `ci`

Examples:
- `feat(convert): add multi-format upload support`
- `fix(preview): handle missing PDF gracefully`
- `refactor(api): extract feedback submission to hook`

---

## UI/Design Rules

- **Dark mode only**: Background `#0F172A`, surface `#1E293B`
- **Primary blue**: `#1E40AF`, accent `#3B82F6`
- **Text**: `#F8FAFC` primary, `#94A3B8` muted
- **Border radius**: 12px cards, 8px buttons, 6px inputs
- **Animations**: 200–300ms, `ease-in-out`, Framer Motion
- **Shadows**: Use subtle glow (`0 0 20px rgba(59,130,246,0.15)`) instead of harsh shadows
- **Fonts**: Inter for UI, JetBrains Mono for code/filenames

### Accessibility
- Every interactive element needs hover AND focus states
- Animations must respect `prefers-reduced-motion`
- Loading states are mandatory — never leave user without feedback
- Error messages must be human-readable — no raw exception text

### Prohibited
- Default browser alerts (use toast notifications)
- Layout shift during loading
- Text truncation without tooltip
- Buttons without loading state during async actions

---

## Key Reference Files

- `src/app/convert/page.tsx` — State machine pattern for conversion flow
- `src/components/convert/DropZone.tsx` — Upload UX with drag-drop and validation
- `src/components/preview/PDFPreview.tsx` — PDF.js integration
- `src/components/feedback/FeedbackWidget.tsx` — Feedback UI (Phase 14, stubbed)
- `docstream-api/routes/convert.py` — API route contracts (v1 + v2)
- `docstream-api/services/converter.py` — Conversion service (5-stage pipeline)
- `docstream-api/tests/conftest.py` — Test fixtures and patterns

---

## Non-Negotiables

1. **NEVER** commit `.env` files or API keys
2. **NEVER** push directly to `main`
3. **ALWAYS** run `npm run lint` + `npm run build` before finishing frontend tasks
4. **ALWAYS** run `pytest` before finishing backend tasks
5. **NEVER** introduce breaking changes to the external `docstream` library
6. Keep changes scoped to this repo only
