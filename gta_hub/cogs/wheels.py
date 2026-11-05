from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.cogs.common import show_catalog_results


class Wheels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    wheel = app_commands.Group(name="wheel", description="Search the GTA V HUB wheel catalog")

    @wheel.command(name="search", description="Search wheels by name")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("wheels", query)
        await show_catalog_results(interaction, kind="wheels", query=query, rows=rows)

    @wheel.command(name="type", description="List wheels of a selected type")
    async def by_type(self, interaction: discord.Interaction, name: str) -> None:
        rows = [row for row in self.bot.catalog.all("wheels") if str(row.get("type", "")).casefold() == name.casefold()]
        await show_catalog_results(interaction, kind="wheels", query=f"type: {name}", rows=rows[:25])

    @wheel.command(name="effects", description="Filter wheels by handling effects")
    @app_commands.describe(
        wheel_type="Optional wheel type",
        traction_bias="Optional traction bias (front or rear)",
        anti_roll="Optional anti-roll sign (+ or -)",
        slip_angle="Optional slip-angle sign (+ or -)",
    )
    async def effects(
        self,
        interaction: discord.Interaction,
        wheel_type: str | None = None,
        traction_bias: str | None = None,
        anti_roll: str | None = None,
        slip_angle: str | None = None,
    ) -> None:
        filters = {
            "type": wheel_type,
            "traction_bias": traction_bias,
            "anti_roll": anti_roll,
            "slip_angle": slip_angle,
        }
        active = {key: value.casefold() for key, value in filters.items() if value}
        if not active:
            await interaction.response.send_message("Add at least one filter to search wheel effects.", ephemeral=True)
            return
        rows = [
            row for row in self.bot.catalog.all("wheels")
            if all(str(row.get(key, "")).casefold() == value for key, value in active.items())
        ]
        label = ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in active.items())
        await show_catalog_results(interaction, kind="wheels", query=label, rows=rows[:25])


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wheels(bot))
