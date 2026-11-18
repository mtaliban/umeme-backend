"""Mazingira ya app — yanasomwa kutoka .env."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    mongo_url: str = "mongodb://localhost:27017"
    db_name: str = "ummu_ayman"
    jwt_secret: str = "badilisha-iwe-ndefu-sana-na-siri"
    jwt_days: int = 90
    tz_name: str = "Africa/Dar_es_Salaam"
    firebase_credentials: str = "./firebase-service-account.json"
    low_stock_threshold: int = 2
    close_day_reminder: str = "21:00"
    weekly_report_time: str = "SUN 21:30"


settings = Settings()
