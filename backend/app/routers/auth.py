# backend/app/routers/auth.py
#
# Central authentication routes:
#   • POST /auth/register – JSON body → create user
#   • POST /auth/login    – x-www-form-urlencoded body (OAuth2 pwd-grant) → JWT pair
#
# The module relies on small helper-functions that live in
# backend/app/services/users.py – keep that service thin so we can
# swap the persistence layer (Motor → SQLModel, etc.) without ever
# touching the API surface.

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..core.config import get_settings
from ..models.user import UserCreate, UserOut, Token
from ..services.users import (
    create_user,           # async def create_user(data: UserCreate) -> UserOut
    authenticate_user,     # async def authenticate_user(username, password) -> UserOut | None
    create_access_token,   # def  create_access_token(claims: dict, expires: int) -> str
    create_refresh_token,  # def  create_refresh_token(claims: dict, expires: int) -> str
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


# ───────────────────────────── register ──────────────────────────────
@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (admin-only in production)",
)
async def register(payload: UserCreate) -> UserOut:
    """
    Accepts the **JSON** body described by `UserCreate`
    and returns the persisted record.

    In production you’d normally *protect* this endpoint so only an Admin
    (or an out-of-band invite token) can hit it – left open for PoC.
    """
    try:
        return await create_user(payload)
    except ValueError as exc:  # e.g. duplicate e-mail
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ────────────────────────────── login ────────────────────────────────
@router.post(
    "/login",
    response_model=Token,
    summary="OAuth2 password-grant login (x-www-form-urlencoded)",
)
async def login(form: OAuth2PasswordRequestForm = Depends()) -> Token:
    """
    Standard **password grant** flow.

    Expects `application/x-www-form-urlencoded` with
    `username` and `password` fields (what <form> or JS `fetch` send).

    Returns both access- and refresh-tokens so the SPA can keep the
    session alive without re-authenticating.
    """
    user = await authenticate_user(form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(
        {"sub": str(user.id)},
        expires=settings.jwt_access_expires,
    )
    refresh_token = create_refresh_token(
        {"sub": str(user.id)},
        expires=settings.jwt_refresh_expires,
    )

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.jwt_access_expires,
    )

