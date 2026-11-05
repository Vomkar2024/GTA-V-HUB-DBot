from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    guild_id: int | None
    owner_ids: frozenset[int]
    invite_url: str | None
    support_url: str | None
    donate_url: str | None
    data_dir: Path
    database_path: Path
    weather_api_url: str | None
    sync_api_url: str | None
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        raw_guild_id = os.getenv("GUILD_ID", "").strip()
        owner_ids = frozenset(
            int(value.strip())
            for value in os.getenv("OWNER_IDS", "").split(",")
            if value.strip().isdigit()
        )
        data_dir = Path(os.getenv("DATA_DIR", "data")).expanduser()
        database_path = Path(os.getenv("DATABASE_PATH", "data/gtavhub.sqlite3")).expanduser()
        if not data_dir.is_absolute():
            data_dir = Path.cwd() / data_dir
        if not database_path.is_absolute():
            database_path = Path.cwd() / database_path
        return cls(
            token=os.getenv("DISCORD_TOKEN", "").strip(),
            guild_id=int(raw_guild_id) if raw_guild_id.isdigit() else None,
            owner_ids=owner_ids,
            invite_url=_optional_url("INVITE_URL"),
            support_url=_optional_url("SUPPORT_URL"),
            donate_url=_optional_url("DONATE_URL"),
            data_dir=data_dir,
            database_path=database_path,
            weather_api_url=_optional_url("GTA_HUB_WEATHER_API_URL"),
            sync_api_url=_optional_url("GTA_HUB_SYNC_API_URL"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


def _optional_url(key: str) -> str | None:
    value = os.getenv(key, "").strip()
    return value or None
