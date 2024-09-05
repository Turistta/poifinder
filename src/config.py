import os

from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=dotenv, env_file_encoding="utf-8", extra="allow")


settings = Settings()
