import os

from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from dev.env
# load_dotenv('dev.env')

# Application settings
app_name = "Stargazer"
environment = os.getenv("ENVIRONMENT", "dev")


class Settings(BaseSettings):
    app_name: str = app_name
    environment: str = environment
    admin_email: str = "admin@example.com"  # Default value added
    model_config = SettingsConfigDict(env_file=f"{environment}.env", env_file_encoding="utf-8")
    github_account: str = "stargazer"
    github_key: str = ""


settings = Settings()
