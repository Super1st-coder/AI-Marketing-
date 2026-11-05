"""LucaCredit service configuration (pydantic-settings, matches the Guide house style)."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "LucaCredit Billing Service"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    API_V1_PREFIX: str = "/api/v1"

    # ── database ──────────────────────────────────────────────────────────────
    # Full URL wins if set (tests use sqlite); otherwise assembled from parts like Guide.
    DATABASE_URL: Optional[str] = None
    DATABASE_HOST: Optional[str] = None
    DATABASE_PORT: Optional[int] = None
    DATABASE_USERNAME: Optional[str] = None
    DATABASE_PASSWORD: Optional[str] = None
    DATABASE_NAME_DEFAULT: Optional[str] = None

    @property
    def sqlalchemy_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if not all([self.DATABASE_USERNAME, self.DATABASE_PASSWORD, self.DATABASE_HOST,
                    self.DATABASE_PORT, self.DATABASE_NAME_DEFAULT]):
            raise ValueError("Database config incomplete: set DATABASE_URL or the DATABASE_* parts")
        return (f"postgresql+psycopg://{self.DATABASE_USERNAME}:{self.DATABASE_PASSWORD}"
                f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME_DEFAULT}")

    # ── internal service auth ─────────────────────────────────────────────────
    # Durval's video module calls with header X-Internal-Key: <LUCA_CREDITS_INTERNAL_KEY>
    # (a SEPARATE trust boundary from Guide's FURY key — agreed with Durval 2026-09-22).
    # ⚠️ OPEN with Luis: platform may standardize on X-Internal-API-Key; single constant to flip.
    LUCA_CREDITS_INTERNAL_KEY: Optional[str] = None

    # ── usage alerts (V1 spend protection) ──────────────────────────────────────
    # Email the org at 50/75/90% usage with a link to buy more (Marco 2026-09-23).
    # V1 destination = a static Stripe Payment Link (no Stripe integration); pending
    # Marco's final confirm (static link vs support route).
    LUCA_CREDITS_TOPUP_URL: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
