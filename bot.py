from __future__ import annotations

import argparse
import asyncio
import logging
import sys

import discord
from discord.ext import commands

try:
    from discord import app_commands
except ImportError:  # pragma: no cover
    app_commands = None  # type: ignore

from gta_hub.branding import make_embed
from gta_hub.catalog import CatalogStore
from gta_hub.config import Settings
from gta_hub.database import Database
from gta_hub.services.catalog_sync import CatalogSyncService
from gta_hub.services.gta import GTAService

EXTENSIONS = (
    "gta_hub.cogs.general",
    "gta_hub.cogs.community",
    "gta_hub.cogs.vehicles",
    "gta_hub.cogs.wheels",
    "gta_hub.cogs.jobs",
    "gta_hub.cogs.weather",
    "gta_hub.cogs.admin",
    "gta_hub.cogs.legacy",
)


if app_commands is not None:
    class ChannelRestrictedError(app_commands.CheckFailure):
        """Raised when an interaction occurs in a disallowed channel."""
else:  # pragma: no cover
    class ChannelRestrictedError(Exception):  # type: ignore
        pass


class GtaHubBot(commands.Bot):
    _hub_settings: Settings

    @property
    def settings(self) -> Settings:
        return self._hub_settings

    @settings.setter
    def settings(self, value: Settings) -> None:
        self._hub_settings = value

    def __init__(self, settings: Settings):
        if hasattr(discord, "Intents"):
            intents = discord.Intents.default()
            super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)
        else:  # pragma: no cover
            super().__init__(command_prefix=commands.when_mentioned, help_command=None)
        self.settings = settings
        self.catalog = CatalogStore(settings.data_dir)
        self.db = Database(str(settings.database_path))
        self.gta = GTAService(settings.data_dir / "vehicles.json")
        self.catalog_sync = CatalogSyncService(
            settings.data_dir, base_url=settings.catalogue_api_base_url
        )

    def is_channel_allowed(self, channel_id: int | None, parent_id: int | None = None) -> bool:
        if not self.settings.allowed_channel_ids:
            return True
        if channel_id is not None and channel_id in self.settings.allowed_channel_ids:
            return True
        if parent_id is not None and parent_id in self.settings.allowed_channel_ids:
            return True
        return False

    def _is_owner_admin_command(self, interaction: discord.Interaction) -> bool:
        if not self.settings.owner_ids or interaction.user.id not in self.settings.owner_ids:
            return False
        cmd = interaction.command
        if not cmd:
            return False
        root_name = getattr(getattr(cmd, "root_parent", None), "name", None)
        parent_name = getattr(getattr(cmd, "parent", None), "name", None)
        cmd_name = getattr(cmd, "name", "")
        return (root_name or parent_name or cmd_name) in ("hubadmin", "admin", "hub9575")

    async def check_interaction_allowed(self, interaction: discord.Interaction) -> bool:
        if self._is_owner_admin_command(interaction):
            return True

        parent_id = getattr(interaction.channel, "parent_id", None)
        if not self.is_channel_allowed(interaction.channel_id, parent_id):
            channels_mention = ", ".join(f"<#{cid}>" for cid in sorted(self.settings.allowed_channel_ids))
            embed = make_embed(
                "Channel Restricted",
                f"GTA V HUB commands can only be used in {channels_mention}."
            )
            if hasattr(interaction, "response") and hasattr(interaction.response, "is_done"):
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True

    async def setup_hook(self) -> None:
        self.catalog.load_all()
        await self.db.initialize()

        if hasattr(self, "tree") and self.tree is not None:
            self.tree.interaction_check = self.check_interaction_allowed

            if app_commands is not None:
                @self.tree.error
                async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
                    if isinstance(error, ChannelRestrictedError):
                        if not interaction.response.is_done():
                            channels_mention = ", ".join(f"<#{cid}>" for cid in sorted(self.settings.allowed_channel_ids))
                            embed = make_embed(
                                "Channel Restricted",
                                f"GTA V HUB commands can only be used in {channels_mention}."
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    if isinstance(error, app_commands.CheckFailure):
                        if not interaction.response.is_done():
                            channels_mention = ", ".join(f"<#{cid}>" for cid in sorted(self.settings.allowed_channel_ids))
                            embed = make_embed(
                                "Channel Restricted",
                                f"GTA V HUB commands can only be used in {channels_mention}."
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                    logging.getLogger("gta_v_hub").error("Unhandled command error: %s", error, exc_info=error)

        @self.check
        async def global_prefix_check(ctx: commands.Context) -> bool:
            parent_id = getattr(ctx.channel, "parent_id", None)
            return self.is_channel_allowed(ctx.channel.id, parent_id)

        for extension in EXTENSIONS:
            if extension == "gta_hub.cogs.legacy" and not self.settings.enable_legacy_commands:
                continue
            await self.load_extension(extension)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logging.getLogger("gta_v_hub").info(
                "Synced %d command(s) to guild %s", len(synced), self.settings.guild_id
            )
            if self.settings.clear_global_on_startup:
                self.tree.clear_commands(guild=None)
                await self.tree.sync()
                logging.getLogger("gta_v_hub").info(
                    "Cleared all global commands to prevent duplicates in guilds."
                )
        else:
            synced = await self.tree.sync()
            logging.getLogger("gta_v_hub").info("Synced %d global command(s)", len(synced))

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        if self.user:
            focused = (
                ", ".join(str(cid) for cid in sorted(self.settings.allowed_channel_ids))
                if self.settings.allowed_channel_ids
                else "all channels"
            )
            logging.getLogger("gta_v_hub").info(
                "Connected as %s (%s). Channel focus: %s", self.user, self.user.id, focused
            )


class _VoiceWarningFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return "voice will NOT be supported" not in record.getMessage()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="GTA V HUB Discord Bot")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--clear-global",
        action="store_true",
        help="Clear all global application commands from Discord (resolves duplicate commands in servers).",
    )
    group.add_argument(
        "--clear-guild",
        action="store_true",
        help="Clear application commands registered to the GUILD_ID specified in .env.",
    )
    group.add_argument(
        "--sync-only",
        action="store_true",
        help="Sync application commands and exit without starting the gateway connection.",
    )
    return parser.parse_args(argv)


