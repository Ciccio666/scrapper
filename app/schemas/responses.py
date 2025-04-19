from pydantic import BaseModel

class HealthResponse(BaseModel):
    status: str

class SettingsResponse(BaseModel):
    status: str
    settings: dict

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int
