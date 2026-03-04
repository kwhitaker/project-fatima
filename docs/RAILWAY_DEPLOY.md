# Railway Deploy (Single Service)

This repo can deploy to Railway as a single service using the root `Dockerfile`.

What you get:

- FastAPI API
  - available at `/api/*` (same as local Vite dev proxy)
- React SPA
  - served from `web/dist` by FastAPI

## 1) Create the Railway service

- New Project -> Deploy from GitHub repo
- Railway should detect the root `Dockerfile` automatically.

## 2) Set environment variables

Backend (server-only):

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

Frontend runtime config (safe to expose to the browser):

- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY`

Notes:

- The frontend reads these at runtime from `/env.js`.
- The backend uses `SUPABASE_URL` to validate Supabase JWTs via the JWKS endpoint.

## 3) Health check

- Path: `/health`

## 4) Verify after deploy

- Open the Railway service URL
- Confirm the SPA loads
- Confirm API responds:
  - `GET /health`
  - `GET /api/games` (requires auth)

## Local Docker smoke

```bash
docker build -t project-fatima:local .
docker run --rm -p 8000:8000 \
  -e SUPABASE_URL=... \
  -e SUPABASE_SERVICE_ROLE_KEY=... \
  -e VITE_SUPABASE_URL=... \
  -e VITE_SUPABASE_ANON_KEY=... \
  project-fatima:local
```