async def _execute_cli_action(settings: Settings, action: str) -> None:
    bot = GtaHubBot(settings)
    async with bot:
        await bot.login(settings.token)
        if action == "clear-global":
            bot.tree.clear_commands(guild=None)
            synced = await bot.tree.sync()
            logging.getLogger("gta_v_hub").info(
                "Successfully cleared global commands (%d remaining). Duplicate commands should now disappear from your guild.",
                len(synced),
            )
        elif action == "clear-guild":
            if not settings.guild_id:
                logging.getLogger("gta_v_hub").error("GUILD_ID is not configured in .env.")
                return
            guild = discord.Object(id=settings.guild_id)
            bot.tree.clear_commands(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logging.getLogger("gta_v_hub").info(
                "Successfully cleared commands for guild %s (%d remaining).",
                settings.guild_id,
                len(synced),
            )
        elif action == "sync-only":
            bot.catalog.load_all()
            for extension in EXTENSIONS:
                if extension == "gta_hub.cogs.legacy" and not settings.enable_legacy_commands:
                    continue
                await bot.load_extension(extension)
            if settings.guild_id:
                guild = discord.Object(id=settings.guild_id)
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)
                logging.getLogger("gta_v_hub").info("Synced %d command(s) to guild %s.", len(synced), settings.guild_id)
                if settings.clear_global_on_startup:
                    bot.tree.clear_commands(guild=None)
                    await bot.tree.sync()
                    logging.getLogger("gta_v_hub").info("Cleared global commands.")
            else:
                synced = await bot.tree.sync()
                logging.getLogger("gta_v_hub").info("Synced %d global command(s).", len(synced))


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = Settings.from_env()
    if not settings.token or settings.token == "replace_with_your_bot_token":
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and set your bot token.")

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logging.getLogger("discord.client").addFilter(_VoiceWarningFilter())

    action = None
    if args.clear_global:
        action = "clear-global"
    elif args.clear_guild:
        action = "clear-guild"
    elif args.sync_only:
        action = "sync-only"

    if action:
        try:
            asyncio.run(_execute_cli_action(settings, action))
        except discord.LoginFailure:
            logging.getLogger("gta_v_hub").critical("Discord rejected the bot token. Check DISCORD_TOKEN.")
            sys.exit(1)
        return

    bot = GtaHubBot(settings)
    try:
        bot.run(settings.token, log_handler=None)
    except discord.LoginFailure:
        logging.getLogger("gta_v_hub").critical("Discord rejected the bot token. Check DISCORD_TOKEN.")
        sys.exit(1)


if __name__ == "__main__":
    main()
