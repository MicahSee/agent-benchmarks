from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from app.routers import runs, web

app = FastAPI(title="Agent Benchmarks", docs_url="/api/docs")

app.include_router(web.router)
app.include_router(runs.router, prefix="/runs", tags=["runs"])


@app.get("/health")
def health():
    return {"status": "ok"}
