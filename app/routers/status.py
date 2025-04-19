# status.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.schemas.response_models import HealthResponse

router = APIRouter(prefix="/api", tags=["status"])

@router.get("/status", response_model=HealthResponse)
async def get_status():
    return JSONResponse(status_code=200, content={"status": "ok"})
