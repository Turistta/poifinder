import os

from pydantic_settings import BaseSettings, SettingsConfigDict

dotenv = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    AIRFLOW_API_ENDPOINT: str = os.environ.get('AIRFLOW_API_ENDPOINT')

    
    model_config = SettingsConfigDict(env_file=dotenv, env_file_encoding="utf-8", extra="allow", case_sensitive=True)


settings = Settings()
