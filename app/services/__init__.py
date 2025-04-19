import json
from pathlib import Path

DEFAULT_SETTINGS_FILE = Path(__file__).resolve().parent.parent.parent / "settings.json"

class SettingsService:
    """Service for managing application settings."""

    def __init__(self, settings: Settings = Depends(get_settings_dependency)):
        """
        Initialize the settings service.

        Args:
            settings: Application settings instance
        """
        self.settings = settings

        # Load initial settings from settings.json if it exists
        if DEFAULT_SETTINGS_FILE.exists():
            try:
                with DEFAULT_SETTINGS_FILE.open("r") as f:
                    json_data = json.load(f)
                    self._update_global_settings(json_data)
                    logger.info("Loaded initial settings from settings.json")
            except Exception as e:
                logger.warning(f"Failed to load settings.json: {str(e)}")
