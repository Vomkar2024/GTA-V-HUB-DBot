from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.cogs.common import show_catalog_results

WHEEL_TYPES = [
    "Benny's Bespoke",
    "Benny's Originals",
    "High End",
    "Lowrider",
    "Muscle",
    "Offroad",
    "SUV's",
    "Sport",
    "Street",
    "Track",
    "Tuners",
]


class Wheels(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    wheel = app_commands.Group(name="wheel", description="Search the GTA V HUB wheel catalog")

    @wheel.command(name="search", description="Search wheels by name")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("wheels", query)
        await show_catalog_results(interaction, kind="wheels", query=query, rows=rows)

    @search.autocomplete("query")
    async def search_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        rows = self.bot.catalog.search("wheels", current, limit=25)
        names = [str(r.get("name") or "") for r in rows if r.get("name")]
        return [app_commands.Choice(name=name[:100], value=name[:100]) for name in names[:25]]

    @wheel.command(name="type", description="List wheels of a selected type")
    async def by_type(self, interaction: discord.Interaction, name: str) -> None:
        clean_name = name.casefold().replace("’", "'")
        rows = [
            row for row in self.bot.catalog.all("wheels")
            if str(row.get("type", "")).casefold().replace("’", "'") == clean_name
        ]
        await show_catalog_results(interaction, kind="wheels", query=f"type: {name}", rows=rows[:25])

    @by_type.autocomplete("name")
    async def by_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        clean = current.casefold().replace("’", "'")
        matches = [wt for wt in WHEEL_TYPES if not clean or clean in wt.casefold().replace("’", "'")]
        return [app_commands.Choice(name=wt[:100], value=wt[:100]) for wt in matches[:25]]

    @wheel.command(name="effects", description="Filter wheels by handling effects")
    @app_commands.describe(
        wheel_type="Optional wheel type",
        traction_bias="Optional traction bias (front or rear)",
        anti_roll="Optional anti-roll sign (+ or -)",
        slip_angle="Optional slip-angle sign (+ or -)",
    )
    @app_commands.choices(
        traction_bias=[
            app_commands.Choice(name="Front Bias", value="front"),
            app_commands.Choice(name="Rear Bias", value="rear"),
        ],
        anti_roll=[
            app_commands.Choice(name="+ (Stiffer)", value="+"),
            app_commands.Choice(name="- (Softer)", value="-"),
        ],
        slip_angle=[
            app_commands.Choice(name="+ (Higher)", value="+"),
            app_commands.Choice(name="- (Lower)", value="-"),
        ],
    )
    async def effects(
        self,
        interaction: discord.Interaction,
        wheel_type: str | None = None,
        traction_bias: app_commands.Choice[str] | None = None,
        anti_roll: app_commands.Choice[str] | None = None,
        slip_angle: app_commands.Choice[str] | None = None,
    ) -> None:
        tb_val = traction_bias.value if isinstance(traction_bias, app_commands.Choice) else traction_bias
        ar_val = anti_roll.value if isinstance(anti_roll, app_commands.Choice) else anti_roll
        sa_val = slip_angle.value if isinstance(slip_angle, app_commands.Choice) else slip_angle

        filters = {
            "type": wheel_type,
            "traction_bias": tb_val,
            "anti_roll": ar_val,
            "slip_angle": sa_val,
        }
        active = {key: str(value).casefold().replace("’", "'") for key, value in filters.items() if value}
        if not active:
            await interaction.response.send_message("Add at least one filter to search wheel effects.", ephemeral=True)
            return
        rows = [
            row for row in self.bot.catalog.all("wheels")
            if all(str(row.get(key, "")).casefold().replace("’", "'") == value for key, value in active.items())
        ]
        label = ", ".join(f"{key.replace('_', ' ')}={value}" for key, value in active.items())
        await show_catalog_results(interaction, kind="wheels", query=label, rows=rows[:25])

    @effects.autocomplete("wheel_type")
    async def effects_wheel_type_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.by_type_autocomplete(interaction, current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Wheels(bot))
