"""GTA V HUB • Los Santos Network first-party catalogue API server.

Provides first-party HTTP endpoints for vehicle and wheel catalogues,
replacing third-party providers with self-hosted API services.
"""
from __future__ import annotations

import argparse
import json
import logging
from math import ceil
from pathlib import Path
from typing import Any

from aiohttp import web

from gta_hub.views import resolve_vehicle_image

logger = logging.getLogger("gta_v_hub.api")


def _number(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            cleaned = value.replace("$", "").replace(",", "").lower().replace("mph", "").strip()
            return float(cleaned) if cleaned else None
        return float(value)
    except (ValueError, TypeError):
        return None


def format_vehicle_for_api(raw: dict[str, Any], base_url: str = "") -> dict[str, Any]:
    name = str(raw.get("name") or raw.get("_name") or "").strip()
    slug = str(
        raw.get("id")
        or raw.get("slug")
        or name.lower().replace(" ", "-").replace("_", "-")
    )
    manufacturer = str(raw.get("manufacturer") or raw.get("_manuf") or "Unknown").strip().title()
    if manufacturer.startswith("_"):
        manufacturer = manufacturer[1:]
    vehicle_class = str(raw.get("class") or raw.get("_class") or raw.get("vehicle_class") or "Unknown").strip()

    raw_price = raw.get("price")
    if raw_price is None:
        raw_price = raw.get("_priceMp")
    num_price = _number(raw_price)
    if num_price is not None and "_priceMp" in raw and "price" not in raw:
        price_int: int | None = int(num_price * 1000)
    elif num_price is not None:
        price_int = int(num_price)
    else:
        price_int = None

    raw_lap = raw.get("lap_time")
    if raw_lap is None:
        raw_lap = raw.get("_lapTime")
    lap_num = _number(raw_lap)
    if lap_num is not None and lap_num > 1000:
        lap_sec: float | None = lap_num / 1000.0
    else:
        lap_sec = lap_num

    raw_speed = raw.get("top_speed")
    if raw_speed is None:
        raw_speed = raw.get("_topSpeed")
    top_spd = _number(raw_speed)

    drivetrain = str(raw.get("drivetrain") or raw.get("_dt") or "Unknown").upper()
    model = str(raw.get("model") or raw.get("_model") or slug)
    seats = raw.get("seats") or raw.get("_seats")
    description = str(raw.get("description") or raw.get("_description") or "")[:1500]

    clean_base = base_url.rstrip("/") if base_url else ""
    url = f"{clean_base}/vehicles/{slug}" if clean_base else f"/vehicles/{slug}"

    image_url: str | None = None
    raw_img = raw.get("image_url") or raw.get("image")
    if isinstance(raw_img, str) and (raw_img.startswith("http://") or raw_img.startswith("https://")):
        image_url = raw_img
    else:
        assets_dir = Path.cwd() / "assets" / "images"
        matched_img = resolve_vehicle_image(raw, assets_dir=assets_dir)
        if matched_img:
            img_file = matched_img.name
            image_url = f"{clean_base}/images/{img_file}" if clean_base else f"/images/{img_file}"

    return {
        "id": slug,
        "_name": name,
        "_manuf": manufacturer.lower(),
        "_class": vehicle_class.lower(),
        "_priceMp": (price_int / 1000.0) if price_int is not None else None,
        "_dt": drivetrain.lower(),
        "_model": model,
        "_lapTime": (lap_sec * 1000.0) if lap_sec is not None else None,
        "_topSpeed": top_spd,
        "_seats": seats,
        "_description": description,
        "name": name,
        "manufacturer": manufacturer,
        "class": vehicle_class,
        "price": price_int,
        "drivetrain": drivetrain,
        "model": model,
        "lap_time": lap_sec,
        "top_speed": top_spd,
        "seats": seats,
        "description": description,
        "url": url,
        "image_url": image_url,
        "_catalog_source": "first-party",
    }


def format_wheels_for_api(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if not isinstance(payload, list):
        return {}
    formatted: dict[str, Any] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "Unnamed Wheel")
        wheel_type = str(item.get("type") or item.get("wheel_type") or "Unknown")
        key = f"{name} ({wheel_type})"
        effects = item.get("wheel_effects")
        if not isinstance(effects, dict):
            effects = {
                "bias": item.get("traction_bias"),
                "slip_angle": item.get("slip_angle"),
                "anti_roll": item.get("anti_roll"),
                "note": item.get("description", ""),
            }
        formatted[key] = {
            "name": name,
            "wheel_type": wheel_type,
            "price": item.get("price"),
            "suggested_state": item.get("suggested") or item.get("suggested_state"),
            "wheel_effects": effects,
            "_catalog_source": "first-party",
        }
    return formatted


class CatalogueApiController:
    def __init__(self, data_dir: Path, base_url: str = ""):
        self.data_dir = Path(data_dir)
        self.base_url = base_url.rstrip("/")
        self._vehicles_cache: tuple[float, list[dict[str, Any]], list[dict[str, Any]], dict[str, dict[str, Any]]] | None = None
        self._wheels_cache: tuple[float, Any, dict[str, Any]] | None = None

    def _get_mtime(self, filename: str) -> float:
        try:
            return (self.data_dir / filename).stat().st_mtime
        except OSError:
            return -1.0

    def _read_json(self, filename: str) -> Any:
        path = self.data_dir / filename
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Error reading %s: %s", path, exc)
            return []

    def get_raw_vehicles(self) -> list[dict[str, Any]]:
        mtime = self._get_mtime("vehicles.json")
        if self._vehicles_cache is not None and self._vehicles_cache[0] == mtime:
            return self._vehicles_cache[1]

        raw = self._read_json("vehicles.json")
        if isinstance(raw, list):
            raw_list = [row for row in raw if isinstance(row, dict)]
        elif isinstance(raw, dict):
            raw_list = [row for row in raw.values() if isinstance(row, dict)]
        else:
            raw_list = []

        formatted = [
            item for raw_item in raw_list
            if (item := format_vehicle_for_api(raw_item, self.base_url)) is not None
            and item.get("name")
        ]
        slug_map: dict[str, dict[str, Any]] = {}
        for item in formatted:
            slug_key = str(item.get("id", "")).casefold()
            name_key = str(item.get("name", "")).casefold()
            if slug_key:
                slug_map[slug_key] = item
            if name_key and name_key not in slug_map:
                slug_map[name_key] = item

        self._vehicles_cache = (mtime, raw_list, formatted, slug_map)
        return raw_list

    def get_formatted_vehicles(self) -> list[dict[str, Any]]:
        self.get_raw_vehicles()
        return self._vehicles_cache[2] if self._vehicles_cache else []

    def get_vehicle_by_slug(self, slug: str) -> dict[str, Any] | None:
        self.get_raw_vehicles()
        if not self._vehicles_cache:
            return None
        return self._vehicles_cache[3].get(slug.casefold())

    def get_raw_wheels(self) -> Any:
        mtime = self._get_mtime("wheels.json")
        if self._wheels_cache is not None and self._wheels_cache[0] == mtime:
            return self._wheels_cache[1]

        raw = self._read_json("wheels.json")
        formatted = format_wheels_for_api(raw)
        self._wheels_cache = (mtime, raw, formatted)
        return raw

    def get_formatted_wheels(self) -> dict[str, Any]:
        self.get_raw_wheels()
        return self._wheels_cache[2] if self._wheels_cache else {}

    async def handle_status(self, request: web.Request) -> web.Response:
        vehicles = self.get_raw_vehicles()
        wheels = self.get_raw_wheels()
        wheels_count = len(wheels) if isinstance(wheels, (list, dict)) else 0
        return web.json_response({
            "status": "healthy",
            "service": "GTA V HUB • Los Santos Network Catalogue API",
            "version": "1.0.0",
            "records": {
                "vehicles": len(vehicles),
                "wheels": wheels_count,
            },
        })

    async def handle_vehicles(self, request: web.Request) -> web.Response:
        try:
            page = max(1, int(request.query.get("page", 1)))
        except ValueError:
            page = 1
        try:
            per_page = max(1, min(200, int(request.query.get("perPage", 60))))
        except ValueError:
            per_page = 60

        sort = request.query.get("sort", "alphabet").strip().casefold()
        reverse_raw = request.query.get("sortReverse", "false").strip().casefold()
        reverse = reverse_raw in ("true", "1", "yes")
        query = request.query.get("q", "").strip().casefold()
        class_filter = request.query.get("class", "").strip().casefold()
        manuf_filter = request.query.get("manufacturer", "").strip().casefold()

        formatted = list(self.get_formatted_vehicles())

        filtered = formatted
        if query:
            filtered = [
                v for v in filtered
                if query in v["name"].casefold()
                or query in v["manufacturer"].casefold()
                or query in v["model"].casefold()
                or query in v["class"].casefold()
            ]

        if class_filter:
            filtered = [v for v in filtered if v["class"].casefold() == class_filter]

        if manuf_filter:
            filtered = [v for v in filtered if v["manufacturer"].casefold() == manuf_filter]

        # Sorting
        if sort in ("alphabet", "name"):
            filtered.sort(key=lambda v: (v["name"].casefold(), v["manufacturer"].casefold()), reverse=reverse)
        elif sort == "price":
            filtered.sort(key=lambda v: (v["price"] is None, v["price"] or 0), reverse=reverse)
        elif sort == "manufacturer":
            filtered.sort(key=lambda v: (v["manufacturer"].casefold(), v["name"].casefold()), reverse=reverse)
        elif sort == "class":
            filtered.sort(key=lambda v: (v["class"].casefold(), v["name"].casefold()), reverse=reverse)
        elif sort == "top_speed":
            filtered.sort(key=lambda v: (v["top_speed"] is None, v["top_speed"] or 0.0), reverse=reverse)
        elif sort == "lap_time":
            filtered.sort(key=lambda v: (v["lap_time"] is None, v["lap_time"] or 999999.0), reverse=reverse)

        total = len(filtered)
        total_pages = max(1, ceil(total / per_page)) if total > 0 else 1
        start = (page - 1) * per_page
        end = start + per_page
        page_items = filtered[start:end] if start < total else []

        return web.json_response({
            "status": True,
            "payload": {
                "vehicles": page_items,
                "total": total,
                "page": page,
                "perPage": per_page,
                "totalPages": total_pages,
            },
        })

    async def handle_vehicle_detail(self, request: web.Request) -> web.Response:
        slug = request.match_info.get("id", "").strip()
        vehicle = self.get_vehicle_by_slug(slug)
        if vehicle is not None:
            return web.json_response({"status": True, "payload": vehicle})
        return web.json_response({"status": False, "error": "Vehicle not found"}, status=404)

    async def handle_wheels(self, request: web.Request) -> web.Response:
        formatted = self.get_formatted_wheels()
        if request.query.get("format") == "list":
            return web.json_response(list(formatted.values()))
        return web.json_response(formatted)


def create_app(data_dir: Path | str | None = None, base_url: str = "") -> web.Application:
    resolved_dir = Path(data_dir or "data").expanduser()
    if not resolved_dir.is_absolute():
        resolved_dir = Path.cwd() / resolved_dir
    controller = CatalogueApiController(resolved_dir, base_url=base_url)

    app = web.Application()
    if hasattr(web, "AppKey"):
        controller_key = web.AppKey("controller", CatalogueApiController)
        app[controller_key] = controller
    else:
        app["controller"] = controller

    # Routes mirroring existing API structure
    assets_dir = Path.cwd() / "assets" / "images"
    if assets_dir.is_dir():
        app.router.add_static("/images", str(assets_dir), show_index=False)

    app.router.add_get("/api", controller.handle_vehicles)
    app.router.add_get("/api/", controller.handle_vehicles)
    app.router.add_get("/api/vehicles", controller.handle_vehicles)
    app.router.add_get("/api/vehicles/{id}", controller.handle_vehicle_detail)
    app.router.add_get("/api/wheels", controller.handle_wheels)
    app.router.add_get("/api/wheels.json", controller.handle_wheels)
    app.router.add_get("/api/status", controller.handle_status)
    app.router.add_get("/api/health", controller.handle_status)

    return app


def run_server(host: str = "127.0.0.1", port: int = 8080, data_dir: Path | str | None = None) -> None:
    app = create_app(data_dir=data_dir, base_url=f"http://{host}:{port}")
    logger.info("Starting GTA V HUB • Los Santos Network Catalogue API at http://%s:%s", host, port)
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GTA V HUB • Los Santos Network Catalogue API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind to (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--data-dir", default="data", help="Path to catalog data directory (default: data)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    run_server(host=args.host, port=args.port, data_dir=args.data_dir)
