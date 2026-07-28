"""
Auth router — rewritten to use Supabase REST API.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from typing import List
from app.supabase_client import users_table, locations_table
from app.services.auth_service import hash_password, create_access_token, verify_password
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _user_out(u: dict) -> dict:
    return {
        "id": u.get("id"),
        "name": u.get("name"),
        "email": u.get("email"),
        "phone": u.get("phone"),
        "role": u.get("role"),
        "is_active": u.get("is_active", True),
        "created_at": u.get("created_at"),
    }


def _authenticate_user(email: str, password: str):
    users = users_table.select("*", email=email)
    if not users:
        return None
    user = users[0]
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user.get("password_hash", "")):
        return None
    return user


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(payload: dict):
    existing = users_table.select("id", email=payload.get("email"))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_data = {
        "name": payload.get("name"),
        "email": payload.get("email"),
        "phone": payload.get("phone"),
        "password_hash": hash_password(payload.get("password")),
        "role": payload.get("role", "retailer"),
    }
    user = users_table.insert(user_data)

    if payload.get("location"):
        loc = payload["location"]
        locations_table.insert({
            "user_id": user["id"],
            "address": loc.get("address"),
            "area": loc.get("area"),
            "city": loc.get("city", "Karachi"),
            "latitude": loc.get("latitude"),
            "longitude": loc.get("longitude"),
        })

    return _user_out(user)


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """OAuth2 form-based login (for /docs Authorize button)."""
    user = _authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(user["id"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": _user_out(user)}


@router.post("/login/json")
def login_json(payload: dict):
    """JSON body login (used by frontend Axios)."""
    user = _authenticate_user(payload.get("email", ""), payload.get("password", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(user["id"], user["role"])
    return {"access_token": token, "token_type": "bearer", "user": _user_out(user)}


@router.get("/me")
def get_me(current_user=Depends(get_current_user)):
    if isinstance(current_user, dict):
        return _user_out(current_user)
    return current_user


@router.get("/users/all")
def get_all_users(current_user=Depends(get_current_user)):
    role = current_user.get("role") if isinstance(current_user, dict) else str(current_user.role)
    if role != "warehouse":
        raise HTTPException(status_code=403, detail="Only Warehouse Admin can view all users")
    users = users_table.select("*")
    return [_user_out(u) for u in users]
