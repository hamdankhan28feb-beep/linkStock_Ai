from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config import settings
from app.supabase_client import users_table
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def _demo_user(user_id: str, role: Optional[str]) -> dict:
    if user_id == "demo-warehouse":
        return {
            "id": user_id,
            "name": "Warehouse Admin",
            "email": settings.DEMO_WAREHOUSE_EMAIL.lower(),
            "phone": "+92-21-35001234",
            "role": role or "warehouse",
            "is_active": True,
            "created_at": None,
        }
    if user_id == "demo-distributor":
        return {
            "id": user_id,
            "name": "Distributor",
            "email": settings.DEMO_DISTRIBUTOR_EMAIL.lower(),
            "phone": "+92-21-32561234",
            "role": role or "distributor",
            "is_active": True,
            "created_at": None,
        }
    if user_id == "demo-retailer":
        return {
            "id": user_id,
            "name": "Retailer",
            "email": settings.DEMO_RETAILER_EMAIL.lower(),
            "phone": "+92-333-1234501",
            "role": role or "retailer",
            "is_active": True,
            "created_at": None,
        }
    return {}


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    demo_user = _demo_user(user_id, payload.get("role"))
    if demo_user:
        return demo_user

    users = users_table.select("*", id=user_id)
    if not users:
        raise credentials_exception
    user = users[0]
    if not user.get("is_active", True):
        raise credentials_exception

    return user

def require_role(*roles: str):
    """Returns a dependency that restricts access to the given roles."""
    def _check(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {list(roles)}",
            )
        return current_user
    return _check

# Convenience role guards
require_retailer = require_role("retailer")
require_distributor = require_role("distributor")
require_warehouse = require_role("warehouse")
require_distributor_or_warehouse = require_role("distributor", "warehouse")
