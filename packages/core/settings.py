from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite+pysqlite:///:memory:"

    model_config = SettingsConfigDict(
        env_prefix="PITAGORAS_",
        extra="ignore",
    )
