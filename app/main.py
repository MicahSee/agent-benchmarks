from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routers import runs, web
from app.auth import hash_password
from app.database import get_users_table


def _seed_admin():
    """Create the admin user in DynamoDB from env vars if they don't exist yet."""
    email = os.environ.get("ADMIN_EMAIL", "")
    password_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if not email or not password_hash:
        return
    table = get_users_table()
    if table.get_item(Key={"email": email}).get("Item"):
        return
    table.put_item(Item={
        "email": email,
        "password_hash": password_hash,
        "role": "admin",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_admin()
    yield


app = FastAPI(title="Agent Benchmarks", docs_url="/api/docs", lifespan=lifespan)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(web.router)
app.include_router(runs.router, prefix="/runs", tags=["runs"])


@app.get("/health")
def health():
    return {"status": "ok"}
