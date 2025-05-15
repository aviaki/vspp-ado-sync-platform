#!/usr/bin/env python3
"""backend.app.main v0.0.2"""
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import api_router
from .services.sync_daemon import run_sync_loop
app = FastAPI(title="VSPP ADO Sync Platform API", version="0.0.2")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router, prefix="/api")
@app.on_event("startup")
async def _startup(): asyncio.create_task(run_sync_loop())
@app.get("/health", tags=["system"])
async def health(): return {"status": "ok"}
