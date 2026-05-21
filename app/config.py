from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./tally.db"
    demo_api_key: str = "tally_sk_demo_4f9a2b7c1e8d6053"
    seed_on_startup: bool = True
    enable_disputes: bool = False

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        # Fly.io / Heroku-style Postgres URLs need an explicit driver.
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
