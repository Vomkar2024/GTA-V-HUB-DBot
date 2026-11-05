from __future__ import annotations

import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

if "aiosqlite" not in sys.modules:
    sys.modules["aiosqlite"] = MagicMock()

from gta_hub.config import Settings
from bot import GtaHubBot


class ChannelRestrictionTests(unittest.TestCase):
    def test_default_allowed_channel_id(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()
            self.assertIn(1567917854341472387, settings.allowed_channel_ids)
            self.assertEqual(settings.allowed_channel_id, 1567917854341472387)

    def test_custom_single_channel_id(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_CHANNEL_ID": "987654321012345678"}, clear=True):
            settings = Settings.from_env()
            self.assertEqual(settings.allowed_channel_ids, frozenset({987654321012345678}))
            self.assertEqual(settings.allowed_channel_id, 987654321012345678)

    def test_multiple_comma_separated_channel_ids(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_CHANNEL_ID": "1567917854341472387, 987654321012345678"}, clear=True):
            settings = Settings.from_env()
            self.assertEqual(settings.allowed_channel_ids, frozenset({1567917854341472387, 987654321012345678}))

    def test_empty_allowed_channel_disables_restriction(self) -> None:
        with patch.dict(os.environ, {"ALLOWED_CHANNEL_ID": ""}, clear=True):
            settings = Settings.from_env()
            self.assertEqual(settings.allowed_channel_ids, frozenset())
            self.assertIsNone(settings.allowed_channel_id)

    def test_bot_is_channel_allowed_checks(self) -> None:
        settings = Settings(
            token="test_token",
            guild_id=None,
            owner_ids=frozenset(),
            allowed_channel_ids=frozenset({1567917854341472387}),
            invite_url=None,
            support_url=None,
            donate_url=None,
            data_dir=Path("data"),
            database_path=Path("data/gtavhub.sqlite3"),
            weather_api_url=None,
            sync_api_url=None,
            log_level="INFO",
        )
        bot = GtaHubBot(settings)

        # Matching channel
        self.assertTrue(bot.is_channel_allowed(1567917854341472387))

        # Non-matching channel
        self.assertFalse(bot.is_channel_allowed(123456789012345678))

        # Thread inside matching channel
        self.assertTrue(bot.is_channel_allowed(999999999999999999, parent_id=1567917854341472387))

        # Thread inside non-matching channel
        self.assertFalse(bot.is_channel_allowed(999999999999999999, parent_id=123456789012345678))

        # None channel ID
        self.assertFalse(bot.is_channel_allowed(None))

    def test_bot_is_channel_allowed_when_unrestricted(self) -> None:
        settings = Settings(
            token="test_token",
            guild_id=None,
            owner_ids=frozenset(),
            allowed_channel_ids=frozenset(),
            invite_url=None,
            support_url=None,
            donate_url=None,
            data_dir=Path("data"),
            database_path=Path("data/gtavhub.sqlite3"),
            weather_api_url=None,
            sync_api_url=None,
            log_level="INFO",
        )
        bot = GtaHubBot(settings)
        self.assertTrue(bot.is_channel_allowed(1567917854341472387))
        self.assertTrue(bot.is_channel_allowed(123456789012345678))
        self.assertTrue(bot.is_channel_allowed(None))


def run_coro(coro):
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    try:
        coro.send(None)
    except StopIteration as exc:
        return exc.value
    return None


class InteractionCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            token="test_token",
            guild_id=None,
            owner_ids=frozenset({1111}),
            allowed_channel_ids=frozenset({1567917854341472387}),
            invite_url=None,
            support_url=None,
            donate_url=None,
            data_dir=Path("data"),
            database_path=Path("data/gtavhub.sqlite3"),
            weather_api_url=None,
            sync_api_url=None,
            log_level="INFO",
        )
        self.bot = GtaHubBot(self.settings)

    def test_interaction_in_allowed_channel_succeeds(self) -> None:
        interaction = MagicMock()
        interaction.channel_id = 1567917854341472387
        interaction.channel.parent_id = None
        interaction.user.id = 2222
        interaction.command.root_parent = None
        interaction.response.is_done.return_value = False

        sent = []
        async def mock_send(*args, **kwargs):
            sent.append((args, kwargs))
        interaction.response.send_message = mock_send

        result = run_coro(self.bot.check_interaction_allowed(interaction))
        self.assertTrue(result)
        self.assertEqual(len(sent), 0)

    def test_interaction_in_disallowed_channel_rejected(self) -> None:
        interaction = MagicMock()
        interaction.channel_id = 999999999
        interaction.channel.parent_id = None
        interaction.user.id = 2222
        interaction.command.root_parent = None
        interaction.response.is_done.return_value = False

        sent = []
        async def mock_send(*args, **kwargs):
            sent.append((args, kwargs))
        interaction.response.send_message = mock_send

        result = run_coro(self.bot.check_interaction_allowed(interaction))
        self.assertFalse(result)
        self.assertEqual(len(sent), 1)

    def test_owner_admin_command_allowed_in_any_channel(self) -> None:
        interaction = MagicMock()
        interaction.channel_id = 999999999
        interaction.channel.parent_id = None
        interaction.user.id = 1111
        interaction.command.root_parent.name = "hubadmin"
        interaction.response.is_done.return_value = False

        sent = []
        async def mock_send(*args, **kwargs):
            sent.append((args, kwargs))
        interaction.response.send_message = mock_send

        result = run_coro(self.bot.check_interaction_allowed(interaction))
        self.assertTrue(result)
        self.assertEqual(len(sent), 0)


if __name__ == "__main__":
    unittest.main()
