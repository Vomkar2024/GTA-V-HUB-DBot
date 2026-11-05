"""First-party catalogue sync service for GTA V HUB • Los Santos Network.

Connects to the self-hosted catalogue API configured via CATALOGUE_API_BASE_URL.
Safely updates local catalogue stores while preserving manual entries and
retaining local fallback data whenever external endpoints are unreachable.
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

DEFAULT_BASE_URL_PLACEHOLDER = "https://catalogue.placeholder.local"
USER_AGENT = "GTA-V-HUB/1.0 (Los Santos Network Catalogue Sync)"

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


class CatalogueSyncError(RuntimeError):
    """Raised when a catalogue synchronization fails while retaining local files."""


def _number(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def normalize_vehicle(raw: dict[str, Any], base_url: str = "") -> dict[str, Any] | None:
    name = raw.get("name") or raw.get("_name")
    if not isinstance(name, str) or not name.strip():
        return None
    class_code = raw.get("class") or raw.get("_class")
    raw_price = raw.get("price") if raw.get("price") is not None else raw.get("_priceMp")
    price = _number(raw_price)
    raw_lap = raw.get("lap_time") if raw.get("lap_time") is not None else raw.get("_lapTime")
    lap_ms = _number(raw_lap)
    vehicle_id = str(raw.get("id") or raw.get("slug") or "")

    clean_base = base_url.rstrip("/") if base_url else ""
    if vehicle_id and clean_base:
        url = f"{clean_base}/vehicles/{vehicle_id}"
    elif clean_base:
        url = f"{clean_base}/vehicles"
    elif vehicle_id:
        url = f"/vehicles/{vehicle_id}"
    else:
        url = "/vehicles"

    if price is not None and "_priceMp" in raw and "price" not in raw:
        price_val = int(price * 1000)
    elif price is not None:
        price_val = int(price)
    else:
        price_val = None

    if lap_ms is not None and lap_ms > 1000:
        lap_time_sec: float | None = lap_ms / 1000.0
    else:
        lap_time_sec = lap_ms

    return {
        "name": name.strip(),
        "manufacturer": str(raw.get("manufacturer") or raw.get("_manuf") or "Unknown").title(),
        "class": CLASS_NAMES.get(str(class_code), str(class_code or "Unknown").replace("_", " ").title()),
        "price": price_val,
        "drivetrain": str(raw.get("drivetrain") or raw.get("_dt") or "Unknown").upper(),
        "model": str(raw.get("model") or raw.get("_model") or ""),
        "lap_time": lap_time_sec,
        "top_speed": _number(raw.get("top_speed") or raw.get("_topSpeed")),
        "seats": raw.get("seats") or raw.get("_seats"),
        "description": str(raw.get("description") or raw.get("_description") or "")[:1500],
        "url": url,
        "_catalog_source": "first-party",
    }


def normalize_wheels(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        for key, raw in payload.items():
            if not isinstance(raw, dict):
                continue
            effects = raw.get("wheel_effects") or {}
            if not isinstance(effects, dict):
                effects = {}
            rows.append({
                "name": str(raw.get("name") or str(key).split(" (")[0]),
                "type": str(raw.get("wheel_type") or raw.get("type") or "Unknown"),
                "price": raw.get("price"),
                "suggested": raw.get("suggested_state") or raw.get("suggested"),
                "traction_bias": effects.get("bias", raw.get("traction_bias")),
                "slip_angle": effects.get("slip_angle", raw.get("slip_angle")),
                "anti_roll": effects.get("anti_roll", raw.get("anti_roll")),
                "description": str(effects.get("note", raw.get("description", "")))[:500],
                "_catalog_source": "first-party",
            })
        return rows

    if isinstance(payload, list):
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            effects = raw.get("wheel_effects") or {}
            if not isinstance(effects, dict):
                effects = {}
            rows.append({
                "name": str(raw.get("name") or "Unnamed Wheel"),
                "type": str(raw.get("wheel_type") or raw.get("type") or "Unknown"),
                "price": raw.get("price"),
                "suggested": raw.get("suggested_state") or raw.get("suggested"),
                "traction_bias": effects.get("bias", raw.get("traction_bias")),
                "slip_angle": effects.get("slip_angle", raw.get("slip_angle")),
                "anti_roll": effects.get("anti_roll", raw.get("anti_roll")),
                "description": str(effects.get("note", raw.get("description", "")))[:500],
                "_catalog_source": "first-party",
            })
        return rows

    raise ValueError("Wheel catalogue response was neither a JSON object nor an array.")


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

    # Replace only records previously imported from this source. Preserve local/manual records.
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
    def __init__(self, data_dir: Path, base_url: str | None = None) -> None:
        self.data_dir = Path(data_dir)
        configured = base_url or os.getenv("CATALOGUE_API_BASE_URL") or DEFAULT_BASE_URL_PLACEHOLDER
        self.base_url = configured.strip().rstrip("/")

    def is_placeholder(self) -> bool:
        clean = (self.base_url or "").strip().casefold()
        return not clean or "placeholder.local" in clean

    def validate_endpoint(self) -> None:
        if self.is_placeholder():
            raise CatalogueSyncError(
                f"Catalogue API base URL is set to placeholder domain ('{self.base_url}'). "
                "To synchronize, configure CATALOGUE_API_BASE_URL=http://127.0.0.1:8080 in .env "
                "and start the server with 'python server.py'. "
                "Alternatively, use '/hubadmin reload-catalogs' to reload existing local files without an API server."
            )

    def vehicle_endpoint(self, page: int) -> str:
        return f"{self.base_url}/api/?game=gta5&page={page}&perPage=60&sort=alphabet&sortReverse=false&q="

    def wheels_endpoint(self) -> str:
        return f"{self.base_url}/api/wheels"

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
        self.validate_endpoint()
        timeout = aiohttp.ClientTimeout(total=30)
        rows: list[dict[str, Any]] = []
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for page in range(1, 101):
                    url = self.vehicle_endpoint(page)
                    try:
                        payload = await _fetch_json(session, url)
                    except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
                        hint = ""
                        if "127.0.0.1" in url or "localhost" in url:
                            hint = " Ensure the local catalogue server is running ('python server.py') or use '/hubadmin reload-catalogs'."
                        log.error(
                            "Failed to sync vehicle catalogue from '%s': %s.%s "
                            "Ensure CATALOGUE_API_BASE_URL is reachable and configured. "
                            "Existing local vehicle catalogue files were retained.",
                            url,
                            exc,
                            hint,
                        )
                        raise CatalogueSyncError(
                            f"Could not connect to catalogue endpoint '{url}' ({exc}).{hint} "
                            "Existing local vehicle data retained."
                        ) from exc

                    if not isinstance(payload, dict) or not payload.get("status"):
                        log.error(
                            "Vehicle catalogue endpoint '%s' returned an error or non-successful status. "
                            "Existing local vehicle catalogue files were retained.",
                            url,
                        )
                        raise CatalogueSyncError(
                            f"Vehicle catalogue endpoint '{url}' returned an unsuccessful status. "
                            "Existing local vehicle data retained."
                        )

                    page_rows = (payload.get("payload") or {}).get("vehicles") or []
                    if not isinstance(page_rows, list):
                        log.error(
                            "Vehicle catalogue endpoint returned unexpected payload format. "
                            "Existing local vehicle catalogue files were retained."
                        )
                        raise CatalogueSyncError(
                            "Vehicle catalogue returned an unexpected format. Existing local vehicle data retained."
                        )

                    if not page_rows:
                        break

                    rows.extend(
                        item for raw in page_rows if isinstance(raw, dict)
                        if (item := normalize_vehicle(raw, self.base_url)) is not None
                    )
                    await asyncio.sleep(0.05)
        except CatalogueSyncError:
            raise
        except Exception as exc:
            hint = ""
            if "127.0.0.1" in self.base_url or "localhost" in self.base_url:
                hint = " Ensure the local catalogue server is running ('python server.py') or use '/hubadmin reload-catalogs'."
            log.error(
                "Unexpected error during vehicle catalogue sync from '%s': %s.%s "
                "Existing local vehicle catalogue files were retained.",
                self.base_url,
                exc,
                hint,
            )
            raise CatalogueSyncError(
                f"Vehicle catalogue sync failed: {exc}.{hint} Existing local vehicle data retained."
            ) from exc

        count = _write_catalog(
            self.data_dir / "vehicles.json",
            rows,
            "first-party",
            ("manufacturer", "name"),
        )
        self._record_success("vehicles", count)
        return count

    async def sync_wheels(self) -> int:
        self.validate_endpoint()
        timeout = aiohttp.ClientTimeout(total=25)
        url = self.wheels_endpoint()
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    payload = await _fetch_json(session, url)
                except (aiohttp.ClientError, asyncio.TimeoutError, json.JSONDecodeError) as exc:
                    hint = ""
                    if "127.0.0.1" in url or "localhost" in url:
                        hint = " Ensure the local catalogue server is running ('python server.py') or use '/hubadmin reload-catalogs'."
                    log.error(
                        "Failed to sync wheel catalogue from '%s': %s.%s "
                        "Ensure CATALOGUE_API_BASE_URL is reachable and configured. "
                        "Existing local wheel catalogue files were retained.",
                        url,
                        exc,
                        hint,
                    )
                    raise CatalogueSyncError(
                        f"Could not connect to wheel catalogue endpoint '{url}' ({exc}).{hint} "
                        "Existing local wheel data retained."
                    ) from exc

            rows = normalize_wheels(payload)
        except CatalogueSyncError:
            raise
        except Exception as exc:
            hint = ""
            if "127.0.0.1" in self.base_url or "localhost" in self.base_url:
                hint = " Ensure the local catalogue server is running ('python server.py') or use '/hubadmin reload-catalogs'."
            log.error(
                "Unexpected error during wheel catalogue sync from '%s': %s.%s "
                "Existing local wheel catalogue files were retained.",
                self.base_url,
                exc,
                hint,
            )
            raise CatalogueSyncError(
                f"Wheel catalogue sync failed: {exc}.{hint} Existing local wheel data retained."
            ) from exc

        count = _write_catalog(
            self.data_dir / "wheels.json",
            rows,
            "first-party",
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
