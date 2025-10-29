from __future__ import annotations

import os
from dataclasses import dataclass


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DEFAULT_DATA_DIR = os.path.join(PROJECT_ROOT, "data")
DEFAULT_MODEL_DIR = os.path.join(PROJECT_ROOT, "models")
DEFAULT_CACHE_DIR = os.path.join(PROJECT_ROOT, "artifacts")


@dataclass
class BaseConfig:
    SECRET_KEY: str = os.environ.get("SMARTCOURSE_SECRET_KEY", "smartcourse-dev-key")
    SQLALCHEMY_DATABASE_URI: str | None = os.environ.get("SMARTCOURSE_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    JSON_SORT_KEYS: bool = False
    CORS_ORIGINS: str | list[str] = os.environ.get("SMARTCOURSE_CORS_ORIGINS", "*")
    DATASET_RAW_PATH: str = os.environ.get("SMARTCOURSE_DATASET", os.path.join(DEFAULT_DATA_DIR, "courses_raw.csv"))
    DATASET_PROCESSED_PATH: str = os.environ.get("SMARTCOURSE_DATASET_PROCESSED", os.path.join(DEFAULT_DATA_DIR, "courses_clean.csv"))
    MODEL_CACHE_DIR: str = os.environ.get("SMARTCOURSE_MODEL_DIR", DEFAULT_MODEL_DIR)
    EMBEDDING_MODEL_NAME: str = os.environ.get("SMARTCOURSE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    MAX_RESULTS: int = int(os.environ.get("SMARTCOURSE_MAX_RESULTS", "10"))


@dataclass
class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True


@dataclass
class TestingConfig(BaseConfig):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///:memory:"
    MAX_RESULTS: int = 5


@dataclass
class ProductionConfig(BaseConfig):
    DEBUG: bool = False


CONFIG_MAPPING = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config(name: str | None) -> type[BaseConfig]:
    if not name:
        name = os.environ.get("SMARTCOURSE_ENV", "default")
    config_cls = CONFIG_MAPPING.get(name.lower())
    if config_cls is None:
        raise KeyError(f"Unknown configuration '{name}'. Valid options: {', '.join(CONFIG_MAPPING)}")
    return config_cls
