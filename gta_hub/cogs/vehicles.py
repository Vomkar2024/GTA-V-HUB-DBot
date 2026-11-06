from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.cogs.common import show_catalog_results


def _matches_class(row_class: str, target: str) -> bool:
    cf_target = target.casefold().strip()
    cf_row = row_class.casefold().strip()
    if not cf_target or not cf_row:
        return False
    if cf_row == cf_target:
        return True
    if cf_row.rstrip("s") == cf_target.rstrip("s"):
        return True
    parts = [p.strip() for p in cf_row.split(",")]
    if any(p == cf_target or p.rstrip("s") == cf_target.rstrip("s") for p in parts):
        return True
    return cf_target in cf_row


class Vehicles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    vehicle = app_commands.Group(name="vehicle", description="Search the GTA V HUB vehicle catalog")

    @vehicle.command(name="search", description="Search vehicles by name or manufacturer")
    @app_commands.describe(query="Vehicle name or manufacturer")
    async def search(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("vehicles", query)
        await show_catalog_results(interaction, kind="vehicles", query=query, rows=rows)

    @search.autocomplete("query")
    async def search_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "autocomplete_vehicle_names"):
            choices = self.bot.gta.autocomplete_vehicle_names(current)
            return [app_commands.Choice(name=name[:100], value=name[:100]) for name in choices[:25]]
        rows = self.bot.catalog.search("vehicles", current, limit=25)
        names = [str(r.get("name") or "") for r in rows if r.get("name")]
        return [app_commands.Choice(name=name[:100], value=name[:100]) for name in names[:25]]

    @vehicle.command(name="class", description="Browse vehicles in a class")
    @app_commands.describe(name="Vehicle class, such as Sports or Super")
    async def by_class(self, interaction: discord.Interaction, name: str) -> None:
        rows = [
            row for row in self.bot.catalog.all("vehicles")
            if _matches_class(str(row.get("class") or row.get("vehicle_class") or ""), name)
        ]
        await show_catalog_results(interaction, kind="vehicles", query=f"class: {name}", rows=rows[:25])

    @by_class.autocomplete("name")
    async def by_class_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "autocomplete_classes"):
            classes = self.bot.gta.autocomplete_classes(current)
            return [app_commands.Choice(name=cls[:100], value=cls[:100]) for cls in classes[:25]]
        all_vehicles = self.bot.catalog.all("vehicles")
        raw_classes = {str(r.get("class") or r.get("vehicle_class") or "").strip() for r in all_vehicles}
        filtered = [c for c in sorted(raw_classes) if c and current.casefold() in c.casefold()]
        return [app_commands.Choice(name=c[:100], value=c[:100]) for c in filtered[:25]]

    @vehicle.command(name="tier", description="Filter vehicle class by performance tier")
    @app_commands.describe(class_name="Vehicle class", tier="Tier label (e.g. S, A, B, C, D)")
    async def tier(self, interaction: discord.Interaction, class_name: str, tier: str) -> None:
        tier_val = str(getattr(tier, "value", tier)).strip()
        rows = [
            row for row in self.bot.catalog.all("vehicles")
            if _matches_class(str(row.get("class") or row.get("vehicle_class") or ""), class_name)
            and str(row.get("tier", "")).casefold() == tier_val.casefold()
        ]
        await show_catalog_results(interaction, kind="vehicles", query=f"{class_name} • tier {tier_val}", rows=rows[:25])

    @tier.autocomplete("class_name")
    async def tier_class_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        return await self.by_class_autocomplete(interaction, current)

    @tier.autocomplete("tier")
    async def tier_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        tiers = ["S", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K"]
        clean = current.strip().upper()
        matches = [t for t in tiers if not clean or clean in t]
        return [app_commands.Choice(name=f"{t} Tier", value=t) for t in matches[:25]]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Vehicles(bot))
