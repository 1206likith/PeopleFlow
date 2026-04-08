from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, List

from dotenv import dotenv_values, load_dotenv
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

logger = logging.getLogger(__name__)


def _resolve_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "modules").exists() or (parent / "apps").exists():
            if parent.name == "backend" and (parent.parent / "modules").exists():
                return parent.parent
            if (parent / "modules").exists():
                return parent
    return current.parents[2]


ROOT_DIR = _resolve_root()


def _default_cors_origins() -> List[str]:
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://peopleflow.vercel.app",
        "https://peopleflow-ruddy.vercel.app",
    ]


def _default_allowed_file_types() -> List[str]:
    return [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/json",
    ]


def _default_feature_flags_path() -> str:
    return str(ROOT_DIR / "artifacts" / "feature_flags.json")


def _default_audit_log_path() -> str:
    return str(ROOT_DIR / "artifacts" / "audit.log")


def _default_evac_params_path() -> str:
    return str(ROOT_DIR / "apps" / "backend" / "app" / "data" / "evacuation_parameters.json")


class Settings(BaseSettings):
    APP_NAME: str = "PeopleFlow"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    APP_MODE: str = "demo"
    SERVICE_NAME: str = "PeopleFlow API"
    SERVICE_VERSION: str = "1.0.0"
    BUILD_SHA: str = "dev"
    BUILD_TIME: str = ""

    CORS_ORIGINS: List[str] | str = Field(default_factory=_default_cors_origins)
    CORS_ORIGIN_REGEX: str = r"^https://peopleflow(?:-[a-z0-9-]+)*\.vercel\.app$"
    FRONTEND_URL: str = "http://localhost:3000"

    DATABASE_MODE: str = "mongodb"
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "peopleflow"
    MONGODB_MAX_POOL_SIZE: int = 100
    SQLITE_URL: str = "sqlite+aiosqlite:///./data/peopleflow.db"
    LOCAL_FILE_DB_PATH: str = "./data/db"

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_ENABLED: bool = False

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    ADMIN_KEY_ENABLED: bool = True
    ADMIN_API_KEY: str = "change-me"
    ACTOR_HEADER_ALLOWED_IN_PRODUCTION: bool = False

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    MAX_REQUEST_SIZE: int = 25 * 1024 * 1024
    ALLOWED_FILE_TYPES: List[str] | str = Field(default_factory=_default_allowed_file_types)

    GZIP_MINIMUM_SIZE: int = 1024
    GZIP_LEVEL: int = 5

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 20

    SENDGRID_API_KEY: str = ""
    FROM_EMAIL: str = "noreply@peopleflow.com"

    UNITY_WS_URL: str = "ws://localhost:8765"
    UNITY_ENABLED: bool = False

    AI_MODEL_REGISTRY_PATH: str = str(ROOT_DIR / "modules" / "ai_engine" / "data" / "model_registry.json")
    AI_CONGESTION_MODEL_PATH: str = str(ROOT_DIR / "modules" / "ai_engine" / "data" / "saved_models" / "congestion_predictor.pkl")
    AI_EXIT_RL_MODEL_PATH: str = str(ROOT_DIR / "modules" / "ai_engine" / "data" / "saved_models" / "exit_allocation_rl.pth")
    EVAC_PARAMS_PATH: str = Field(default_factory=_default_evac_params_path)

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    REQUIRE_HTTPS: bool = False

    IDEMPOTENCY_TTL_SECONDS: int = 24 * 3600
    IDEMPOTENCY_MAX_ENTRIES: int = 5000

    FLOORPLAN_CACHE_TTL_SECONDS: int = 6 * 3600
    FLOORPLAN_CACHE_MAX_ENTRIES: int = 2000

    MAX_CONCURRENT_SIMULATIONS: int = 8

    FEATURE_FLAGS_FILE: str = Field(default_factory=_default_feature_flags_path)
    ALLOW_FEATURE_MUTATION: bool = True
    AUDIT_LOG_FILE: str = Field(default_factory=_default_audit_log_path)
    AUDIT_LOG_MAX_ENTRIES: int = 5000
    AUDIT_LOG_TTL_SECONDS: int = 7 * 24 * 3600

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        validate_default=True,
    )

    @property
    def IS_DEMO_MODE(self) -> bool:
        return self.APP_MODE != "production"

    @field_validator("APP_MODE", mode="before")
    @classmethod
    def _normalize_app_mode(cls, value: Any) -> str:
        mode = str(value or "demo").strip().lower()
        if mode not in {"demo", "production"}:
            return "demo"
        return mode

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value: Any) -> str:
        return str(value or "development").strip().lower()

    @field_validator("DEBUG", "REDIS_ENABLED", "ADMIN_KEY_ENABLED", "ACTOR_HEADER_ALLOWED_IN_PRODUCTION", "RATE_LIMIT_ENABLED", "UNITY_ENABLED", "ENABLE_METRICS", "REQUIRE_HTTPS", "ALLOW_FEATURE_MUTATION", mode="before")
    @classmethod
    def _normalize_boolish_flags(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        normalized = str(value).strip().lower()
        if normalized in {"1", "true", "t", "yes", "y", "on", "debug", "dev", "development"}:
            return True
        if normalized in {"0", "false", "f", "no", "n", "off", "release", "prod", "production", ""}:
            return False
        logger.warning("Unrecognized boolean-like setting value %r; defaulting to false", value)
        return False

    @field_validator("LOG_LEVEL", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> str:
        return str(value or "INFO").strip().upper()

    @field_validator("LOG_FORMAT", mode="before")
    @classmethod
    def _normalize_log_format(cls, value: Any) -> str:
        candidate = str(value or "json").strip().lower()
        return candidate if candidate in {"json", "text"} else "json"

    @field_validator("CORS_ORIGINS", "ALLOWED_FILE_TYPES", mode="before")
    @classmethod
    def _parse_csv_or_json_list(cls, value: Any):
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _finalize(self):
        required = {
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            str(self.FRONTEND_URL).strip(),
        }

        current = self.CORS_ORIGINS
        if isinstance(current, str):
            current_list = [item.strip() for item in current.split(",") if item.strip()]
        else:
            current_list = [str(item).strip() for item in current if str(item).strip()]

        if self.ENVIRONMENT != "production":
            self.CORS_ORIGINS = list(dict.fromkeys([*current_list, *sorted(required)]))
            local_origin_regex = r"^https?://(?:localhost|127\.0\.0\.1)(?::\d+)?$"
            existing_regex = (self.CORS_ORIGIN_REGEX or "").strip()
            if existing_regex:
                has_localhost = "localhost" in existing_regex or "127\\.0\\.0\\.1" in existing_regex
                if not has_localhost:
                    self.CORS_ORIGIN_REGEX = f"(?:{existing_regex})|(?:{local_origin_regex})"
            else:
                self.CORS_ORIGIN_REGEX = local_origin_regex
        else:
            self.CORS_ORIGINS = current_list

        return self


def _warn_on_unknown_dotenv_keys(settings_cls: type[Settings]) -> None:
    env_file = ROOT_DIR / ".env"
    if not env_file.exists():
        return
    try:
        parsed = dotenv_values(env_file)
    except Exception:
        return

    known_keys = set(settings_cls.model_fields)
    unknown_keys = sorted(key for key in parsed if key and key not in known_keys)
    if unknown_keys:
        logger.warning(
            "Ignoring unknown environment keys from %s: %s",
            env_file,
            ", ".join(unknown_keys),
        )


_warn_on_unknown_dotenv_keys(Settings)
settings = Settings()
