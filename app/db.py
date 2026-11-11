import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None


async def init_db() -> None:
    global _client
    if _client is not None:
        return  # already initialised (e.g. by test fixture)
    _client = AsyncIOMotorClient(
        settings.mongo_url,
        serverSelectionTimeoutMS=5000,
    )

    # Import all document models
    from app.models.user import User
    from app.models.activity import Activity
    from app.models.content import HeroSlide, Stat, Feature, WorkStep
    from app.models.pages import Page
    from app.models.team import TeamMember, Certification
    from app.models.services import ServiceCategory, Service
    from app.models.projects import Project
    from app.models.training import TrainingProgramme, TrainingIntake, TrainingStep
    from app.models.clients import Client, Testimonial
    from app.models.posts import Post
    from app.models.gallery import GalleryAlbum
    from app.models.misc import FAQ, Office, Download, SiteSettings
    from app.models.inbox import ServiceRequest, TrainingApplication, ContactMessage

    await init_beanie(
        database=_client[settings.mongo_db],
        document_models=[
            User,
            Activity,
            HeroSlide,
            Stat,
            Feature,
            WorkStep,
            Page,
            TeamMember,
            Certification,
            ServiceCategory,
            Service,
            Project,
            TrainingProgramme,
            TrainingIntake,
            TrainingStep,
            Client,
            Testimonial,
            Post,
            GalleryAlbum,
            FAQ,
            Office,
            Download,
            SiteSettings,
            ServiceRequest,
            TrainingApplication,
            ContactMessage,
        ],
    )
    logger.info("Database initialised: %s", settings.mongo_db)


async def get_db_status() -> bool:
    if _client is None:
        return False
    try:
        await _client.admin.command("ping")
        return True
    except Exception:
        return False
