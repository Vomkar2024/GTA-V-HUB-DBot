from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from gta_hub.catalog import CatalogError, CatalogStore


class CatalogStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        for name in ("vehicles", "wheels", "jobs", "creators"):
            (self.data_dir / f"{name}.json").write_text("[]", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_missing_catalogs_are_created_and_loaded(self) -> None:
        store = CatalogStore(self.data_dir)
        store.load_all()
        self.assertEqual(store.counts(), {"vehicles": 0, "wheels": 0, "jobs": 0, "creators": 0})

    def test_exact_and_partial_search(self) -> None:
        rows = [
            {"name": "Comet S2", "manufacturer": "Pfister"},
            {"name": "Sultan RS", "manufacturer": "Karin"},
        ]
        (self.data_dir / "vehicles.json").write_text(json.dumps(rows), encoding="utf-8")
        store = CatalogStore(self.data_dir)
        store.load_all()
        self.assertEqual(store.search("vehicles", "comet s2")[0]["name"], "Comet S2")
        self.assertEqual(store.search("vehicles", "Pfister")[0]["name"], "Comet S2")

    def test_empty_query_returns_no_results(self) -> None:
        store = CatalogStore(self.data_dir)
        store.load_all()
        self.assertEqual(store.search("vehicles", "  "), [])

    def test_invalid_catalog_shape_is_rejected(self) -> None:
        (self.data_dir / "vehicles.json").write_text('"not a list"', encoding="utf-8")
        store = CatalogStore(self.data_dir)
        with self.assertRaises(CatalogError):
            store.load_all()

    def test_add_persists_manual_catalog_entry(self) -> None:
        store = CatalogStore(self.data_dir)
        store.load_all()
        store.add("vehicles", {"name": "Comet S2", "manufacturer": "Pfister"})
        self.assertEqual(store.search("vehicles", "Comet S2")[0]["name"], "Comet S2")
        with self.assertRaises(ValueError):
            store.add("vehicles", {"name": "Comet S2", "manufacturer": "Pfister"})

    def test_all_and_counts(self) -> None:
        store = CatalogStore(self.data_dir)
        store.load_all()
        self.assertEqual(store.count("vehicles"), 0)
        self.assertEqual(len(store.all("vehicles")), 0)
        with self.assertRaises(KeyError):
            store.all("unknown_catalog")


if __name__ == "__main__":
    unittest.main()
