from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI  # noqa: E402

from app.routers.cards import router as cards_router  # noqa: E402
from app.routers.games import router as games_router  # noqa: E402

app = FastAPI(title="Project Fatima", version="0.1.0")
app.include_router(games_router)
app.include_router(cards_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
