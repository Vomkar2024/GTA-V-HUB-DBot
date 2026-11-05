from __future__ import annotations

import logging
import sys

import discord
from discord.ext import commands

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
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.settings = settings
        self.catalog = CatalogStore(settings.data_dir)
        self.db = Database(str(settings.database_path))
        self.gta = GTAService(settings.data_dir / "vehicles.json")

    async def setup_hook(self) -> None:
        self.catalog.load_all()
        await self.db.initialize()
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
            logging.getLogger("gta_v_hub").info("Connected as %s (%s)", self.user, self.user.id)


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
