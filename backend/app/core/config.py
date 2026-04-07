import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "WowRussian Analyzer"
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=10080, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    admin_secret_key: str = Field(default="", env="ADMIN_SECRET_KEY")

    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", env="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", env="CELERY_RESULT_BACKEND")

    storage_path: str = Field(default="/app/storage", env="STORAGE_PATH")
    upload_max_size: int = Field(default=10485760, env="UPLOAD_MAX_SIZE")  # 10MB

    allowed_origins: List[str] = Field(default=["http://localhost:3000"], env="ALLOWED_ORIGINS")

    crawler_user_agent: str = Field(default="WowRussianBot/1.0", env="CRAWLER_USER_AGENT")
    crawler_delay: int = Field(default=1, env="CRAWLER_DELAY")
    crawler_timeout: int = Field(default=30, env="CRAWLER_TIMEOUT")
    crawler_max_pages: int = Field(default=1000, env="CRAWLER_MAX_PAGES")

    # Dictionary settings for foreign word analysis (law №168-FZ compliance)
    dictionary_path: str = Field(default="/app/dictionaries/russian_words.txt", env="DICTIONARY_PATH")
    dictionary_url: str = Field(default="https://raw.githubusercontent.com/danakt/russian-words/master/russian.txt", env="DICTIONARY_URL")
    auto_download_dictionary: bool = Field(default=True, env="AUTO_DOWNLOAD_DICTIONARY")

    # 168fz integration settings
    use_fz168: bool = Field(default=True, env="USE_FZ168")
    fz168_url: str = Field(default="http://localhost:8169", env="FZ168_URL")
    fz168_timeout: int = Field(default=60, env="FZ168_TIMEOUT")  # Increased from 10 to 60 seconds
    fz168_retry_attempts: int = Field(default=3, env="FZ168_RETRY_ATTEMPTS")

    # Operator info (for 152-FZ compliance)
    operator_name: str = Field(default="", env="OPERATOR_NAME")
    operator_inn: str = Field(default="", env="OPERATOR_INN")
    operator_ogrn: str = Field(default="", env="OPERATOR_OGRN")
    operator_address: str = Field(default="", env="OPERATOR_ADDRESS")
    operator_email: str = Field(default="", env="OPERATOR_EMAIL")

    # Tab order for home page (comma-separated list: text,url,site,file)
    # Default order: site,text,url,file
    tab_order: str = Field(default="site,text,url,file", env="TAB_ORDER")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()