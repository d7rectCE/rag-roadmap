from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    timeout_seconds: float = Field(3.0, gt=0, description="Таймаут чтения в секундах")
    max_retries: int = Field(3, ge=0, le=10, description="Максимальное число попыток")
    max_concurrent: int = Field(5, ge=1, le=100, description="Максимум одновременных запросов")
    rate_limit_per_second: float = Field(2.0, gt=0, description="Запросов в секунду")
    log_level: str = "INFO"