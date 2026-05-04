import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone

from boto3.dynamodb.conditions import Key
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import create_session_token, verify_password
from app.database import get_api_keys_table, get_table
from app.dependencies import get_session_user
from decimal import Decimal


def _clean(obj):
    """Recursively convert Decimal to int/float for template rendering."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    if isinstance(obj, Decimal):
        return int(obj) if obj == obj.to_integral_value() else float(obj)
    return obj

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return RedirectResponse("/dashboard" if get_session_user(request) else "/login")


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if get_session_user(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
async def login(request: Request, email: str = Form(...), password: str = Form(...)):
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    admin_hash = os.environ.get("ADMIN_PASSWORD_HASH", "")
    if email != admin_email or not verify_password(password, admin_hash):
        return templates.TemplateResponse(request, "login.html", {"error": "Invalid email or password"}, status_code=401)
    token = create_session_token(email)
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 7)
    return resp


@router.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    return resp


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, benchmark: str | None = None):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    table = get_table()
    if benchmark:
        result = table.query(
            IndexName="benchmark-timestamp-index",
            KeyConditionExpression=Key("benchmark").eq(benchmark),
            ScanIndexForward=False,
            Limit=50,
        )
    else:
        result = table.scan(Limit=50)
    runs = [_clean(item) for item in sorted(result["Items"], key=lambda r: r["timestamp"], reverse=True)]
    return templates.TemplateResponse(request, "dashboard.html", {
        "user": user, "runs": runs, "benchmark": benchmark, "active": "dashboard",
    })


@router.get("/dashboard/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    resp = get_table().get_item(Key={"run_id": run_id})
    item = resp.get("Item")
    if not item:
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse(request, "run_detail.html", {
        "user": user, "run": _clean(item), "active": "dashboard",
    })


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request, new_key: str | None = None):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    result = get_api_keys_table().query(
        IndexName="user-index",
        KeyConditionExpression=Key("user_id").eq(user),
    )
    keys = sorted(result["Items"], key=lambda k: k["created_at"], reverse=True)
    return templates.TemplateResponse(request, "settings.html", {
        "user": user, "api_keys": keys, "new_key": new_key, "active": "settings",
    })


@router.post("/settings/api-keys")
async def create_api_key(request: Request, name: str = Form(...)):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    raw_key = "ab_" + secrets.token_hex(24)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    get_api_keys_table().put_item(Item={
        "key_hash": key_hash,
        "key_id": str(uuid.uuid4()),
        "user_id": user,
        "name": name,
        "key_prefix": raw_key[:10],
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return RedirectResponse(f"/settings?new_key={raw_key}", status_code=303)


@router.post("/settings/api-keys/{key_id}/revoke")
async def revoke_api_key(request: Request, key_id: str):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login")
    table = get_api_keys_table()
    result = table.query(
        IndexName="user-index",
        KeyConditionExpression=Key("user_id").eq(user),
    )
    for item in result["Items"]:
        if item["key_id"] == key_id:
            table.delete_item(Key={"key_hash": item["key_hash"]})
            break
    return RedirectResponse("/settings", status_code=303)
