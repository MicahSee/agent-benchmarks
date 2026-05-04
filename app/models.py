from pydantic import BaseModel
from typing import Any


class RunCreate(BaseModel):
    benchmark: str
    device: str | None = None
    apk_version: str | None = None
    results: dict[str, Any]


class Run(RunCreate):
    run_id: str
    timestamp: str
