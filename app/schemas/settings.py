# settings.py
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from app.schemas.settings import ScraperSettings
from app.services.settings_service import load_settings, update_settings

router = APIRouter(prefix="/api", tags=["settings"])

@router.get("/settings/json", response_model=ScraperSettings)
async def get_settings_json():
    return load_settings()

@router.post("/settings/json", response_model=ScraperSettings)
async def update_settings_json(settings: ScraperSettings):
    return update_settings(settings)

@router.get("/settings_yaml", response_class=PlainTextResponse)
async def get_settings_yaml():
    settings = load_settings()
    return settings.model_dump_yaml()

@router.post("/settings_yaml")
async def update_settings_yaml(request: Request):
    body = await request.body()
    yaml_text = body.decode()
    settings = ScraperSettings.model_validate_yaml(yaml_text)
    return update_settings(settings)
