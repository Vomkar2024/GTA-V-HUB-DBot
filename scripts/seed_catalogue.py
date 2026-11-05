#!/usr/bin/env python3
"""GTA V HUB • Los Santos Network Catalogue Seeding and Sanitation Tool.

Sanitizes, standardizes, and seeds local catalogue files (vehicles.json, wheels.json)
under the project's own controlled schema without third-party dependencies or external URLs.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any

# Ensure repository root is on sys.path for gta_hub imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gta_hub.views import resolve_vehicle_image

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("seed_catalogue")


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


def sanitize_vehicle(raw: dict[str, Any], base_url: str = "") -> dict[str, Any]:
    name = str(raw.get("name") or raw.get("_name") or "").strip()
    slug = str(
        raw.get("id")
        or raw.get("slug")
        or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    )

    manufacturer = str(raw.get("manufacturer") or raw.get("_manuf") or "Unknown").strip().title()
    if manufacturer.startswith("_"):
        manufacturer = manufacturer[1:]
    vehicle_class = str(raw.get("class") or raw.get("_class") or raw.get("vehicle_class") or "Unknown").strip()

    raw_price = raw.get("price") if raw.get("price") is not None else raw.get("_priceMp")
    num_price = _number(raw_price)
    if num_price is not None and "_priceMp" in raw and "price" not in raw:
        price_val = int(num_price * 1000)
    elif num_price is not None:
        price_val = int(num_price)
    else:
        price_val = None

    raw_lap = raw.get("lap_time") if raw.get("lap_time") is not None else raw.get("_lapTime")
    lap_num = _number(raw_lap)
    if lap_num is not None and lap_num > 1000:
        lap_sec: float | None = round(lap_num / 1000.0, 3)
    else:
        lap_sec = round(lap_num, 3) if lap_num is not None else None

    raw_speed = raw.get("top_speed") if raw.get("top_speed") is not None else raw.get("_topSpeed")
    top_spd = round(_number(raw_speed), 2) if _number(raw_speed) is not None else None

    clean_base = base_url.rstrip("/") if base_url else ""
    url = f"{clean_base}/vehicles/{slug}" if clean_base else f"/vehicles/{slug}"

    result: dict[str, Any] = {
        "id": slug,
        "name": name,
        "manufacturer": manufacturer,
        "class": vehicle_class,
        "price": price_val,
        "drivetrain": str(raw.get("drivetrain") or raw.get("_dt") or "Unknown").upper(),
        "model": str(raw.get("model") or raw.get("_model") or slug),
        "lap_time": lap_sec,
        "top_speed": top_spd,
        "seats": raw.get("seats") or raw.get("_seats"),
        "description": str(raw.get("description") or raw.get("_description") or "")[:1500],
        "url": url,
        "_catalog_source": "first-party",
    }

    # Retain useful technical specs while purging external links or raw internal hashes
    spec_fields = (
        "storage", "dlc", "gears", "weight_kg", "tier",
        "brake_force", "cornering_grip", "straight_line_grip", "off_road_grip_loss",
    )
    for field in spec_fields:
        if field in raw and raw[field] not in (None, ""):
            result[field] = raw[field]

    # Assign clean image_url if a local asset exists or safe URL is present
    raw_img = raw.get("image_url")
    if isinstance(raw_img, str) and (raw_img.startswith("http://") or raw_img.startswith("https://")):
        result["image_url"] = raw_img
    else:
        assets_dir = Path.cwd() / "assets" / "images"
        matched_img = resolve_vehicle_image(result, assets_dir=assets_dir)
        if matched_img:
            result["image_url"] = f"{clean_base}/images/{matched_img.name}" if clean_base else f"/images/{matched_img.name}"

    return result


def sanitize_wheel(raw: dict[str, Any]) -> dict[str, Any]:
    name = str(raw.get("name") or "Unnamed Wheel").strip()
    wheel_type = str(raw.get("type") or raw.get("wheel_type") or "Unknown").strip()
    effects = raw.get("wheel_effects")
    if not isinstance(effects, dict):
        effects = {
            "bias": raw.get("traction_bias"),
            "slip_angle": raw.get("slip_angle"),
            "anti_roll": raw.get("anti_roll"),
            "note": raw.get("description", ""),
        }

    return {
        "name": name,
        "type": wheel_type,
        "price": raw.get("price"),
        "suggested": raw.get("suggested") or raw.get("suggested_state"),
        "traction_bias": effects.get("bias") or raw.get("traction_bias"),
        "slip_angle": effects.get("slip_angle") or raw.get("slip_angle"),
        "anti_roll": effects.get("anti_roll") or raw.get("anti_roll"),
        "description": str(effects.get("note") or raw.get("description") or "")[:500],
        "wheel_effects": effects,
        "_catalog_source": "first-party",
    }


def process_catalogue(data_dir: Path, base_url: str = "") -> None:
    data_dir = Path(data_dir)
    vehicles_path = data_dir / "vehicles.json"
    wheels_path = data_dir / "wheels.json"
    jobs_path = data_dir / "jobs.json"
    creators_path = data_dir / "creators.json"

    if vehicles_path.exists():
        try:
            raw_v = json.loads(vehicles_path.read_text(encoding="utf-8"))
            if isinstance(raw_v, dict):
                raw_v = list(raw_v.values())
            if isinstance(raw_v, list):
                sanitized_v = [sanitize_vehicle(v, base_url) for v in raw_v if isinstance(v, dict)]
                vehicles_path.write_text(json.dumps(sanitized_v, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                log.info("Sanitized %d vehicles in %s", len(sanitized_v), vehicles_path)
        except Exception as exc:
            log.error("Failed to process vehicles.json: %s", exc)

    if wheels_path.exists():
        try:
            raw_w = json.loads(wheels_path.read_text(encoding="utf-8"))
            if isinstance(raw_w, dict):
                raw_w = list(raw_w.values())
            if isinstance(raw_w, list):
                sanitized_w = [sanitize_wheel(w) for w in raw_w if isinstance(w, dict)]
                wheels_path.write_text(json.dumps(sanitized_w, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                log.info("Sanitized %d wheels in %s", len(sanitized_w), wheels_path)
        except Exception as exc:
            log.error("Failed to process wheels.json: %s", exc)

    if jobs_path.exists():
        try:
            raw_j = json.loads(jobs_path.read_text(encoding="utf-8"))
            if isinstance(raw_j, list):
                changed = 0
                for job in raw_j:
                    if isinstance(job, dict):
                        # Purge external CDN links or unverified creator profile links
                        thumb = str(job.get("thumbnail") or "")
                        if thumb.startswith(("http://", "https://")) and (not base_url or not thumb.startswith(base_url)):
                            job.pop("thumbnail", None)
                            changed += 1
                        c_url = str(job.get("creator_url") or "")
                        if c_url.startswith(("http://", "https://")) and (not base_url or not c_url.startswith(base_url)):
                            job.pop("creator_url", None)
                            changed += 1
                if changed:
                    jobs_path.write_text(json.dumps(raw_j, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log.info("Sanitized %d references in %s", changed, jobs_path)
        except Exception as exc:
            log.error("Failed to process jobs.json: %s", exc)

    if creators_path.exists():
        try:
            raw_c = json.loads(creators_path.read_text(encoding="utf-8"))
            if isinstance(raw_c, list):
                changed = 0
                for creator in raw_c:
                    if isinstance(creator, dict):
                        cr_url = str(creator.get("url") or "")
                        if cr_url.startswith(("http://", "https://")) and (not base_url or not cr_url.startswith(base_url)):
                            creator.pop("url", None)
                            changed += 1
                if changed:
                    creators_path.write_text(json.dumps(raw_c, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                    log.info("Sanitized %d references in %s", changed, creators_path)
        except Exception as exc:
            log.error("Failed to process creators.json: %s", exc)


def main() -> None:
    parser = argparse.ArgumentParser(description="GTA V HUB Catalogue Seeder and Sanitizer")
    parser.add_argument("--data-dir", default="data", help="Directory containing catalogue JSON files")
    parser.add_argument("--base-url", default=os.getenv("CATALOGUE_API_BASE_URL", ""), help="Base URL for vehicle links")
    args = parser.parse_args()

    process_catalogue(Path(args.data_dir), base_url=args.base_url)


if __name__ == "__main__":
    main()
