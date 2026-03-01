from dotenv import load_dotenv

load_dotenv(override=True)

from pathlib import Path  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402

from app.routers.cards import router as cards_router  # noqa: E402
from app.routers.games import router as games_router  # noqa: E402

app = FastAPI(title="Project Fatima", version="0.1.0")
app.include_router(games_router)
app.include_router(cards_router)

# Frontend expects API under /api/* in production.
# Keep the non-/api routes for tests and direct usage.
app.include_router(games_router, prefix="/api")
app.include_router(cards_router, prefix="/api")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/env.js", include_in_schema=False)
def env_js() -> Response:
    """Expose a small, safe runtime config to the browser.

    This avoids needing to bake Vite env vars at build time for deploys.
    """
    import json
    import os

    payload: dict[str, str] = {}
    for k in ("VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY"):
        v = os.environ.get(k)
        if v:
            payload[k] = v
    body = f"window.__FATIMA_ENV__ = {json.dumps(payload)};"
    return Response(content=body, media_type="application/javascript")


# Serve the built web SPA (web/dist) when present.
_dist_dir = Path(__file__).resolve().parent.parent / "web" / "dist"
_index_html = _dist_dir / "index.html"


if _dist_dir.exists() and _index_html.exists():

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        # Let API/docs routes resolve first (they are registered before this).
        requested = (_dist_dir / path).resolve()
        if not str(requested).startswith(str(_dist_dir.resolve())):
            return FileResponse(_index_html)
        if path and requested.is_file():
            return FileResponse(requested)
        return FileResponse(_index_html)
