from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

if "aiosqlite" not in sys.modules:
    sys.modules["aiosqlite"] = MagicMock()

import discord
from bot import GtaHubBot
from gta_hub.cogs.admin import AdminSecret, HubAdmin
from gta_hub.config import Settings
from gta_hub.views import (
    ADMIN_PANEL_TEXT,
    HELP_SECTIONS,
    AdminPanelView,
    HelpSelect,
    make_admin_panel_embed,
)


def run_coro(coro):
    while True:
        try:
            coro.send(None)
        except StopIteration as exc:
            return exc.value


class AdminPanelHelpTests(unittest.TestCase):
    def test_links_and_help_does_not_contain_admin_commands(self) -> None:
        links_help = HELP_SECTIONS.get("Links & Help", "")
        self.assertNotIn("/hubadmin", links_help)
        self.assertNotIn("reload-catalogs", links_help)
        self.assertNotIn("sync-catalogs", links_help)
        self.assertIn("/help", links_help)
        self.assertIn("/ping", links_help)

    def test_admin_panel_text_contains_all_admin_privileges(self) -> None:
        self.assertIn("/hubadmin status", ADMIN_PANEL_TEXT)
        self.assertIn("/hubadmin reload-catalogs", ADMIN_PANEL_TEXT)
        self.assertIn("/hubadmin sync", ADMIN_PANEL_TEXT)
        self.assertIn("/hubadmin sync-catalogs", ADMIN_PANEL_TEXT)
        self.assertIn("/hubadmin add-vehicle", ADMIN_PANEL_TEXT)
        self.assertIn("/9575", ADMIN_PANEL_TEXT)

    def test_make_admin_panel_embed(self) -> None:
        embed = make_admin_panel_embed()
        self.assertIn("Admin Control Panel", embed.title)
        self.assertIn("OWNER_IDS", embed.description)

    def test_help_select_does_not_leak_admin_panel(self) -> None:
        select = HelpSelect()
        option_values = [opt.value for opt in select.options]
        self.assertNotIn("Admin", option_values)
        self.assertNotIn("hubadmin", option_values)


class AdminPanelViewInteractionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.settings.owner_ids = frozenset({12345})
        self.bot.catalog.counts.return_value = {"vehicles": 10, "wheels": 5}
        self.bot.guilds = [MagicMock(), MagicMock()]
        self.bot.latency = 0.045
        self.bot.catalog_sync.history.return_value = []

    def test_interaction_check_rejects_non_owner(self) -> None:
        view = AdminPanelView(self.bot)
        interaction = MagicMock()
        interaction.user.id = 99999
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()

        allowed = run_coro(view.interaction_check(interaction))
        self.assertFalse(allowed)
        interaction.response.send_message.assert_called_once()
        self.assertIn("not authorized", interaction.response.send_message.call_args[0][0])

    def test_interaction_check_allows_owner(self) -> None:
        view = AdminPanelView(self.bot)
        interaction = MagicMock()
        interaction.user.id = 12345
        allowed = run_coro(view.interaction_check(interaction))
        self.assertTrue(allowed)

    def test_status_button_action(self) -> None:
        view = AdminPanelView(self.bot)
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()

        run_coro(view.status_button.callback(interaction))
        interaction.response.send_message.assert_called_once()
        embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(embed)
        self.assertIn("Runtime Status", embed.title)

    def test_reload_button_action(self) -> None:
        view = AdminPanelView(self.bot)
        interaction = MagicMock()
        interaction.response.send_message = AsyncMock()

        run_coro(view.reload_button.callback(interaction))
        self.bot.catalog.load_all.assert_called_once()
        interaction.response.send_message.assert_called_once()
        embed = interaction.response.send_message.call_args[1].get("embed")
        self.assertIsNotNone(embed)
        self.assertIn("Catalogs Reloaded", embed.title)


class SecretAdminCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bot = MagicMock()
        self.bot.settings.owner_ids = frozenset({12345})
        self.admin_secret = AdminSecret(self.bot)
        self.hub_admin = HubAdmin(self.bot)

    def test_secret_9575_rejected_for_non_owner(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 99999
        interaction.response.send_message = AsyncMock()

        run_coro(self.admin_secret.secret_admin_panel.callback(self.admin_secret, interaction))
        interaction.response.send_message.assert_called_once()
        self.assertIn("not authorized", interaction.response.send_message.call_args[0][0])

    def test_secret_9575_allowed_for_owner(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.response.send_message = AsyncMock()

        run_coro(self.admin_secret.secret_admin_panel.callback(self.admin_secret, interaction))
        interaction.response.send_message.assert_called_once()
        call_kwargs = interaction.response.send_message.call_args[1]
        self.assertIn("embed", call_kwargs)
        self.assertIn("view", call_kwargs)
        self.assertIn("Admin Control Panel", call_kwargs["embed"].title)

    def test_hubadmin_panel_command(self) -> None:
        interaction = MagicMock()
        interaction.user.id = 12345
        interaction.response.send_message = AsyncMock()

        run_coro(self.hub_admin.admin_panel.callback(self.hub_admin, interaction))
        interaction.response.send_message.assert_called_once()
        call_kwargs = interaction.response.send_message.call_args[1]
        self.assertIn("Admin Control Panel", call_kwargs["embed"].title)

    def test_on_secret_message_for_owner(self) -> None:
        message = MagicMock()
        message.author.bot = False
        message.author.id = 12345
        message.content = "/9575"
        message.delete = AsyncMock()
        message.channel.send = AsyncMock()

        run_coro(self.admin_secret.on_secret_message(message))
        message.delete.assert_called_once()
        message.channel.send.assert_called_once()

    def test_on_secret_message_ignored_for_non_owner(self) -> None:
        message = MagicMock()
        message.author.bot = False
        message.author.id = 88888
        message.content = "/9575"
        message.delete = AsyncMock()
        message.channel.send = AsyncMock()

        run_coro(self.admin_secret.on_secret_message(message))
        message.delete.assert_not_called()
        message.channel.send.assert_not_called()


class BotAdminBypassTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            token="test_token",
            guild_id=None,
            owner_ids=frozenset({12345}),
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

    def test_9575_bypasses_channel_restrictions_for_owner(self) -> None:
        interaction = MagicMock()
        interaction.channel_id = 999999999  # Restricted channel
        interaction.channel.parent_id = None
        interaction.user.id = 12345  # Owner
        interaction.command.name = "9575"
        interaction.command.root_parent = None
        interaction.command.parent = None
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()

        result = run_coro(self.bot.check_interaction_allowed(interaction))
        self.assertTrue(result)
        interaction.response.send_message.assert_not_called()

    def test_9575_fails_channel_check_for_non_owner(self) -> None:
        interaction = MagicMock()
        interaction.channel_id = 999999999  # Restricted channel
        interaction.channel.parent_id = None
        interaction.user.id = 55555  # Non-owner
        interaction.command.name = "9575"
        interaction.command.root_parent = None
        interaction.command.parent = None
        interaction.response.is_done.return_value = False
        interaction.response.send_message = AsyncMock()

        result = run_coro(self.bot.check_interaction_allowed(interaction))
        self.assertFalse(result)
        interaction.response.send_message.assert_called_once()


if __name__ == "__main__":
    unittest.main()
