from __future__ import annotations

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
from gta_hub.services.gta import GTAService

EXTENSIONS = (
    "gta_hub.cogs.general",
    "gta_hub.cogs.vehicles",
    "gta_hub.cogs.wheels",
    "gta_hub.cogs.jobs",
    "gta_hub.cogs.weather",
    "gta_hub.cogs.admin",
    "gta_hub.cogs.legacy",
)


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
            super().__init__(command_prefix="!", intents=intents, help_command=None)
        else:  # pragma: no cover
            super().__init__(command_prefix="!", help_command=None)
        self.settings = settings
        self.catalog = CatalogStore(settings.data_dir)
        self.db = Database(str(settings.database_path))
        self.gta = GTAService(settings.data_dir / "vehicles.json")

    def is_channel_allowed(self, channel_id: int | None, parent_id: int | None = None) -> bool:
        if not self.settings.allowed_channel_ids:
            return True
        if channel_id is not None and channel_id in self.settings.allowed_channel_ids:
            return True
        if parent_id is not None and parent_id in self.settings.allowed_channel_ids:
            return True
        return False

    async def check_interaction_allowed(self, interaction: discord.Interaction) -> bool:
        if (
            self.settings.owner_ids
            and interaction.user.id in self.settings.owner_ids
            and interaction.command
            and getattr(interaction.command, "root_parent", None) is not None
            and interaction.command.root_parent.name == "hubadmin"
        ):
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
            @self.tree.interaction_check
            async def global_interaction_check(interaction: discord.Interaction) -> bool:
                return await self.check_interaction_allowed(interaction)

            if app_commands is not None:
                @self.tree.error
                async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
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
            await self.load_extension(extension)

        if self.settings.guild_id:
            guild = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            logging.getLogger("gta_v_hub").info("Synced %d command(s) to guild %s", len(synced), self.settings.guild_id)
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


def main() -> None:
    settings = Settings.from_env()
    if not settings.token or settings.token == "replace_with_your_bot_token":
        raise SystemExit("DISCORD_TOKEN is missing. Copy .env.example to .env and set your bot token.")

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    bot = GtaHubBot(settings)
    try:
        bot.run(settings.token, log_handler=None)
    except discord.LoginFailure:
        logging.getLogger("gta_v_hub").critical("Discord rejected the bot token. Check DISCORD_TOKEN.")
        sys.exit(1)


if __name__ == "__main__":
    main()
