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
    redis_product_ttl_seconds: int = 900
    redis_competitor_price_ttl_seconds: int = 300

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/1"
    competitor_crawl_schedule_seconds: int = 21600
    demand_forecast_schedule_seconds: int = 86400
    demand_forecast_default_horizon_days: int = 7
    demand_forecast_min_history_days: int = 21
    celery_task_always_eager: bool = False

    crawler_timeout_seconds: float = 10.0
    crawler_max_retries: int = 2
    crawler_retry_backoff_seconds: float = 0.25
    crawler_request_delay_seconds: float = 0.1
    crawler_user_agent: str = "PricingIntelligenceBot/1.0 (+public product price monitoring)"

    jwt_algorithm: str
    jwt_secret_key: str
    jwt_default_exp_minutes: int = 30
    cors_origins: str = "http://localhost:5173"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

settings = Settings()
