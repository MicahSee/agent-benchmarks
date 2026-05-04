from fastapi import APIRouter, HTTPException
from boto3.dynamodb.conditions import Key
from app.models import Run, RunCreate
from app.database import get_table
import uuid
from datetime import datetime, timezone

router = APIRouter()


@router.post("/", response_model=Run, status_code=201)
def create_run(run: RunCreate):
    table = get_table()
    item = {
        "run_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **run.model_dump(),
    }
    table.put_item(Item=item)
    return item


@router.get("/", response_model=list[Run])
def list_runs(benchmark: str | None = None, limit: int = 50):
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
def get_run(run_id: str):
    table = get_table()
    resp = table.get_item(Key={"run_id": run_id})
    item = resp.get("Item")
    if not item:
        raise HTTPException(status_code=404, detail="Run not found")
    return item
