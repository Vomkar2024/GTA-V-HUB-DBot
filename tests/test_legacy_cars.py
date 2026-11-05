from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from gta_hub.cogs.legacy import LegacyCommands


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class LegacyCarsCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.gta = MagicMock()
        self.cog = LegacyCommands(self.bot)

    def test_group_has_expected_subcommands(self) -> None:
        commands_dict = {cmd.name: cmd for cmd in self.cog.cars.commands}
        self.assertIn("name", commands_dict)
        self.assertIn("manufacturer", commands_dict)
        self.assertIn("class", commands_dict)

    def test_name_subcommand_description_and_autocomplete(self) -> None:
        cmd = next(c for c in self.cog.cars.commands if c.name == "name")
        param = cmd.parameters[0]
        self.assertEqual(param.name, "query")
        self.assertEqual(param.description, "Vehicle name")
        self.assertTrue(param.autocomplete)

    def test_cars_name_defers_and_searches(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_name.return_value = [
            {"name": "Benefactor Krieger", "manufacturer": "Benefactor", "class": "Super"}
        ]
        self.bot.gta.vehicle_list_embed.return_value = discord.Embed(title="Test")

        run_coro(self.cog.cars_name.callback(self.cog, interaction, "Krieger"))

        interaction.response.defer.assert_called_once_with(ephemeral=True)
        self.bot.gta.search_vehicles_by_name.assert_called_once_with("Krieger")
        interaction.followup.send.assert_called_once()
        for f in interaction.followup.send.call_args.kwargs.get("files", []):
            f.close()

    def test_cars_manufacturer_defers_and_searches(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_manufacturer.return_value = [
            {"name": "Benefactor Krieger", "manufacturer": "Benefactor", "class": "Super"}
        ]
        self.bot.gta.vehicle_list_embed.return_value = discord.Embed(title="Test")

        run_coro(self.cog.cars_manufacturer.callback(self.cog, interaction, "Benefactor"))

        interaction.response.defer.assert_called_once_with(ephemeral=True)
        self.bot.gta.search_vehicles_by_manufacturer.assert_called_once_with("Benefactor")
        interaction.followup.send.assert_called_once()
        for f in interaction.followup.send.call_args.kwargs.get("files", []):
            f.close()

    def test_cars_class_defers_and_searches(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_class.return_value = [
            {"name": "Benefactor Krieger", "manufacturer": "Benefactor", "class": "Super"}
        ]
        self.bot.gta.vehicle_list_embed.return_value = discord.Embed(title="Test")

        run_coro(self.cog.cars_class.callback(self.cog, interaction, "Super"))

        interaction.response.defer.assert_called_once_with(ephemeral=True)
        self.bot.gta.search_vehicles_by_class.assert_called_once_with("Super")
        interaction.followup.send.assert_called_once()
        for f in interaction.followup.send.call_args.kwargs.get("files", []):
            f.close()

    def test_autocomplete_handlers(self) -> None:
        interaction = MagicMock()
        self.bot.gta.autocomplete_vehicle_names.return_value = ["Benefactor Krieger"]
        self.bot.gta.autocomplete_manufacturers.return_value = ["Benefactor"]
        self.bot.gta.autocomplete_classes.return_value = ["Super"]

        choices_name = run_coro(self.cog.cars_name_autocomplete(interaction, "Krieg"))
        self.assertEqual(len(choices_name), 1)
        self.assertEqual(choices_name[0].name, "Benefactor Krieger")

        choices_mfg = run_coro(self.cog.cars_manufacturer_autocomplete(interaction, "Bene"))
        self.assertEqual(len(choices_mfg), 1)
        self.assertEqual(choices_mfg[0].name, "Benefactor")

        choices_cls = run_coro(self.cog.cars_class_autocomplete(interaction, "Sup"))
        self.assertEqual(len(choices_cls), 1)
        self.assertEqual(choices_cls[0].name, "Super")

    def test_cars_name_attaches_vehicle_image_and_catalog_view(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_name.return_value = [
            {"id": "krieger", "name": "Krieger", "manufacturer": "Benefactor", "class": "Super"},
            {"id": "benefactor-krieger", "name": "Benefactor Krieger", "manufacturer": "Benefactor", "class": "Super"},
        ]
        self.bot.gta.vehicle_list_embed.return_value = discord.Embed(title="GTA Online Vehicles")

        run_coro(self.cog.cars_name.callback(self.cog, interaction, "Krieger"))

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args.kwargs
        self.assertIn("embed", call_kwargs)
        self.assertIn("files", call_kwargs)
        self.assertIn("view", call_kwargs)

        files = call_kwargs["files"]
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].filename, "krieger.png")
        files[0].close()

    def test_cars_name_single_match_omits_dropdown_view(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_name.return_value = [
            {"id": "krieger", "name": "Krieger", "manufacturer": "Benefactor", "class": "Super"},
        ]
        self.bot.gta.vehicle_list_embed.return_value = discord.Embed(title="GTA Online Vehicles")

        run_coro(self.cog.cars_name.callback(self.cog, interaction, "Krieger"))

        interaction.followup.send.assert_called_once()
        call_kwargs = interaction.followup.send.call_args.kwargs
        self.assertIn("embed", call_kwargs)
        self.assertIn("files", call_kwargs)
        self.assertIsNone(call_kwargs.get("view"))
        if call_kwargs.get("files"):
            call_kwargs["files"][0].close()

    def test_cars_name_empty_results_sends_not_found(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        self.bot.gta.search_vehicles_by_name.return_value = []

        run_coro(self.cog.cars_name.callback(self.cog, interaction, "NonExistentVehicleXYZ"))

        interaction.followup.send.assert_called_once()
        args = interaction.followup.send.call_args[0]
        self.assertIn("No matching vehicles found", args[0])


if __name__ == "__main__":
    unittest.main()

