from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gta_hub.services.gta import GTAService


class GTAServiceTests(unittest.TestCase):
    def test_search_supports_both_class_field_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vehicles.json"
            path.write_text(json.dumps([
                {"name": "Comet S2", "manufacturer": "Pfister", "class": "Sports"},
                {"name": "Zentorno", "manufacturer": "Pegassi", "vehicle_class": "Super"},
            ]), encoding="utf-8")
            service = GTAService(path)
            match1 = service.find_vehicle("sports")
            self.assertIsNotNone(match1)
            assert match1 is not None
            self.assertEqual(match1["name"], "Comet S2")

            match2 = service.find_vehicle("super")
            self.assertIsNotNone(match2)
            assert match2 is not None
            self.assertEqual(match2["name"], "Zentorno")

    def test_missing_catalog_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            service = GTAService(Path(temp) / "missing.json")
            self.assertEqual(service.search_vehicles("anything"), [])

    def test_reload_vehicles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vehicles.json"
            path.write_text("[]", encoding="utf-8")
            service = GTAService(path)
            self.assertEqual(len(service.vehicles), 0)

            path.write_text(json.dumps([{"name": "Banshee", "manufacturer": "Bravado"}]), encoding="utf-8")
            count = service.reload_vehicles()
            self.assertEqual(count, 1)
            self.assertEqual(service.vehicles[0]["name"], "Banshee")

    def test_value_alias_and_formatting(self) -> None:
        data = {
            "name": "Krieger",
            "price": 2875000,
            "category": "Super",
            "max_speed": 127.25,
        }
        self.assertEqual(GTAService.value(data, "cost"), "$2,875,000")
        self.assertEqual(GTAService.value(data, "vehicle_class"), "Super")
        self.assertEqual(GTAService.value(data, "top_speed_mph"), "127.25")
        self.assertEqual(GTAService.value(data, "nonexistent"), "Not available")


if __name__ == "__main__":
    unittest.main()
