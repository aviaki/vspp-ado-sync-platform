from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import List
from ..services.database import get_db
from .config import get_settings
from .security import ALGORITHM
settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
async def get_current_user(token: str = Depends(oauth2_scheme)):
    db = get_db()
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials",
                        headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise exc
    except JWTError:
        raise exc
    user = await db.users.find_one({"_id": user_id, "active": True})
    if not user:
        raise exc
    return user
class RoleChecker:
    def __init__(self, roles: List[str]): self.roles = roles
    async def __call__(self, user=Depends(get_current_user)):
        if user["role"] not in self.roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
