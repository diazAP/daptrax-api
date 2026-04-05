from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "daptrax-api"
    app_env: str = "development"
    app_debug: bool = True

    database_url: str
    database_url_migrations: str | None = None

    frontend_url: str = "http://localhost:5173"

    post_login_redirect_url: str = "http://127.0.0.1:8000/api/v1/auth/me"

    session_cookie_name: str = "daptrax_session"
    session_days: int = 7
    session_secret: str

    google_client_id: str | None = None
    google_client_secret: str | None = None
    google_redirect_uri: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()