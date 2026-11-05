from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gta_hub.services.catalog_sync import _write_catalog, normalize_vehicle, normalize_wheels


class CatalogSyncTests(unittest.TestCase):
    def test_vehicle_normalization(self) -> None:
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
        self.assertEqual(row["url"], "https://gtacars.net/gta5/comet-s2")
        self.assertIsNone(normalize_vehicle({"_name": ""}))
        self.assertIsNone(normalize_vehicle({}))

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

    def test_wheel_normalization_invalid_payload(self) -> None:
        with self.assertRaises(ValueError):
            normalize_wheels(["not", "a", "dict"])

    def test_sync_replaces_provider_rows_but_preserves_local_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vehicles.json"
            path.write_text(
                json.dumps([
                    {"name": "Old imported", "manufacturer": "Test", "_catalog_source": "gtacars"},
                    {"name": "My manual entry", "manufacturer": "Custom"},
                ]),
                encoding="utf-8",
            )
            count = _write_catalog(
                path,
                [{"name": "New imported", "manufacturer": "Test", "_catalog_source": "gtacars"}],
                "gtacars",
                ("manufacturer", "name"),
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(count, 1)
            self.assertEqual([row["name"] for row in data], ["My manual entry", "New imported"])


if __name__ == "__main__":
    unittest.main()

