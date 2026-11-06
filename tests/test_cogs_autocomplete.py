from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

import discord

from gta_hub.cogs.jobs import Jobs
from gta_hub.cogs.legacy import LegacyCommands
from gta_hub.cogs.vehicles import Vehicles
from gta_hub.cogs.wheels import Wheels


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class CogsAutocompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.catalog = MagicMock()
        self.bot.db = MagicMock()
        self.bot.gta = MagicMock()

    def test_vehicles_autocomplete(self) -> None:
        cog = Vehicles(self.bot)
        self.bot.gta.autocomplete_vehicle_names.return_value = ["Emerus", "Entity MT"]
        self.bot.gta.autocomplete_classes.return_value = ["Super", "Sports"]

        interaction = MagicMock(spec=discord.Interaction)

        # /vehicle search query
        res_search = run_coro(cog.search_autocomplete(interaction, "em"))
        self.assertEqual(len(res_search), 2)
        self.assertEqual(res_search[0].name, "Emerus")

        # /vehicle class name
        res_class = run_coro(cog.by_class_autocomplete(interaction, "su"))
        self.assertEqual(len(res_class), 2)
        self.assertEqual(res_class[0].name, "Super")

        # /vehicle tier
        res_tier = run_coro(cog.tier_autocomplete(interaction, "S"))
        self.assertEqual(len(res_tier), 1)
        self.assertEqual(res_tier[0].value, "S")

    def test_wheels_autocomplete(self) -> None:
        cog = Wheels(self.bot)
        self.bot.catalog.search.return_value = [{"name": "Fujiwara", "type": "Tuner"}]

        interaction = MagicMock(spec=discord.Interaction)

        # /wheel search query
        res_search = run_coro(cog.search_autocomplete(interaction, "fuji"))
        self.assertEqual(len(res_search), 1)
        self.assertEqual(res_search[0].name, "Fujiwara")

        # /wheel type name
        res_type = run_coro(cog.by_type_autocomplete(interaction, "tun"))
        self.assertTrue(any(c.name == "Tuners" for c in res_type))

    def test_jobs_autocomplete(self) -> None:
        cog = Jobs(self.bot)
        self.bot.catalog.search.side_effect = lambda kind, q, limit=25: [
            {"name": "Wallride Mania"} if kind == "jobs" else {"name": "Broughy1322"}
        ]

        interaction = MagicMock(spec=discord.Interaction)

        # /job search query
        res_job = run_coro(cog.search_job_autocomplete(interaction, "wall"))
        self.assertEqual(len(res_job), 1)
        self.assertEqual(res_job[0].name, "Wallride Mania")

        # /creator search query
        res_creator = run_coro(cog.search_creator_autocomplete(interaction, "brough"))
        self.assertEqual(len(res_creator), 1)
        self.assertEqual(res_creator[0].name, "Broughy1322")

    def test_legacy_compare_and_garage_autocomplete(self) -> None:
        cog = LegacyCommands(self.bot)
        self.bot.gta.autocomplete_vehicle_names.return_value = ["Krieger", "Karin Previon"]
        self.bot.db.get_garage = AsyncMock(return_value=[("Emerus", "2026-11-06"), ("Krieger", "2026-11-06")])

        interaction = MagicMock(spec=discord.Interaction)
        interaction.user.id = 12345

        # Compare autocomplete
        res_compare = run_coro(cog.compare_autocomplete(interaction, "kri"))
        self.assertEqual(len(res_compare), 2)
        self.assertEqual(res_compare[0].name, "Krieger")

        # Garage autocomplete for "add"
        interaction.namespace.action = "add"
        res_garage_add = run_coro(cog.garage_vehicle_autocomplete(interaction, "kri"))
        self.assertEqual(len(res_garage_add), 2)
        self.assertEqual(res_garage_add[0].name, "Krieger")

        # Garage autocomplete for "remove" (pulls from user's garage)
        interaction.namespace.action = "remove"
        res_garage_remove = run_coro(cog.garage_vehicle_autocomplete(interaction, "eme"))
        self.assertEqual(len(res_garage_remove), 1)
        self.assertEqual(res_garage_remove[0].name, "Emerus")


if __name__ == "__main__":
    unittest.main()

