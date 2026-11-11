from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MongoDB
    mongo_host: str = "mongo"
    mongo_port: int = 27017
    mongo_root_username: str
    mongo_root_password: str
    mongo_db: str = "company_website"

    # JWT
    jwt_secret: str

    # First Super Admin
    admin_email: str
    admin_password: str

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    notify_email: str = ""

    # Site
    site_url: str = "http://localhost"
    # URL of the Next.js frontend (for revalidation calls; set FRONTEND_URL env var to override)
    frontend_url: str = "http://frontend:3000"
    revalidate_secret: str = ""

    # reCAPTCHA
    recaptcha_secret: str = ""

    # Uploads
    max_upload_mb: int = 5

    @property
    def mongo_url(self) -> str:
        return (
            f"mongodb://{self.mongo_root_username}:{self.mongo_root_password}"
            f"@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}"
            f"?authSource=admin"
        )


settings = Settings()
