from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from gta_hub.services.catalog_sync import (
    CatalogueSyncError,
    CatalogSyncService,
    _write_catalog,
    normalize_vehicle,
    normalize_wheels,
)


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class CatalogSyncTests(unittest.TestCase):
    def test_vehicle_normalization_default_base(self) -> None:
        row = normalize_vehicle({
            "id": "comet-s2",
            "_name": "Comet S2",
            "_manuf": "pfister",
            "_class": "sport",
            "_priceMp": 1.9,
            "_dt": "rwd",
            "_lapTime": 62000,
            "_topSpeed": 123.0,
            "_seats": 2,
            "_description": "A sports car.",
        })
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["name"], "Comet S2")
        self.assertEqual(row["manufacturer"], "Pfister")
        self.assertEqual(row["class"], "Sports")
        self.assertEqual(row["price"], 1900)
        self.assertEqual(row["lap_time"], 62.0)
        self.assertEqual(row["top_speed"], 123.0)
        self.assertEqual(row["seats"], 2)
        self.assertEqual(row["drivetrain"], "RWD")
        self.assertEqual(row["url"], "/vehicles/comet-s2")
        self.assertEqual(row["_catalog_source"], "first-party")
        self.assertIsNone(normalize_vehicle({"_name": ""}))
        self.assertIsNone(normalize_vehicle({}))

    def test_vehicle_normalization_with_base_url(self) -> None:
        row = normalize_vehicle(
            {
                "id": "banshee",
                "name": "Banshee",
                "manufacturer": "Bravado",
                "class": "Sports",
                "price": 105000,
            },
            base_url="https://catalogue.example.com",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row["url"], "https://catalogue.example.com/vehicles/banshee")
        self.assertEqual(row["_catalog_source"], "first-party")

    def test_wheel_normalization(self) -> None:
        rows = normalize_wheels({
            "Wheel A (Sport)": {
                "name": "Wheel A",
                "wheel_type": "Sport",
                "price": 5000,
                "suggested_state": "Stock",
                "wheel_effects": {"bias": "rear", "anti_roll": "+", "slip_angle": "-", "note": "Great grip"},
            }
        })
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Wheel A")
        self.assertEqual(rows[0]["type"], "Sport")
        self.assertEqual(rows[0]["price"], 5000)
        self.assertEqual(rows[0]["traction_bias"], "rear")
        self.assertEqual(rows[0]["anti_roll"], "+")
        self.assertEqual(rows[0]["slip_angle"], "-")
        self.assertEqual(rows[0]["description"], "Great grip")
        self.assertEqual(rows[0]["_catalog_source"], "first-party")

    def test_wheel_normalization_invalid_payload(self) -> None:
        with self.assertRaises(ValueError):
            normalize_wheels("invalid string payload")

    def test_sync_replaces_provider_rows_but_preserves_local_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vehicles.json"
            path.write_text(
                json.dumps([
                    {"name": "Old imported", "manufacturer": "Test", "_catalog_source": "first-party"},
                    {"name": "My manual entry", "manufacturer": "Custom"},
                ]),
                encoding="utf-8",
            )
            count = _write_catalog(
                path,
                [{"name": "New imported", "manufacturer": "Test", "_catalog_source": "first-party"}],
                "first-party",
                ("manufacturer", "name"),
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(count, 1)
            self.assertEqual([row["name"] for row in data], ["My manual entry", "New imported"])

    def test_sync_service_endpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            service = CatalogSyncService(Path(temp), base_url="https://catalogue.example.internal")
            self.assertEqual(service.base_url, "https://catalogue.example.internal")
            self.assertIn("/api/?game=gta5&page=1", service.vehicle_endpoint(1))
            self.assertEqual(service.wheels_endpoint(), "https://catalogue.example.internal/api/wheels")

    def test_sync_retains_local_files_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp)
            vehicles_file = data_dir / "vehicles.json"
            initial_data = [{"name": "Existing Car", "manufacturer": "Test", "_catalog_source": "manual"}]
            vehicles_file.write_text(json.dumps(initial_data), encoding="utf-8")

            service = CatalogSyncService(data_dir, base_url="https://invalid.unreachable.endpoint")

            with patch("aiohttp.ClientSession") as mock_session_cls:
                mock_ctx = AsyncMock()
                mock_session_cls.return_value.__aenter__.return_value = mock_ctx
                with patch("gta_hub.services.catalog_sync._fetch_json", side_effect=Exception("Connection refused")):
                    with self.assertRaises(CatalogueSyncError):
                        run_coro(service.sync_vehicles())

            # Verify local file retained intact
            retained = json.loads(vehicles_file.read_text(encoding="utf-8"))
            self.assertEqual(retained, initial_data)


if __name__ == "__main__":
    unittest.main()
