# response_models.py
from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int
