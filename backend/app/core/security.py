from datetime import datetime, timedelta
from typing import Dict, Any
from jose import jwt
from passlib.context import CryptContext
from .config import get_settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"
_settings = get_settings()
def hash_password(p: str) -> str: return pwd_context.hash(p)
def verify_password(p: str, h: str) -> bool: return pwd_context.verify(p, h)
def create_token(sub: str, role: str, exp: int) -> str:
    return jwt.encode({"sub": sub, "role": role, "exp": datetime.utcnow() + timedelta(seconds=exp)},
                      _settings.jwt_secret, algorithm=ALGORITHM)
