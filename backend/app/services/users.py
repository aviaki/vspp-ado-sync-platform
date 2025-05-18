"""
User-centric helpers:
• create_user          – register a new user
• authenticate_user    – validate credentials
• create_tokens        – issue JWT access/refresh tokens
"""

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from ..core.config import get_settings
from ..models.user import UserCreate, UserOut
from ..models.auth import LoginRequest  # just for type hints
from ..models.user import Token
from .database import get_db

settings = get_settings()

# ────────────────────────── password hashing ───────────────────────────
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash(pw: str) -> str:
    return pwd_ctx.hash(pw)


def _verify(pw: str, hashed: str) -> bool:
    return pwd_ctx.verify(pw, hashed)


# ────────────────────────── JWT helpers ────────────────────────────────
def _jwt_encode(claims: dict, expires: int) -> str:
    payload = {
        **claims,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=expires),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def create_tokens(user: UserOut) -> Token:
    """
    Produce both access- and refresh-tokens for a given user doc.
    """
    base_claims = {"sub": user.id, "email": user.email, "role": user.role}
    return Token(
        access_token=_jwt_encode(base_claims, settings.jwt_access_expires),
        refresh_token=_jwt_encode(base_claims, settings.jwt_refresh_expires),
        expires_in=settings.jwt_access_expires,
    )


# ────────────────────────── CRUD helpers ───────────────────────────────
async def _find_user_by_email(email: str):
    db = get_db()
    return await db.users.find_one({"email": email})


async def create_user(payload: UserCreate) -> UserOut:
    """
    Inserts a new user document (throws 409 if e-mail already exists).
    """
    db = get_db()

    if await _find_user_by_email(payload.email):
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail already registered",
        )

    doc = {
        "email": payload.email,
        "name": payload.name,
        "role": payload.role,
        "hashed_pw": _hash(payload.password),
        "created_at": datetime.now(timezone.utc),
        "active": True,
    }
    res = await db.users.insert_one(doc)
    return UserOut(
        id=str(res.inserted_id),
        email=doc["email"],
        name=doc["name"],
        role=doc["role"],
        created_at=doc["created_at"],
        active=doc["active"],
    )


async def authenticate_user(email: str, password: str) -> UserOut | None:
    """
    Returns the user doc if credentials are valid, else None.
    """
    doc = await _find_user_by_email(email)
    if not doc or not _verify(password, doc["hashed_pw"]):
        return None

    return UserOut(
        id=str(doc["_id"]),
        email=doc["email"],
        name=doc["name"],
        role=doc["role"],
        created_at=doc["created_at"],
        active=doc["active"],
    )

