from pydantic import BaseModel
from typing import Any


class RunCreate(BaseModel):
    benchmark: str
    run_type: str = "benchmark"  # "benchmark" | "telemetry"
    title: str | None = None
    device: str | None = None
    apk_version: str | None = None
    results: dict[str, Any]


class Run(RunCreate):
    run_id: str
    timestamp: str
    user_id: str | None = None
    log_url: str | None = None
    deployment_name: str | None = None
