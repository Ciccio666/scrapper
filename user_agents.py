from fastapi import APIRouter
from app.response_models import UserAgentsResponse

router = APIRouter()

VALID_USER_AGENTS = [
    "chrome-windows", "firefox-linux", "safari-mac", "edge-windows"
]

@router.get("/api/user_agents", response_model=UserAgentsResponse)
def list_user_agents():
    return {"agents": VALID_USER_AGENTS}
