from fastapi import APIRouter
from app.response_models import ProxyListResponse

router = APIRouter()

PROXIES = [
    {"host": "proxy1.com", "port": 8000, "country": "US"},
    {"host": "proxy2.com", "port": 8080, "country": "UK"},
]

@router.get("/api/proxies", response_model=ProxyListResponse)
def list_proxies():
    return {"proxies": PROXIES}

@router.post("/api/proxies")
def add_proxy(proxy: dict):
    PROXIES.append(proxy)
    return {"status": "added", "proxy": proxy}
