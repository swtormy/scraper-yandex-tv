import sys
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    MLDB_USER: str = "postgres"
    MLDB_PASSWORD: str = "postgres"
    MLDB_HOST: str = "localhost"
    MLDB_PORT: str = "5432"
    MLDB_NAME: str = "public"
    MLDB_SCHEMA: str = "public"

    DEBUG: bool = False

    YANDEX_TV_COOKIE_I: str = ""
    YANDEX_TV_X_SK: str = ""


settings = Settings()


def setup_logger(debug: bool):
    logger.remove()
    log_level = "DEBUG" if debug else "INFO"
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    logger.add(sys.stderr, level=log_level, format=log_format)

    log_file_path = Path(__file__).parent / "logs" / "app.log"
    logger.add(
        log_file_path,
        rotation="10 MB",
        retention="10 days",
        level="INFO",
        format=log_format,
        encoding="utf-8",
    )
    logger.info(f"Logger initialized. Debug mode: {debug}. Log level: {log_level}")


setup_logger(settings.DEBUG)
