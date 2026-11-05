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
            self.assertEqual(service.find_vehicle("sports")["name"], "Comet S2")
            self.assertEqual(service.find_vehicle("super")["name"], "Zentorno")

    def test_missing_catalog_is_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            service = GTAService(Path(temp) / "missing.json")
            self.assertEqual(service.search_vehicles("anything"), [])


if __name__ == "__main__":
    unittest.main()
