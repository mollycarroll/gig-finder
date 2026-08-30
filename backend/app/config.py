from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SUPABASE_JWT_SECRET: str

    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"

    CACHE_REFRESH_DAYS: int = 30
    SCRAPE_TIMEOUT_SECONDS: int = 5
    SCRAPE_CONCURRENCY: int = 10
    MAX_SEARCH_RADIUS_M: int = 25000


settings = Settings()
