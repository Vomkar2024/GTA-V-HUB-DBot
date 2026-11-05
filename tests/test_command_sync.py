from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

if "aiosqlite" not in sys.modules:
    sys.modules["aiosqlite"] = MagicMock()

import discord
from bot import GtaHubBot, _execute_cli_action, parse_args
from gta_hub.cogs.admin import HubAdmin
from gta_hub.config import Settings


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


class CommandSyncConfigTests(unittest.TestCase):
    def test_default_config_flags(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()
            self.assertTrue(settings.enable_legacy_commands)
            self.assertFalse(settings.clear_global_on_startup)

    def test_custom_config_flags(self) -> None:
        with patch.dict(
            os.environ,
            {
                "ENABLE_LEGACY_COMMANDS": "false",
                "CLEAR_GLOBAL_ON_STARTUP": "true",
            },
            clear=True,
        ):
            settings = Settings.from_env()
            self.assertFalse(settings.enable_legacy_commands)
            self.assertTrue(settings.clear_global_on_startup)


class CliArgParsingTests(unittest.TestCase):
    def test_default_no_args(self) -> None:
        args = parse_args([])
        self.assertFalse(args.clear_global)
        self.assertFalse(args.clear_guild)
        self.assertFalse(args.sync_only)

    def test_clear_global_arg(self) -> None:
        args = parse_args(["--clear-global"])
        self.assertTrue(args.clear_global)
        self.assertFalse(args.clear_guild)
        self.assertFalse(args.sync_only)

    def test_clear_guild_arg(self) -> None:
        args = parse_args(["--clear-guild"])
        self.assertFalse(args.clear_global)
        self.assertTrue(args.clear_guild)
        self.assertFalse(args.sync_only)

    def test_sync_only_arg(self) -> None:
        args = parse_args(["--sync-only"])
        self.assertFalse(args.clear_global)
        self.assertFalse(args.clear_guild)
        self.assertTrue(args.sync_only)


class SetupHookSyncTests(unittest.TestCase):
    def _create_bot(self, **kwargs) -> GtaHubBot:
        defaults = dict(
            token="test_token",
            guild_id=123456789,
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
            enable_legacy_commands=True,
            clear_global_on_startup=False,
        )
        defaults.update(kwargs)
        settings = Settings(**defaults)
        return GtaHubBot(settings)

    def test_setup_hook_skips_legacy_when_disabled(self) -> None:
        bot = self._create_bot(enable_legacy_commands=False)
        bot.catalog = MagicMock()
        bot.db = MagicMock()
        bot.db.initialize = AsyncMock()
        loaded = []
        bot.load_extension = AsyncMock(side_effect=lambda ext: loaded.append(ext))
        bot.tree.copy_global_to = MagicMock()
        bot.tree.sync = AsyncMock(return_value=[])

        run_coro(bot.setup_hook())
        self.assertNotIn("gta_hub.cogs.legacy", loaded)

    def test_setup_hook_loads_legacy_when_enabled(self) -> None:
        bot = self._create_bot(enable_legacy_commands=True)
        bot.catalog = MagicMock()
        bot.db = MagicMock()
        bot.db.initialize = AsyncMock()
        loaded = []
        bot.load_extension = AsyncMock(side_effect=lambda ext: loaded.append(ext))
        bot.tree.copy_global_to = MagicMock()
        bot.tree.sync = AsyncMock(return_value=[])

        run_coro(bot.setup_hook())
        self.assertIn("gta_hub.cogs.legacy", loaded)

    def test_setup_hook_clears_global_when_configured(self) -> None:
        bot = self._create_bot(clear_global_on_startup=True)
        bot.catalog = MagicMock()
        bot.db = MagicMock()
        bot.db.initialize = AsyncMock()
        bot.load_extension = AsyncMock()
        bot.tree.copy_global_to = MagicMock()
        bot.tree.clear_commands = MagicMock()
        bot.tree.sync = AsyncMock(return_value=[])

        run_coro(bot.setup_hook())
        bot.tree.clear_commands.assert_called_with(guild=None)
        self.assertEqual(bot.tree.sync.call_count, 2)


class HubAdminSyncCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.tree = MagicMock()
        self.bot.tree.sync = AsyncMock(return_value=[MagicMock(), MagicMock()])
        self.cog = HubAdmin(self.bot)

    def test_sync_clear_global(self) -> None:
        interaction = MagicMock()
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        mode_choice = MagicMock()
        mode_choice.value = "clear-global"

        run_coro(self.cog.sync_commands.callback(self.cog, interaction, mode_choice))
        self.bot.tree.clear_commands.assert_called_with(guild=None)
        self.bot.tree.sync.assert_called_once()
        interaction.followup.send.assert_called_once()

    def test_sync_guild(self) -> None:
        interaction = MagicMock()
        interaction.guild = discord.Object(id=999)
        interaction.guild.name = "Test Guild"
        interaction.response.defer = AsyncMock()
        interaction.followup.send = AsyncMock()

        mode_choice = MagicMock()
        mode_choice.value = "guild"

        run_coro(self.cog.sync_commands.callback(self.cog, interaction, mode_choice))
        self.bot.tree.copy_global_to.assert_called_once_with(guild=interaction.guild)
        self.bot.tree.sync.assert_called_once_with(guild=interaction.guild)
        interaction.followup.send.assert_called_once()


class ExecuteCliActionTests(unittest.TestCase):
    @patch("bot.GtaHubBot")
    def test_execute_cli_action_clear_global(self, mock_bot_cls: MagicMock) -> None:
        mock_bot = MagicMock()
        mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
        mock_bot.__aexit__ = AsyncMock(return_value=None)
        mock_bot.login = AsyncMock()
        mock_bot.tree.sync = AsyncMock(return_value=[])
        mock_bot_cls.return_value = mock_bot

        settings = Settings(
            token="test_token",
            guild_id=123,
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

        run_coro(_execute_cli_action(settings, "clear-global"))
        mock_bot.login.assert_called_once_with("test_token")
        mock_bot.tree.clear_commands.assert_called_once_with(guild=None)
        mock_bot.tree.sync.assert_called_once()


if __name__ == "__main__":
    unittest.main()
