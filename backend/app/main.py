from fastapi import FastAPI
import asyncio

from .routers import api_router          # all your sub-routers live here
from .services.sync_daemon import run_sync_loop

app = FastAPI(title="VSPP-ADO Sync Platform")

# ⚠️  no global “/api” prefix – nginx already took it away
app.include_router(api_router)

# background sync loop -------------------------------------------------
@app.on_event("startup")
async def _start_sync() -> None:         # fire-and-forget task
    asyncio.create_task(run_sync_loop())
