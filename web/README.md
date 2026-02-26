# project-fatima web

React/Vite/TS frontend for Project Fatima.

## Commands

```bash
# Install dependencies
bun install

# Start dev server (proxies /api/* to FastAPI at localhost:8000)
bun dev

# Build for production
bun run build

# Preview production build
bun run preview

# Run unit tests (vitest)
bun test

# Watch mode tests
bun run test:watch

# Type-check (no emit)
bun run lint
```

## Proxy

Dev server proxies `/api/*` → `http://localhost:8000/*` (strips `/api` prefix).
Make sure `uv run uvicorn app.main:app --reload` is running on port 8000.

## Tech stack

- Vite 5 + React 18 + TypeScript
- Tailwind CSS 3 (CSS variables theme)
- shadcn/ui components (see `src/components/ui/`)
- React Router 6 (routes: `/login`, `/games`, `/g/:gameId`)
- Vitest + Testing Library for unit tests
