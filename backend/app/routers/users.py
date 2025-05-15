from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from ..core.auth import RoleChecker
from ..core.security import hash_password
from ..models.user import UserCreate, UserOut
from ..services.database import get_db
admin = RoleChecker(["Admin"])
router = APIRouter(prefix="/users", tags=["users"])
@router.get("/", response_model=list[UserOut], dependencies=[Depends(admin)])
async def users():
    db=get_db(); return [{**u,"id":u["_id"]} async for u in db.users.find()]
@router.post("/", response_model=dict, dependencies=[Depends(admin)])
async def create(u: UserCreate):
    db=get_db()
    if await db.users.find_one({"email":u.email}): raise HTTPException(400,"Email exists")
    await db.users.insert_one({"_id":u.email,"email":u.email,"name":u.name,"role":u.role,
                               "password_hash":hash_password(u.password),"created_at":datetime.utcnow(),"active":True})
    return {"msg":"created"}
