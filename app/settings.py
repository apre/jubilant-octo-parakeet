import logging
import os
from pathlib import PurePath
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict

app_name = "Stargazer"
environment = os.getenv("ENVIRONMENT", "dev")

# Project root directory configuration
PROJECT_ROOT = PurePath(os.path.dirname(os.path.abspath(__file__))).parent
STATIC_DIR = PROJECT_ROOT / "static"

class Settings(BaseSettings):
    app_name: str = app_name
    environment: str = environment
    admin_email: str = "admin@example.com"  # Default value added
    model_config = SettingsConfigDict(env_file=f"{environment}.env", env_file_encoding="utf-8")
    github_key: str = ""
    log_level: ClassVar[int] = logging.DEBUG

settings = Settings()
