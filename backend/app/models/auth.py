"""
Dedicated request/response models for authentication endpoints
(kept separate from the general User models).
"""
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """
    Payload expected by POST /auth/login
    """
    email: EmailStr
    password: str = Field(..., min_length=8)

