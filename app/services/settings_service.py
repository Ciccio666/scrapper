"""
Settings management service for the application.

This module provides functions for getting and updating application settings,
with support for both YAML and JSON formats.
"""
import yaml
from typing import Dict, Any, Optional

from fastapi import Depends, HTTPException
from loguru import logger
from pydantic import ValidationError

from app.core.config import Settings, get_settings_dependency
from app.core.logging import with_log_context
from app.schemas.settings import ScraperSettings


class SettingsService:
    """Service for managing application settings."""
    
    def __init__(self, settings: Settings = Depends(get_settings_dependency)):
        """
        Initialize the settings service.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
    
    @with_log_context(service="settings_service")
    def get_settings(self) -> ScraperSettings:
        """
        Get current settings as a ScraperSettings model.
        
        Returns:
            ScraperSettings: Current application settings
        """
        return ScraperSettings(
            page_load_timeout=self.settings.PAGE_LOAD_TIMEOUT,
            dynamic_content_wait=self.settings.DYNAMIC_CONTENT_WAIT,
            chatgpt_min_wait=self.settings.CHATGPT_MIN_WAIT,
            chatgpt_max_wait=self.settings.CHATGPT_MAX_WAIT,
            max_depth=self.settings.MAX_DEPTH,
            max_pages_per_domain=self.settings.MAX_PAGES_PER_DOMAIN,
            restrict_to_domains=self.settings.RESTRICT_TO_DOMAINS,
            follow_external_links=self.settings.FOLLOW_EXTERNAL_LINKS,
            ignore_query_strings=self.settings.IGNORE_QUERY_STRINGS,
            exclude_url_patterns=self.settings.EXCLUDE_URL_PATTERNS,
        )
    
    @with_log_context(service="settings_service")
    def get_settings_yaml(self) -> str:
        """
        Get current settings as YAML string.
        
        Returns:
            str: YAML-formatted settings
        """
        settings_dict = self.get_settings().dict()
        return yaml.dump(settings_dict, default_flow_style=False)
    
    @with_log_context(service="settings_service")
    def update_settings_from_yaml(self, yaml_data: str) -> ScraperSettings:
        """
        Update settings from YAML string.
        
        Args:
            yaml_data: YAML-formatted settings
            
        Returns:
            ScraperSettings: Updated settings
            
        Raises:
            HTTPException: If YAML is invalid or validation fails
        """
        try:
            # Parse YAML
            settings_dict = yaml.safe_load(yaml_data)
            if not settings_dict:
                raise ValueError("Empty or invalid YAML")
                
            # Validate against schema
            self._validate_settings_dict(settings_dict)
            
            # Update global settings
            self._update_global_settings(settings_dict)
            
            # Return updated settings
            return self.get_settings()
            
        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid YAML format: {str(e)}")
            
        except ValidationError as e:
            logger.error(f"Settings validation error: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Settings validation error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")
    
    @with_log_context(service="settings_service")
    def update_settings_from_json(self, settings: ScraperSettings) -> ScraperSettings:
        """
        Update settings from ScraperSettings model.
        
        Args:
            settings: New settings
            
        Returns:
            ScraperSettings: Updated settings
        """
        # Update global settings
        self._update_global_settings(settings.dict())
        
        # Return updated settings
        return self.get_settings()
    
    def _validate_settings_dict(self, settings_dict: Dict[str, Any]) -> None:
        """
        Validate settings dictionary against schema.
        
        Args:
            settings_dict: Dictionary of settings to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Create model to validate
        try:
            ScraperSettings(**settings_dict)
        except ValidationError as e:
            raise ValidationError(e.errors(), ScraperSettings)
    
    def _update_global_settings(self, settings_dict: Dict[str, Any]) -> None:
        """
        Update global settings from dictionary.
        
        Args:
            settings_dict: Dictionary of settings to update
        """
        if "page_load_timeout" in settings_dict:
            self.settings.PAGE_LOAD_TIMEOUT = settings_dict["page_load_timeout"]
            
        if "dynamic_content_wait" in settings_dict:
            self.settings.DYNAMIC_CONTENT_WAIT = settings_dict["dynamic_content_wait"]
            
        if "chatgpt_min_wait" in settings_dict:
            self.settings.CHATGPT_MIN_WAIT = settings_dict["chatgpt_min_wait"]
            
        if "chatgpt_max_wait" in settings_dict:
            self.settings.CHATGPT_MAX_WAIT = settings_dict["chatgpt_max_wait"]
            
        if "max_depth" in settings_dict:
            self.settings.MAX_DEPTH = settings_dict["max_depth"]
            
        if "max_pages_per_domain" in settings_dict:
            self.settings.MAX_PAGES_PER_DOMAIN = settings_dict["max_pages_per_domain"]
            
        if "restrict_to_domains" in settings_dict:
            self.settings.RESTRICT_TO_DOMAINS = settings_dict["restrict_to_domains"]
            
        if "follow_external_links" in settings_dict:
            self.settings.FOLLOW_EXTERNAL_LINKS = settings_dict["follow_external_links"]
            
        if "ignore_query_strings" in settings_dict:
            self.settings.IGNORE_QUERY_STRINGS = settings_dict["ignore_query_strings"]
            
        if "exclude_url_patterns" in settings_dict:
            self.settings.EXCLUDE_URL_PATTERNS = settings_dict["exclude_url_patterns"]
            
        logger.info("Settings updated successfully")