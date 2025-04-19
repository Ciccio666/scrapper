from fastapi import APIRouter
from app.models.responses import ProxyListResponse

router = APIRouter()

@router.get("/api/proxies", response_model=ProxyListResponse)
def list_proxies():
    return ProxyListResponse(proxies=[{"host": "proxy.example.com", "port": 8080}])