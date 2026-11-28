"""Mazingira ya app — yanasomwa kutoka .env au compose."""

from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MONGO_URL ikiwekwa inatumika moja kwa moja; vinginevyo URL inajengwa
    # kutoka MONGO_HOST / MONGO_PORT / MONGO_ROOT_USERNAME / MONGO_ROOT_PASSWORD
    # (kama docker-compose ya production inavyoweka).
    mongo_url: str = ""
    mongo_host: str = "localhost"
    mongo_port: int = 27017
    mongo_root_username: str = ""
    mongo_root_password: str = ""

    db_name: str = "ummu_ayman"
    jwt_secret: str = "badilisha-iwe-ndefu-sana-na-siri"
    jwt_days: int = 90
    tz_name: str = "Africa/Dar_es_Salaam"
    firebase_credentials: str = "./firebase-service-account.json"
    low_stock_threshold: int = 2
    close_day_reminder: str = "21:00"
    weekly_report_time: str = "SUN 21:30"
    shop_pin: str = "1234"

    # Jina la muuzaji linaloonekana kwenye risiti (GET /me na risiti).
    signature_name: str = "Ummu Ayman"

    # ── Picha ya daftari (POST /daily/{date}/scan) ───────────────────────────
    # AI_PROVIDER ndiye anayeanza; AI_FALLBACK ni orodha iliyotenganishwa kwa
    # koma (mfano "groq,claude"). Kubadilisha AI = kubadilisha .env + restart.
    ai_provider: str = "gemini"
    ai_fallback: str = "groq,claude"
    ai_timeout: float = 45.0
    scan_max_mb: float = 6.0

    gemini_api_key: str = ""
    # Modal za Gemini zilibadilika: 2.0/2.5 zimezimwa; 3.5-flash-lite ni ya bure
    # na ya bei ndogo kwa kusoma nyaraka. Badilisha hapa .env ikihitajika.
    gemini_model: str = "gemini-3.5-flash-lite"
    groq_api_key: str = ""
    # Llama 4 Scout ilizimwa Groq (17 Julai 2026); qwen3.8-27b ndiyo vision ya sasa.
    groq_model: str = "qwen/qwen3.8-27b"
    claude_api_key: str = ""
    claude_model: str = "claude-haiku-5-5"

    @property
    def database_url(self) -> str:
        if self.mongo_url.strip():
            return self.mongo_url.strip()
        if self.mongo_root_username:
            user = quote_plus(self.mongo_root_username)
            password = quote_plus(self.mongo_root_password)
            return (
                f"mongodb://{user}:{password}@"
                f"{self.mongo_host}:{self.mongo_port}/?authSource=admin"
            )
        return f"mongodb://{self.mongo_host}:{self.mongo_port}"


settings = Settings()
