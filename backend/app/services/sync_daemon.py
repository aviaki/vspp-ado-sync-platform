import asyncio, logging
from datetime import datetime
from ..core.config import get_settings
from .ado_client import fetch_mk_feature_requests
from .database import get_db
settings = get_settings()
log = logging.getLogger("sync_daemon")
async def sync_once():
    frs = await fetch_mk_feature_requests(["New", "Active", "Under Consideration"])
    if not frs:
        log.info("No FRs")
        return
    db = get_db()
    for fr in frs:
        mk_id = fr["id"]
        await db.mk_feature_requests.update_one({"mk_id": mk_id},
            {"$set": {"mk_id": mk_id, "title": fr['fields']['System.Title'],
                      "state": fr['fields']['System.State'], "last_updated": datetime.utcnow()}},
            upsert=True)
    log.info("Synced %d FRs", len(frs))
async def run_sync_loop():
    interval = int(getattr(settings, "sync_poll_interval", 300))
    while True:
        try: await sync_once()
        except Exception as e:
            log.error("sync error %s", e, exc_info=True)
        await asyncio.sleep(interval)
