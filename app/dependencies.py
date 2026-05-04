from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from fastapi.responses import RedirectResponse
from app.auth import decode_session_token
from app.database import get_api_keys_table
import hashlib

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_session_user(request: Request) -> str | None:
    token = request.cookies.get("session")
    if not token:
        return None
    return decode_session_token(token)


def require_session(request: Request) -> str:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


async def require_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(status_code=401, detail="X-API-Key header required")
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    table = get_api_keys_table()
    resp = table.get_item(Key={"key_hash": key_hash})
    if not resp.get("Item"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return resp["Item"]["user_id"]
