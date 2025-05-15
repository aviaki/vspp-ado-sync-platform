from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, MongoDsn
class Settings(BaseSettings):
    mongo_uri: MongoDsn = "mongodb://mongo:27017/vspp"
    jwt_secret: str = Field(..., min_length=32)
    jwt_access_expires: int = 900
    jwt_refresh_expires: int = 604800
    mk_ado_org: str
    mk_ado_project: str
    mk_ado_pat: str
    tm_ado_org: str
    tm_ado_project: str
    tm_ado_pat: str
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_pass: str
    smtp_from: str = "noreply@vspp.com"
    class Config: env_file = ".env"
@lru_cache
def get_settings() -> Settings: return Settings()
