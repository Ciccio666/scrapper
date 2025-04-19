from fastapi import APIRouter
from app.models.responses import UserAgentListResponse

router = APIRouter()

@router.get("/api/user_agents", response_model=UserAgentListResponse)
def list_user_agents():
    return UserAgentListResponse(agents=["chrome-windows", "firefox-linux", "safari-mac"])