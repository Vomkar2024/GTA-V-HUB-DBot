from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed
from gta_hub.cogs.common import show_catalog_results


class Vehicles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    vehicle = app_commands.Group(name="vehicle", description="Search the GTA V HUB vehicle catalog")

    @vehicle.command(name="search", description="Search vehicles by name or manufacturer")
    @app_commands.describe(query="Vehicle name or manufacturer")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("vehicles", query)
        await show_catalog_results(interaction, kind="vehicles", query=query, rows=rows)

    @vehicle.command(name="class", description="Browse vehicles in a class")
    @app_commands.describe(name="Vehicle class, such as Sports or Super")
    async def by_class(self, interaction: discord.Interaction, name: str) -> None:
        rows = [row for row in self.bot.catalog.all("vehicles") if str(row.get("class", "")).casefold() == name.casefold()]
        await show_catalog_results(interaction, kind="vehicles", query=f"class: {name}", rows=rows[:25])

    @vehicle.command(name="tier", description="Filter vehicle class by performance tier")
    @app_commands.describe(class_name="Vehicle class", tier="Tier label used in your catalog")
    async def tier(self, interaction: discord.Interaction, class_name: str, tier: str) -> None:
        rows = [
            row for row in self.bot.catalog.all("vehicles")
            if str(row.get("class", "")).casefold() == class_name.casefold()
            and str(row.get("tier", "")).casefold() == tier.casefold()
        ]
        await show_catalog_results(interaction, kind="vehicles", query=f"{class_name} • tier {tier}", rows=rows[:25])


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vehicles(bot))
