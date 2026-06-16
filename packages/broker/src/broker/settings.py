
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class BrokerSettings(BaseSettings):
    redis_url: str = 'redis://:root@localhost:6379'
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> BrokerSettings:
    return BrokerSettings()
