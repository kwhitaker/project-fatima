from dotenv import load_dotenv

load_dotenv(override=True)

from fastapi import FastAPI

from app.routers.games import router as games_router

app = FastAPI(title="Project Fatima", version="0.1.0")
app.include_router(games_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
