from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # Base Supabase project URL, e.g. http://127.0.0.1:54321 locally, or
    # https://<project-ref>.supabase.co in prod. Used to build the Auth
    # JWKS endpoint for JWT verification (see app/auth.py).
    SUPABASE_URL: str

    OVERPASS_API_URL: str = "https://overpass-api.de/api/interpreter"
    NOMINATIM_URL: str = "https://nominatim.openstreetmap.org"

    CACHE_REFRESH_DAYS: int = 30
    SCRAPE_TIMEOUT_SECONDS: int = 5
    SCRAPE_CONCURRENCY: int = 10
    MAX_SEARCH_RADIUS_M: int = 25000


settings = Settings()
