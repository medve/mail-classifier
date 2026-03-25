"""Configuration from environment variables."""

import os
from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BASE_DIR / "data"
HISTORY_DIR: Path = DATA_DIR / "history"
PEOPLE_REGISTRY_PATH: Path = DATA_DIR / "people_registry.json"

ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

CORRELATION_MODEL: str = os.environ.get("CORRELATION_MODEL", "claude-sonnet-4-20250514")
EXTRACTION_MODEL: str = os.environ.get("EXTRACTION_MODEL", "claude-sonnet-4-20250514")
CLASSIFICATION_MODEL: str = os.environ.get("CLASSIFICATION_MODEL", "claude-sonnet-4-20250514")
DRAFTING_MODEL: str = os.environ.get("DRAFTING_MODEL", "claude-sonnet-4-20250514")
VERIFICATION_MODEL: str = os.environ.get("VERIFICATION_MODEL", "claude-sonnet-4-20250514")
BRIEFING_MODEL: str = os.environ.get("BRIEFING_MODEL", "claude-sonnet-4-20250514")

MAX_RETRIES_PER_STAGE: int = 2
HISTORY_DAYS: int = 7

COMPANY_DOMAINS: list[str] = os.environ.get("COMPANY_DOMAINS", "company.com").split(",")

REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
TASK_TTL_SECONDS: int = int(os.environ.get("TASK_TTL_SECONDS", "86400"))
