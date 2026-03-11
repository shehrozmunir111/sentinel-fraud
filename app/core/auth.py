"""
SentinelFraud Auth Dependencies
Stage 4: JWT bearer auth, RBAC enforcement
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token, has_permission

bearer_scheme = HTTPBearer(auto_error=True)


# ---------------------------------------------------------------------------
# Token payload extraction
# ---------------------------------------------------------------------------
async def get_current_user_payload(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def get_current_user_id(payload: dict = Depends(get_current_user_payload)) -> str:
    return payload["sub"]


async def get_current_user_role(payload: dict = Depends(get_current_user_payload)) -> str:
    return payload.get("role", "viewer")


# ---------------------------------------------------------------------------
# RBAC dependency factory
# ---------------------------------------------------------------------------
def require_permission(permission: str):
    async def _check(role: str = Depends(get_current_user_role)):
        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required",
            )
    return Depends(_check)


def require_role(*roles: str):
    async def _check(role: str = Depends(get_current_user_role)):
        if role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' not authorized. Required: {list(roles)}",
            )
    return Depends(_check)
