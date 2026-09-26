"""Central configuration. Every tunable (weights, thresholds, providers) lives here."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./omnicompare.db"

    # Hybrid matching weights — configurable, must sum to ~1.0
    match_weight_text: float = 0.40
    match_weight_attribute: float = 0.25
    match_weight_image: float = 0.35

    # Classification thresholds
    match_threshold_exact: float = 0.90
    match_threshold_similar: float = 0.70

    embedding_provider: str = "hashing"
    image_similarity_provider: str = "placeholder"
    openai_api_key: str = ""

    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
