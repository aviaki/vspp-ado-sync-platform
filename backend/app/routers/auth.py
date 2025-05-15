from fastapi import APIRouter, HTTPException, status
from datetime import datetime
from jose import jwt
from ..core.config import get_settings
from ..core.security import hash_password, verify_password, create_token
from ..models.user import UserCreate, Token
from ..services.database import get_db
router = APIRouter(prefix="/auth", tags=["auth"])
s = get_settings(); _refresh=set()
@router.post("/register", response_model=dict)
async def register(u: UserCreate):
    db = get_db()
    if await db.users.find_one({"email": u.email}): raise HTTPException(400, "Email exists")
    await db.users.insert_one({"_id": u.email, "email": u.email, "name": u.name,
                               "role": u.role, "password_hash": hash_password(u.password),
                               "created_at": datetime.utcnow(), "active": True})
    return {"msg": "created"}
@router.post("/login", response_model=Token)
async def login(u: UserCreate):
    db = get_db()
    user = await db.users.find_one({"email": u.email, "active": True})
    if not user or not verify_password(u.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    access=create_token(user["_id"], user["role"], s.jwt_access_expires)
    refresh=create_token(user["_id"], user["role"], s.jwt_refresh_expires); _refresh.add(refresh)
    return Token(access_token=access, refresh_token=refresh, expires_in=s.jwt_access_expires)
@router.post("/refresh", response_model=Token)
async def refresh(t: str):
    if t not in _refresh: raise HTTPException(401, "Invalid refresh")
    data = jwt.decode(t, s.jwt_secret, algorithms=["HS256"])
    access=create_token(data["sub"], data["role"], s.jwt_access_expires)
    refresh=create_token(data["sub"], data["role"], s.jwt_refresh_expires)
    _refresh.remove(t); _refresh.add(refresh)
    return Token(access_token=access, refresh_token=refresh, expires_in=s.jwt_access_expires)
