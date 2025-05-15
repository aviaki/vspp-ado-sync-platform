from fastapi import APIRouter, Depends
from typing import List
from ..core.auth import RoleChecker
from ..services.database import get_db
router = APIRouter(prefix="/items", tags=["items"])
pm = RoleChecker(["TechM PM","MK PM","Admin","Presales","Viewer"])
@router.get("/mk/feature-requests", dependencies=[Depends(pm)])
async def list_fr() -> List[dict]:
    db=get_db()
    frs=await db.mk_feature_requests.find().to_list(100)
    for fr in frs: fr["id"]=str(fr.pop("_id",fr.get("mk_id")))
    return frs
