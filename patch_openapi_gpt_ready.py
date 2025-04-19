"""
Patch script to finalize OpenAPI enhancements for GPT Custom Actions.
- Adds missing response models
- Ensures all endpoints have typed responses
- Annotates settings with descriptions
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

models_path = os.path.join(BASE_DIR, "app", "schemas")
settings_model_file = os.path.join(models_path, "settings.py")
scraping_model_file = os.path.join(models_path, "scraping.py")
router_file = os.path.join(BASE_DIR, "app", "routers", "settings.py")

# === SETTINGS MODEL ENHANCEMENT ===

SETTINGS_PATCH = """
from pydantic import BaseModel, Field

class ScraperSettings(BaseModel):
    page_load_timeout: int = Field(30, description="Max seconds to wait for a page to load.")
    dynamic_content_wait: float = Field(2.0, description="Delay before capturing dynamic content.")
    chatgpt_min_wait: float = Field(5.0, description="Min wait for ChatGPT pages.")
    chatgpt_max_wait: float = Field(8.0, description="Max wait for ChatGPT pages.")
    max_depth: int = Field(1, description="Depth of recursive crawling.")
    max_pages_per_domain: int = Field(10, description="Max pages to crawl per domain.")
    restrict_to_domains: list[str] = Field(default_factory=list, description="Allowed domains.")
    follow_external_links: bool = Field(False, description="Crawl links outside starting domain.")
    ignore_query_strings: bool = Field(True, description="Ignore query params for visited URLs.")
    exclude_url_patterns: list[str] = Field(default_factory=list, description="Patterns to skip.")
"""

with open(settings_model_file, "w") as f:
    f.write(SETTINGS_PATCH.strip())

print("[OK] ScraperSettings model updated with descriptions.")

# === SCREENSHOT RESPONSE MODEL ===

SCREENSHOT_MODEL = """
from pydantic import BaseModel

class ScreenshotResponse(BaseModel):
    status: str
    image_base64: str
    width: int
    height: int
"""

with open(scraping_model_file, "a") as f:
    f.write("\n\n" + SCREENSHOT_MODEL.strip())

print("[OK] ScreenshotResponse model added.")

# === HEALTH & SETTINGS RESPONSE MODELS ===

ROUTER_MODELS = """
class HealthResponse(BaseModel):
    status: str = "ok"

class SettingsResponse(ScraperSettings):
    pass
"""

with open(settings_model_file, "a") as f:
    f.write("\n\n" + ROUTER_MODELS.strip())

print("[OK] HealthResponse & SettingsResponse models added.")

# === SETTINGS ROUTER PATCH (light check for GPT-aware schema usage) ===

with open(router_file, "r") as f:
    contents = f.read()

if "response_model=SettingsResponse" not in contents:
    contents = contents.replace(
        "@router.get(\"/api/settings/json\"",
        "@router.get(\"/api/settings/json\", response_model=SettingsResponse"
    )
    contents = contents.replace(
        "@router.post(\"/api/settings/json\"",
        "@router.post(\"/api/settings/json\", response_model=SettingsResponse"
    )
    with open(router_file, "w") as f:
        f.write(contents)
    print("[OK] Settings router updated with typed responses.")

print("\nAll patches applied successfully.")
print("Restart your FastAPI app and visit /openapi.json to confirm the changes.")
