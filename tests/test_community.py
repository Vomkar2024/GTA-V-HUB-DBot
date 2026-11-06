from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock

from discord import app_commands

from gta_hub.cogs.community import Community


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class CommunityCogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.db = MagicMock()
        self.bot.db.set_profile = AsyncMock()
        self.bot.db.get_profile = AsyncMock()
        self.bot.db.get_community_stats = AsyncMock()
        self.bot.db.get_leaderboard = AsyncMock()
        self.cog = Community(self.bot)

    def test_link_validation_rejects_short_name(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.response.send_message = AsyncMock()

        choice = MagicMock(spec=app_commands.Choice)
        choice.value = "PC"

        run_coro(self.cog.link.callback(self.cog, interaction, "a", choice))
        self.bot.db.set_profile.assert_not_called()
        interaction.response.send_message.assert_called_once_with(
            "Rockstar nickname must be 2–32 characters.", ephemeral=True
        )

    def test_link_success(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.response.send_message = AsyncMock()

        choice = MagicMock(spec=app_commands.Choice)
        choice.value = "PlayStation"

        run_coro(self.cog.link.callback(self.cog, interaction, "LosSantosSpeed", choice))
        self.bot.db.set_profile.assert_called_once_with(12345, "LosSantosSpeed", "PlayStation")
        interaction.response.send_message.assert_called_once()
        sent_embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(sent_embed)
        self.assertIn("LosSantosSpeed", sent_embed.description)

    def test_profile_not_linked(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.user.display_name = "PlayerOne"
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_profile.return_value = None

        run_coro(self.cog.profile.callback(self.cog, interaction, member=None))
        interaction.response.send_message.assert_called_once()
        self.assertIn("has no linked community profile yet", interaction.response.send_message.call_args[0][0])

    def test_profile_found(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.user.display_name = "PlayerOne"
        interaction.user.display_avatar.url = "https://example.com/avatar.png"
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_profile.return_value = ("LosSantosSpeed", "PC")

        run_coro(self.cog.profile.callback(self.cog, interaction, member=None))
        interaction.response.send_message.assert_called_once()
        sent_embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(sent_embed)
        field_values = [f.value for f in sent_embed.fields]
        self.assertIn("LosSantosSpeed", field_values)
        self.assertIn("PC", field_values)

    def test_stats_not_found(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.user.display_name = "PlayerOne"
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_community_stats.return_value = None

        run_coro(self.cog.stats.callback(self.cog, interaction, member=None))
        interaction.response.send_message.assert_called_once()
        self.assertIn("has no daily reward history yet", interaction.response.send_message.call_args[0][0])

    def test_stats_found(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.user.display_name = "PlayerOne"
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_community_stats.return_value = {
            "last_claim": "2026-11-05",
            "streak": 5,
            "total_credits": 1250,
            "claim_count": 8,
        }

        run_coro(self.cog.stats.callback(self.cog, interaction, member=None))
        interaction.response.send_message.assert_called_once()
        sent_embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(sent_embed)
        field_names = [f.name for f in sent_embed.fields]
        self.assertIn("HUB Credits earned", field_names)
        self.assertIn("Daily claims", field_names)
        self.assertIn("Current streak", field_names)

    def test_leaderboard_empty(self) -> None:
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_leaderboard.return_value = []

        run_coro(self.cog.leaderboard.callback(self.cog, interaction, metric=None))
        interaction.response.send_message.assert_called_once()
        sent_embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(sent_embed)
        self.assertIn("No community activity recorded yet", sent_embed.description)

    def test_leaderboard_with_records(self) -> None:
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()
        self.bot.db.get_leaderboard.return_value = [
            {
                "discord_user_id": "111",
                "streak": 10,
                "total_credits": 3000,
                "claim_count": 15,
                "rockstar_name": "RacerOne",
                "platform": "PC",
            },
            {
                "discord_user_id": "222",
                "streak": 3,
                "total_credits": 800,
                "claim_count": 4,
                "rockstar_name": None,
                "platform": None,
            },
        ]

        choice = MagicMock(spec=app_commands.Choice)
        choice.value = "credits"
        run_coro(self.cog.leaderboard.callback(self.cog, interaction, metric=choice))
        self.bot.db.get_leaderboard.assert_called_once_with(metric="credits", limit=10)
        interaction.response.send_message.assert_called_once()
        sent_embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(sent_embed)
        self.assertIn("🥇", sent_embed.description)
        self.assertIn("<@111>", sent_embed.description)
        self.assertIn("RacerOne", sent_embed.description)
        self.assertIn("3,000", sent_embed.description)
        self.assertIn("<@222>", sent_embed.description)


if __name__ == "__main__":
    unittest.main()
