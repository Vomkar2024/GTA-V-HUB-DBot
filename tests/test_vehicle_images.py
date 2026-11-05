from __future__ import annotations

from pathlib import Path
from typing import Any
import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from gta_hub.cogs.common import show_catalog_results
from gta_hub.views import (
    CatalogSelect,
    build_entry_embed_and_file,
    entry_embed,
    resolve_vehicle_image,
)


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class VehicleImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sample_vehicle = {
            "id": "airbus",
            "name": "Airport Bus",
            "manufacturer": "Unknown",
            "class": "Service",
            "price": 550000,
            "drivetrain": "AWD",
            "model": "airbus",
            "top_speed": 65.0,
            "lap_time": 117.427,
            "images": ["images/d3192937d4d50ddec8587e36526f0811"],
            "image_source_refs": ["images/d3192937d4d50ddec8587e36526f0811"],
        }

    def test_entry_embed_never_shows_image_reference_field(self) -> None:
        embed = entry_embed("vehicles", self.sample_vehicle)
        field_names = [f.name for f in embed.fields]
        self.assertNotIn("Image Reference", field_names)
        self.assertNotIn("image reference", [name.lower() for name in field_names])

    def test_resolve_vehicle_image_matches_known_asset(self) -> None:
        image_path = resolve_vehicle_image(self.sample_vehicle)
        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.is_file())
        self.assertEqual(image_path.name.lower(), "airbus.png")

    def test_resolve_vehicle_image_with_clean_name(self) -> None:
        vehicle = {
            "id": "albany-alpha",
            "name": "Albany Alpha",
            "manufacturer": "Albany",
            "model": "alpha",
        }
        image_path = resolve_vehicle_image(vehicle)
        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.is_file())
        self.assertEqual(image_path.name.lower(), "alpha.png")

    def test_resolve_vehicle_image_with_roman_numerals(self) -> None:
        vehicle = {
            "id": "gallivanter-baller-ii",
            "name": "Gallivanter Baller II",
            "manufacturer": "Gallivanter",
        }
        image_path = resolve_vehicle_image(vehicle)
        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.is_file())
        self.assertEqual(image_path.name.lower(), "baller2.png")

    def test_resolve_vehicle_image_with_parenthetical_trim(self) -> None:
        vehicle = {
            "id": "western-daemon-custom",
            "name": "Western Daemon (Custom)",
            "manufacturer": "Western",
        }
        image_path = resolve_vehicle_image(vehicle)
        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.is_file())
        self.assertEqual(image_path.name.lower(), "daemon.png")

    def test_resolve_vehicle_image_with_direct_image_url(self) -> None:
        vehicle = {
            "id": "unknown-slug-xyz",
            "name": "Custom Vehicle",
            "image_url": "/images/adder.png",
        }
        image_path = resolve_vehicle_image(vehicle)
        self.assertIsNotNone(image_path)
        self.assertTrue(image_path.is_file())
        self.assertEqual(image_path.name.lower(), "adder.png")

    def test_build_entry_embed_and_file_attaches_image(self) -> None:
        embed, file = build_entry_embed_and_file("vehicles", self.sample_vehicle)
        self.assertIsNotNone(file)
        self.assertIsInstance(file, discord.File)
        self.assertEqual(file.filename, "airbus.png")
        self.assertEqual(embed.image.url, "attachment://airbus.png")
        self.assertNotIn("Image Reference", [f.name for f in embed.fields])
        file.close()

    def test_entry_embed_with_valid_image_url(self) -> None:
        vehicle = dict(self.sample_vehicle)
        vehicle["image_url"] = "https://cdn.example.com/vehicles/airbus.png"
        embed = entry_embed("vehicles", vehicle)
        self.assertEqual(embed.image.url, "https://cdn.example.com/vehicles/airbus.png")

    def test_catalog_select_callback_attaches_file(self) -> None:
        rows = [self.sample_vehicle]
        select = CatalogSelect(rows, kind="vehicles")
        select._values = ["0"]

        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_response = MagicMock()
        mock_response.edit_message = AsyncMock()
        mock_interaction.response = mock_response

        run_coro(select.callback(mock_interaction))

        mock_response.edit_message.assert_awaited_once()
        call_kwargs = mock_response.edit_message.await_args.kwargs
        self.assertIn("embed", call_kwargs)
        self.assertIn("attachments", call_kwargs)
        attachments = call_kwargs["attachments"]
        self.assertEqual(len(attachments), 1)
        self.assertIsInstance(attachments[0], discord.File)
        self.assertEqual(attachments[0].filename, "airbus.png")
        self.assertEqual(call_kwargs["embed"].image.url, "attachment://airbus.png")
        attachments[0].close()

    def test_show_catalog_results_single_match_sends_file_directly(self) -> None:
        mock_interaction = MagicMock(spec=discord.Interaction)
        mock_response = MagicMock()
        mock_response.send_message = AsyncMock()
        mock_interaction.response = mock_response

        run_coro(
            show_catalog_results(
                mock_interaction,
                kind="vehicles",
                query="airbus",
                rows=[self.sample_vehicle],
            )
        )

        mock_response.send_message.assert_awaited_once()
        call_kwargs = mock_response.send_message.await_args.kwargs
        self.assertIn("embed", call_kwargs)
        self.assertIn("files", call_kwargs)
        files = call_kwargs["files"]
        self.assertEqual(len(files), 1)
        self.assertIsInstance(files[0], discord.File)
        self.assertEqual(files[0].filename, "airbus.png")
        self.assertEqual(call_kwargs["embed"].image.url, "attachment://airbus.png")
        files[0].close()


if __name__ == "__main__":
    unittest.main()
