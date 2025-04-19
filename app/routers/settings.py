from fastapi import APIRouter
from app.schemas.settings import ScraperSettings
from app.schemas.response_models import SettingsResponse

router = APIRouter()

@router.get("/api/settings/json", response_model=SettingsResponse, response_model=ScraperSettings)
async def get_settings():
    return ScraperSettings()

@router.post("/api/settings/json", response_model=SettingsResponse, response_model=ScraperSettings)
async def update_settings(settings: ScraperSettings):
    return settings
