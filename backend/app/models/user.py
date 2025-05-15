from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., max_length=80)
    role: str = Field(..., regex="^(Admin|TechM PM|MK PM|Presales|Viewer)$")
class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
class UserOut(UserBase):
    id: str
    created_at: datetime
    active: bool = True
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
