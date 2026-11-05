"""Respectful public catalogue adapters for GTA V HUB.

The vehicle endpoint follows the public GTACars API pattern referenced by the
GTALens project. The wheel importer reads the public GTALens wheel JSON file.
Check source terms before redistribution. No proxy rotation or rate-limit
bypass is used.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any

import aiohttp

log = logging.getLogger("gta_v_hub.catalog_sync")

VEHICLE_API = "https://gtacars.net/api/?game=gta5&page={page}&perPage=60&sort=alphabet&sortReverse=false&q="
WHEELS_JSON = "https://raw.githubusercontent.com/nosv1/GTALens/dev/wheels.json"
USER_AGENT = "GTA-V-HUB-Community-Bot/1.0 (low-rate catalogue sync)"

CLASS_NAMES: dict[str, str] = {
    "boat": "Boats",
    "commercial": "Commercial",
    "compacts": "Compacts",
    "coupe": "Coupes",
    "cycle": "Cycles",
    "emergency": "Emergency",
    "helicopter": "Helicopters",
    "industrial": "Industrial",
    "military": "Military",
    "motorcycle": "Motorcycles",
    "muscle": "Muscle",
    "off_road": "Off-Road",
    "open_wheel": "Open Wheel",
    "plane": "Planes",
    "rail": "Rail",
    "sedan": "Sedans",
    "service": "Service",
    "sport": "Sports",
    "sport_classic": "Sports Classics",
    "super": "Supers",
    "suv": "SUVs",
    "utility": "Utility",
    "van": "Vans",
}


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize_vehicle(raw: dict[str, Any]) -> dict[str, Any] | None:
    name = raw.get("_name")
    if not isinstance(name, str) or not name.strip():
        return None
    class_code = raw.get("_class")
    price = _number(raw.get("_priceMp"))
    lap_ms = _number(raw.get("_lapTime"))
    vehicle_id = str(raw.get("id") or "")
    return {
        "name": name.strip(),
        "manufacturer": str(raw.get("_manuf") or "Unknown").title(),
        "class": CLASS_NAMES.get(str(class_code), str(class_code or "Unknown").replace("_", " ").title()),
        "price": int(price * 1000) if price is not None else None,
        "drivetrain": str(raw.get("_dt") or "Unknown").upper(),
        "model": str(raw.get("_model") or ""),
        "lap_time": lap_ms / 1000 if lap_ms is not None else None,
        "top_speed": _number(raw.get("_topSpeed")),
        "seats": raw.get("_seats"),
        "description": str(raw.get("_description") or "")[:1500],
        "url": f"https://gtacars.net/gta5/{vehicle_id}" if vehicle_id else "https://gtacars.net/gta5",
        "_catalog_source": "gtacars",
    }


def normalize_wheels(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        raise ValueError("Wheel provider response was not a JSON object.")
    rows: list[dict[str, Any]] = []
    for key, raw in payload.items():
        if not isinstance(raw, dict):
            continue
        effects = raw.get("wheel_effects") or {}
        if not isinstance(effects, dict):
            effects = {}
        rows.append({
            "name": str(raw.get("name") or str(key).split(" (")[0]),
            "type": str(raw.get("wheel_type") or "Unknown"),
            "price": raw.get("price"),
            "suggested": raw.get("suggested_state"),
            "traction_bias": effects.get("bias"),
            "slip_angle": effects.get("slip_angle"),
            "anti_roll": effects.get("anti_roll"),
            "description": str(effects.get("note") or "")[:500],
            "_catalog_source": "gtalens-wheel-reference",
        })
    return rows


async def _fetch_json(session: aiohttp.ClientSession, url: str) -> Any:
    async with session.get(url, headers={"User-Agent": USER_AGENT}) as response:
        response.raise_for_status()
        return await response.json(content_type=None)


def _write_catalog(
    path: Path,
    remote_rows: list[dict[str, Any]],
    source: str,
    key_fields: tuple[str, ...],
) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing: list[dict[str, Any]] = []
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                existing = [row for row in payload if isinstance(row, dict)]
            elif isinstance(payload, dict):
                existing = [row for row in payload.values() if isinstance(row, dict)]
        except (OSError, json.JSONDecodeError):
            raise ValueError(f"Cannot safely replace invalid catalogue file: {path}")

    # Replace only records previously imported from this provider. Preserve local/manual records.
    merged = [row for row in existing if row.get("_catalog_source") != source]
    seen: set[tuple[str, ...]] = set()
    for row in remote_rows:
        identity = tuple(str(row.get(field) or "").casefold() for field in key_fields)
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(row)

    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(merged, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return len(remote_rows)


class CatalogSyncService:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    def _record_success(self, kind: str, count: int) -> None:
        log_path = self.data_dir / "catalog_sync_history.json"
        history: list[dict[str, Any]] = []
        if log_path.exists():
            try:
                raw = json.loads(log_path.read_text(encoding="utf-8"))
                if isinstance(raw, list):
                    history = [item for item in raw if isinstance(item, dict)]
            except (OSError, json.JSONDecodeError):
                history = []

        history.append({
            "catalogue": kind,
            "records": count,
            "status": "success",
            "synced_at": datetime.now(timezone.utc).isoformat(),
        })
        self.data_dir.mkdir(parents=True, exist_ok=True)
        fd, temp_name = tempfile.mkstemp(prefix=".catalog_sync_history.", suffix=".tmp", dir=str(self.data_dir))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(history[-20:], handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temp_name, log_path)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise

    def history(self, limit: int = 4) -> list[dict[str, Any]]:
        path = self.data_dir / "catalog_sync_history.json"
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if not isinstance(payload, list):
            return []
        return [item for item in payload if isinstance(item, dict)][-max(1, min(limit, 20)):][::-1]

    async def sync_vehicles(self) -> int:
        timeout = aiohttp.ClientTimeout(total=30)
        rows: list[dict[str, Any]] = []
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for page in range(1, 101):
                payload = await _fetch_json(session, VEHICLE_API.format(page=page))
                if not isinstance(payload, dict) or not payload.get("status"):
                    raise RuntimeError(f"Vehicle provider returned an unsuccessful response on page {page}.")
                page_rows = (payload.get("payload") or {}).get("vehicles") or []
                if not isinstance(page_rows, list):
                    raise ValueError("Vehicle provider returned an unexpected vehicles list.")
                if not page_rows:
                    break
                rows.extend(
                    item for raw in page_rows if isinstance(raw, dict)
                    if (item := normalize_vehicle(raw)) is not None
                )
                await asyncio.sleep(0.75)
        count = _write_catalog(
            self.data_dir / "vehicles.json",
            rows,
            "gtacars",
            ("manufacturer", "name"),
        )
        self._record_success("vehicles", count)
        return count

    async def sync_wheels(self) -> int:
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            payload = await _fetch_json(session, WHEELS_JSON)
        rows = normalize_wheels(payload)
        count = _write_catalog(
            self.data_dir / "wheels.json",
            rows,
            "gtalens-wheel-reference",
            ("name", "type"),
        )
        self._record_success("wheels", count)
        return count

    async def sync(self, kind: str) -> dict[str, int]:
        if kind == "vehicles":
            return {"vehicles": await self.sync_vehicles()}
        if kind == "wheels":
            return {"wheels": await self.sync_wheels()}
        if kind == "all":
            return {
                "vehicles": await self.sync_vehicles(),
                "wheels": await self.sync_wheels(),
            }
        raise ValueError(f"Unknown catalogue: {kind}")

