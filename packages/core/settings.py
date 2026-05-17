from urllib.parse import quote_plus

from pydantic import model_validator
from pydantic_settings import PydanticBaseSettingsSource
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str | None = None
    db_user: str | None = None
    db_password: str | None = None
    db_sslmode: str = "require"

    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle_seconds: int = 1800

    model_config = SettingsConfigDict(
        env_prefix="PITAGORAS_",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        init_values = init_settings()

        if init_values:
            env_settings = _DatabaseContractOverrideSource(env_settings, init_values)
            dotenv_settings = _DatabaseContractOverrideSource(dotenv_settings, init_values)

        return init_settings, env_settings, dotenv_settings, file_secret_settings

    @model_validator(mode="after")
    def validate_database_contract(self) -> "Settings":
        has_database_url = bool(self.database_url)
        postgres_values = {
            "db_host": self.db_host,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "db_password": self.db_password,
        }
        postgres_fields_present = [name for name, value in postgres_values.items() if value]
        has_any_postgres_field = bool(postgres_fields_present)
        has_full_postgres_tuple = len(postgres_fields_present) == len(postgres_values)

        if has_database_url and has_any_postgres_field:
            raise ValueError("Use either database_url or full PITAGORAS_DB_* contract, not both")

        if not has_database_url and not has_any_postgres_field:
            raise ValueError("Settings require either database_url or full PITAGORAS_DB_* contract")

        if has_any_postgres_field and not has_full_postgres_tuple:
            raise ValueError("Settings require full PITAGORAS_DB_* contract")

        return self

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url

        assert self.db_host is not None
        assert self.db_name is not None
        assert self.db_user is not None
        assert self.db_password is not None

        encoded_user = quote_plus(self.db_user)
        encoded_password = quote_plus(self.db_password)

        return (
            f"postgresql+psycopg://{encoded_user}:{encoded_password}@{self.db_host}:{self.db_port}/"
            f"{self.db_name}?sslmode={self.db_sslmode}"
        )


class _DatabaseContractOverrideSource:
    _POSTGRES_FIELDS = {"db_host", "db_port", "db_name", "db_user", "db_password", "db_sslmode"}

    def __init__(self, source: PydanticBaseSettingsSource, init_values: dict[str, object]) -> None:
        self._source = source
        self._init_values = init_values

    def __call__(self) -> dict[str, object]:
        values = self._source()

        if "database_url" in self._init_values:
            values = {key: value for key, value in values.items() if key not in self._POSTGRES_FIELDS}

        if self._POSTGRES_FIELDS.intersection(self._init_values):
            values.pop("database_url", None)

        return values
