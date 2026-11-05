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

    def test_categorical_search_and_autocomplete(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "vehicles.json"
            path.write_text(json.dumps([
                {"name": "Benefactor Krieger", "manufacturer": "Benefactor", "class": "Super"},
                {"name": "Benefactor Feltzer", "manufacturer": "Benefactor", "class": "Sports"},
                {"name": "Pegassi Zentorno", "manufacturer": "Pegassi", "vehicle_class": "Super"},
                {"name": "Pfister Comet S2", "manufacturer": "Pfister", "vehicle_class": "Sports"},
            ]), encoding="utf-8")
            service = GTAService(path)

            # Name search only matches name
            name_matches = service.search_vehicles_by_name("Krieger")
            self.assertEqual(len(name_matches), 1)
            self.assertEqual(name_matches[0]["name"], "Benefactor Krieger")
            # Searching for manufacturer in name returns nothing
            self.assertEqual(len(service.search_vehicles_by_name("Pegassi")), 1)  # Name is "Pegassi Zentorno"
            self.assertEqual(len(service.search_vehicles_by_name("Pfister")), 1)  # Name is "Pfister Comet S2"
            self.assertEqual(len(service.search_vehicles_by_name("Super")), 0)  # Class is Super, not in name

            # Manufacturer search
            mfg_matches = service.search_vehicles_by_manufacturer("Benefactor")
            self.assertEqual(len(mfg_matches), 2)
            self.assertEqual(len(service.search_vehicles_by_manufacturer("Pfister")), 1)
            self.assertEqual(len(service.search_vehicles_by_manufacturer("Krieger")), 0)

            # Class search
            class_matches = service.search_vehicles_by_class("Super")
            self.assertEqual(len(class_matches), 2)
            self.assertEqual(len(service.search_vehicles_by_class("Sports")), 2)
            self.assertEqual(len(service.search_vehicles_by_class("Benefactor")), 0)

            # Autocomplete helpers
            name_choices = service.autocomplete_vehicle_names("bene")
            self.assertIn("Benefactor Krieger", name_choices)
            self.assertIn("Benefactor Feltzer", name_choices)
            self.assertEqual(len(name_choices), 2)

            mfg_choices = service.autocomplete_manufacturers("be")
            self.assertEqual(mfg_choices, ["Benefactor"])

            class_choices = service.autocomplete_classes("sp")
            self.assertEqual(class_choices, ["Sports"])


if __name__ == "__main__":
    unittest.main()
