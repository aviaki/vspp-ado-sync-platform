from motor.motor_asyncio import AsyncIOMotorClient
from functools import lru_cache
from ..core.config import get_settings
settings = get_settings()
@lru_cache
def get_client(): return AsyncIOMotorClient(settings.mongo_uri, uuidRepresentation="standard")
def get_db(): return get_client().get_default_database()
