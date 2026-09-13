# ClaimTrace Frontend

React + TypeScript + Vite, no UI framework. See the repository root
`README.md` for the full project overview and how to run the backend
this depends on.

## Run locally

```bash
npm install
npm run dev
```

Requires the backend running at `http://127.0.0.1:8000` (see the root
README). The dev server proxies `/api/*` to it (`vite.config.ts`) so the
browser never needs CORS support from the backend — set
`VITE_API_PROXY_TARGET` to point at a different backend host if needed.

## Structure

- `src/api/` — the only place that talks to the backend (`client.ts`,
  typed against the backend's actual Pydantic schemas in `types.ts`)
- `src/components/ui/` — generic primitives (Badge, Button, Panel, states)
- `src/components/layout/` — the app shell: nav rail, breadcrumb, the
  reusable Inspector
- `src/components/evidence/` — citation/evidence display, shared by any
  screen that shows backend evidence
- `src/lib/` — frontend-only concerns: a temporary local project
  directory (the backend has no project-listing endpoint yet), example
  questions, and a session-local investigation cache (the backend doesn't
  persist investigations yet either) — each clearly documented in-file
- `src/pages/` — one file per route; `src/pages/workspace/` holds the
  Investigation Workspace's per-tab panels
- `src/styles/tokens.css` — centralized design tokens (color, type,
  spacing, radii) — change the visual system here, not in components

## Commands

- `npm run dev` — dev server with backend proxy
- `npm run build` — typecheck (`tsc -b`) + production build
- `npm run lint` — oxlint
