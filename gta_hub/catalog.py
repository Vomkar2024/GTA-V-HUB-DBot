from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

logger = logging.getLogger("gta_v_hub.catalog")

CATALOG_FILES = {
    "vehicles": "vehicles.json",
    "wheels": "wheels.json",
    "jobs": "jobs.json",
    "creators": "creators.json",
}


class CatalogError(RuntimeError):
    """Raised when a catalog file cannot be read or validated."""


class CatalogStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._catalogs: dict[str, list[dict[str, Any]]] = {}

    def load_all(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        loaded: dict[str, list[dict[str, Any]]] = {}
        for kind, filename in CATALOG_FILES.items():
            path = self.data_dir / filename
            if not path.exists():
                path.write_text("[]\n", encoding="utf-8")
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise CatalogError(f"Could not load {path}: {exc}") from exc
            if isinstance(payload, dict):
                payload = list(payload.values())
            if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
                raise CatalogError(f"{path} must contain a JSON array of objects")
            loaded[kind] = payload
        self._catalogs = loaded
        counts = ", ".join(f"{kind}={len(rows)}" for kind, rows in loaded.items())
        logger.info("Catalogs loaded: %s", counts)

    def all(self, kind: str) -> list[dict[str, Any]]:
        self._ensure_loaded()
        if kind not in self._catalogs:
            raise KeyError(f"Unknown catalog: {kind}")
        return list(self._catalogs[kind])

    def search(self, kind: str, query: str, *, limit: int = 25) -> list[dict[str, Any]]:
        self._ensure_loaded()
        needle = " ".join(query.casefold().split())
        if not needle:
            return []

        rows = self._catalogs.get(kind)
        if rows is None:
            raise KeyError(f"Unknown catalog: {kind}")

        scored: list[tuple[float, int, dict[str, Any]]] = []
        for index, row in enumerate(rows):
            name = _display_name(row).casefold()
            searchable_fields = ("manufacturer", "creator", "class", "type", "platform")
            extras = " ".join(str(row.get(field, "")) for field in searchable_fields)
            haystack = f"{name} {extras}".casefold().strip()
            if needle == name:
                score = 3.0
            elif needle in haystack:
                score = 2.0 + len(needle) / max(len(haystack), 1)
            else:
                score = SequenceMatcher(None, needle, haystack).ratio()
            if score >= 0.34:
                scored.append((score, index, row))

        scored.sort(key=lambda item: (-item[0], item[1]))
        return [row for _, _, row in scored[: max(1, min(limit, 25))]]

    def count(self, kind: str) -> int:
        self._ensure_loaded()
        return len(self._catalogs.get(kind, []))

    def counts(self) -> dict[str, int]:
        self._ensure_loaded()
        return {kind: len(rows) for kind, rows in self._catalogs.items()}

    def _ensure_loaded(self) -> None:
        if not self._catalogs:
            self.load_all()


def _display_name(row: dict[str, Any]) -> str:
    for key in ("name", "title", "vehicle", "wheel"):
        value = row.get(key)
        if value:
            return str(value)
    return "Unnamed entry"
