from fastapi import FastAPI

app = FastAPI(title="Project Fatima", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
