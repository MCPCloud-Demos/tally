from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

_bearer = HTTPBearer(auto_error=True)


def require_api_key(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> str:
    settings = get_settings()
    if credentials.credentials != settings.demo_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # The key maps to an isolated demo tenant; all rows are scoped to it.
    return "demo"
