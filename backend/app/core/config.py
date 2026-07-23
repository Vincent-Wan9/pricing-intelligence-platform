from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    app_name: str = "Pricing Intelligence Platform"
    app_version: str = "1.0.0"
    environment: str = "development"
    database_url: str

    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 20
    redis_connect_timeout_seconds: float = 5.0
    redis_socket_timeout_seconds: float = 5.0
    redis_default_ttl_seconds: int = 3600

    jwt_algorithm: str
    jwt_secret_key: str
    jwt_default_exp_minutes: int = 30


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
