from functools import lru_cache
from pydantic_settings import SettingsConfigDict
from pydantic_settings.main import BaseSettings


class DatabaseSettings(BaseSettings):
    db_url: str = "postgresql+asyncpg://root:root@localhost:5432/saga"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_db_settings() -> DatabaseSettings:
    return DatabaseSettings()