import os
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import app.db as db_module

TEST_MONGO_URL = os.getenv(
    "TEST_MONGO_URL",
    "mongodb://mongoadmin:testpass@localhost:27017/test_company_website?authSource=admin",
)


@pytest.fixture(scope="session", autouse=True)
async def init_test_db():
    """Connect to a test MongoDB before the test session starts."""
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

    client = AsyncIOMotorClient(TEST_MONGO_URL, serverSelectionTimeoutMS=5000)
    db = client["test_company_website"]
    await init_beanie(
        database=db,
        document_models=[
            User, Activity,
            HeroSlide, Stat, Feature, WorkStep,
            Page, TeamMember, Certification,
            ServiceCategory, Service,
            Project,
            TrainingProgramme, TrainingIntake, TrainingStep,
            Client, Testimonial,
            Post, GalleryAlbum,
            FAQ, Office, Download, SiteSettings,
            ServiceRequest, TrainingApplication, ContactMessage,
        ],
    )
    db_module._client = client
    yield
    client.close()
