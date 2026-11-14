# frontend/ — Clinician interface

The ChronoVoice interface for primary-care clinicians: the people followed, each
person's change from their own baseline, session details with the highlighted
transcript, recording a new session with the microphone, and a printable summary.
Specification: [`docs/specs/clinician-ui.md`](../docs/specs/clinician-ui.md).

Stack: Vite, React 19, TypeScript (strict), Tailwind CSS 4, Recharts, Lucide.

## Run

The API must be running (see the root README). The dev server proxies `/api` to it:

```bash
npm install
VITE_API_TARGET=http://127.0.0.1:8000 npm run dev   # http://localhost:5173
```

## Build

```bash
npm run build      # writes dist/, which FastAPI serves on the same origin as the API
npm run lint
npm run typecheck
```

## API types

`src/api/schema.d.ts` is generated from the backend's OpenAPI description, so the
types mirror the Python models field for field. After a backend change:

```bash
cd ../backend && uv run python -m scripts.export_openapi
cd ../frontend && npm run gen:api
```

## Layout

```text
src/
  api/          generated schema, type aliases, API calls
  components/   page sections, charts, shared UI pieces
  lib/          formatting, level styles, data loading, microphone recorder
  pages/        the five screens
```
