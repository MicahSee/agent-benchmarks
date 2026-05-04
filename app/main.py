from fastapi import FastAPI
from app.routers import runs

app = FastAPI(title="Agent Benchmarks")

app.include_router(runs.router, prefix="/runs", tags=["runs"])


@app.get("/health")
def health():
    return {"status": "ok"}
