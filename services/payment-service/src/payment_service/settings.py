from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic_settings.main import SettingsConfigDict

class PaymentSettings(BaseSettings):
    payment_fail_rate: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings() -> PaymentSettings:
    return PaymentSettings()