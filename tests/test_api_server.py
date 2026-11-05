from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from aiohttp.test_utils import make_mocked_request

from gta_hub.api.server import (
    CatalogueApiController,
    create_app,
    format_vehicle_for_api,
    format_wheels_for_api,
)


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class ApiServerUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

        self.sample_vehicles = [
            {
                "id": "comet-s2",
                "name": "Comet S2",
                "manufacturer": "Pfister",
                "class": "Sports",
                "price": 1900000,
                "drivetrain": "RWD",
                "model": "comet6",
                "top_speed": 123.0,
                "lap_time": 62.0,
            },
            {
                "id": "zentorno",
                "name": "Zentorno",
                "manufacturer": "Pegassi",
                "class": "Super",
                "price": 725000,
                "drivetrain": "AWD",
                "model": "zentorno",
                "top_speed": 122.0,
                "lap_time": 63.5,
            },
            {
                "id": "krieger",
                "name": "Krieger",
                "manufacturer": "Benefactor",
                "class": "Super",
                "price": 2875000,
                "drivetrain": "AWD",
                "model": "krieger",
                "top_speed": 127.25,
                "lap_time": 58.5,
            },
        ]
        (self.data_dir / "vehicles.json").write_text(json.dumps(self.sample_vehicles), encoding="utf-8")

        self.sample_wheels = [
            {
                "name": "Shadow",
                "type": "High End",
                "price": 8780,
                "suggested": "Stock",
                "traction_bias": "rear",
                "anti_roll": "+",
                "slip_angle": "-",
                "description": "Clean rim",
            }
        ]
        (self.data_dir / "wheels.json").write_text(json.dumps(self.sample_wheels), encoding="utf-8")

        self.controller = CatalogueApiController(self.data_dir, base_url="http://127.0.0.1:8080")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_format_vehicle_for_api_mirrors_and_normalizes(self) -> None:
        formatted = format_vehicle_for_api(self.sample_vehicles[0], base_url="https://catalogue.example.com")
        # Check consumer mirror fields
        self.assertEqual(formatted["id"], "comet-s2")
        self.assertEqual(formatted["_name"], "Comet S2")
        self.assertEqual(formatted["_manuf"], "pfister")
        self.assertEqual(formatted["_class"], "sports")
        self.assertEqual(formatted["_priceMp"], 1900.0)
        self.assertEqual(formatted["_dt"], "rwd")
        # Check first-party normalized fields
        self.assertEqual(formatted["name"], "Comet S2")
        self.assertEqual(formatted["price"], 1900000)
        self.assertEqual(formatted["url"], "https://catalogue.example.com/vehicles/comet-s2")
        self.assertEqual(formatted["_catalog_source"], "first-party")

    def test_format_wheels_for_api(self) -> None:
        formatted = format_wheels_for_api(self.sample_wheels)
        self.assertIn("Shadow (High End)", formatted)
        wheel = formatted["Shadow (High End)"]
        self.assertEqual(wheel["name"], "Shadow")
        self.assertEqual(wheel["price"], 8780)
        self.assertEqual(wheel["wheel_effects"]["bias"], "rear")

    def test_handle_status(self) -> None:
        req = make_mocked_request("GET", "/api/status")
        resp = run_coro(self.controller.handle_status(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["records"]["vehicles"], 3)
        self.assertEqual(data["records"]["wheels"], 1)

    def test_handle_vehicles_pagination(self) -> None:
        req = make_mocked_request("GET", "/api/vehicles?page=1&perPage=2")
        resp = run_coro(self.controller.handle_vehicles(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        self.assertTrue(data["status"])
        payload = data["payload"]
        self.assertEqual(payload["total"], 3)
        self.assertEqual(len(payload["vehicles"]), 2)
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["totalPages"], 2)

    def test_handle_vehicles_root_endpoint_compatibility(self) -> None:
        req = make_mocked_request("GET", "/api/?game=gta5&page=1&perPage=60&sort=alphabet&sortReverse=false&q=")
        resp = run_coro(self.controller.handle_vehicles(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        self.assertTrue(data["status"])
        payload = data["payload"]
        self.assertEqual(len(payload["vehicles"]), 3)
        self.assertEqual(payload["vehicles"][0]["_catalog_source"], "first-party")

    def test_handle_vehicles_query_filtering(self) -> None:
        req = make_mocked_request("GET", "/api/vehicles?q=krieger")
        resp = run_coro(self.controller.handle_vehicles(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        vehicles = data["payload"]["vehicles"]
        self.assertEqual(len(vehicles), 1)
        self.assertEqual(vehicles[0]["name"], "Krieger")

    def test_handle_vehicles_sorting_by_price_reverse(self) -> None:
        req = make_mocked_request("GET", "/api/vehicles?sort=price&sortReverse=true")
        resp = run_coro(self.controller.handle_vehicles(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        vehicles = data["payload"]["vehicles"]
        self.assertEqual(vehicles[0]["name"], "Krieger")  # Highest price
        self.assertEqual(vehicles[-1]["name"], "Zentorno")  # Lowest price

    def test_handle_vehicle_detail(self) -> None:
        req_found = make_mocked_request("GET", "/api/vehicles/comet-s2", match_info={"id": "comet-s2"})
        resp_found = run_coro(self.controller.handle_vehicle_detail(req_found))
        self.assertEqual(resp_found.status, 200)
        data = json.loads(resp_found.text)
        self.assertTrue(data["status"])
        self.assertEqual(data["payload"]["name"], "Comet S2")

        req_not_found = make_mocked_request("GET", "/api/vehicles/nonexistent", match_info={"id": "nonexistent"})
        resp_not_found = run_coro(self.controller.handle_vehicle_detail(req_not_found))
        self.assertEqual(resp_not_found.status, 404)

    def test_handle_wheels(self) -> None:
        req = make_mocked_request("GET", "/api/wheels")
        resp = run_coro(self.controller.handle_wheels(req))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.text)
        self.assertIn("Shadow (High End)", data)

    def test_create_app_routes(self) -> None:
        app = create_app(data_dir=self.data_dir, base_url="http://127.0.0.1:8080")
        routes = [route.resource.canonical for route in app.router.routes()]
        self.assertIn("/images", routes)
        self.assertIn("/api", routes)
        self.assertIn("/api/vehicles", routes)
        self.assertIn("/api/wheels", routes)
        self.assertIn("/api/status", routes)


if __name__ == "__main__":
    unittest.main()
