"""
database.py – Motor client helpers
"""

from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

from ..core.config import get_settings

settings = get_settings()


@lru_cache            # 1 global singleton – avoids reconnect churn
def get_client() -> AsyncIOMotorClient:
    """
    Return a cached Motor client.

    • settings.mongo_uri is a pydantic MongoDsn → cast to str.
    • uuidRepresentation="standard" keeps UUIDs driver-default.
    """
    return AsyncIOMotorClient(str(settings.mongo_uri), uuidRepresentation="standard")


def get_db():
    """Convenience accessor for the default database specified in the URI."""
    return get_client().get_default_database()

