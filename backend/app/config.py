from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://cashflow:cashflow@localhost:5432/cashflow"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]
    APP_VERSION: str = "0.1.0"


settings = Settings()
