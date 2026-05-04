import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_table
from app.dependencies import require_api_key
from app.models import Run, RunCreate

router = APIRouter()


@router.post("/", response_model=Run, status_code=201)
def create_run(run: RunCreate, _: str = Depends(require_api_key)):
    table = get_table()
    data = run.model_dump()
    if not data.get("title"):
        parts = [data["benchmark"]]
        if data.get("apk_version"):
            parts.append(f"v{data['apk_version']}")
        if data.get("device"):
            parts.append(data["device"])
        parts.append(datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        data["title"] = " · ".join(parts)
    item = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    table.put_item(Item=item)
    return item


@router.get("/", response_model=list[Run])
def list_runs(benchmark: str | None = None, limit: int = 50, _: str = Depends(require_api_key)):
    table = get_table()
    if benchmark:
        resp = table.query(
            IndexName="benchmark-timestamp-index",
            KeyConditionExpression=Key("benchmark").eq(benchmark),
            ScanIndexForward=False,
            Limit=limit,
        )
    else:
        resp = table.scan(Limit=limit)
    return resp["Items"]


@router.get("/{run_id}", response_model=Run)
def get_run(run_id: str, _: str = Depends(require_api_key)):
    table = get_table()
    resp = table.get_item(Key={"run_id": run_id})
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Run not found")
    return item
