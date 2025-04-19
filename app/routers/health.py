from fastapi import APIRouter
from app.schemas.response_models import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return {"status": "ok"}
