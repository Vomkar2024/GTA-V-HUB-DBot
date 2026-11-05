from __future__ import annotations

from pathlib import Path
from typing import Any

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed
from gta_hub.services.gta import GTAService
from gta_hub.views import CatalogResultsView, resolve_vehicle_image


class LegacyCommands(commands.Cog):
    """Commands retained from the starter implementation."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="profile", description="View a GTA Online player profile")
    @app_commands.describe(player="Rockstar Social Club username or Rockstar ID")
    async def profile(self, interaction: discord.Interaction, player: str) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await self.bot.gta.player_profile(player)
        await interaction.followup.send(embed=self.bot.gta.profile_embed(result), ephemeral=True)

    @app_commands.command(name="stats", description="View GTA Online player statistics")
    @app_commands.describe(player="Rockstar Social Club username or Rockstar ID")
    async def stats(self, interaction: discord.Interaction, player: str) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await self.bot.gta.player_stats(player)
        await interaction.followup.send(embed=self.bot.gta.stats_embed(result), ephemeral=True)

    cars = app_commands.Group(name="cars", description="Search GTA Online vehicles by category")

    async def _send_vehicle_results(
        self,
        interaction: discord.Interaction,
        matches: list[dict[str, Any]],
        not_found_message: str,
    ) -> None:
        if not matches:
            await interaction.followup.send(not_found_message, ephemeral=True)
            return

        file: discord.File | None = None
        attachment_filename: str | None = None
        for v in matches:
            image_path = resolve_vehicle_image(v)
            if image_path and image_path.is_file():
                attachment_filename = image_path.name
                file = discord.File(fp=str(image_path), filename=attachment_filename)
                break

        try:
            embed = self.bot.gta.vehicle_list_embed(matches, attachment_filename=attachment_filename)
        except TypeError:
            embed = self.bot.gta.vehicle_list_embed(matches)
            if attachment_filename:
                embed.set_image(url=f"attachment://{attachment_filename}")

        files = [file] if file is not None else []
        view = CatalogResultsView(matches, kind="vehicles")
        await interaction.followup.send(embed=embed, files=files, view=view, ephemeral=True)

    @cars.command(name="name", description="Search vehicles by vehicle name")
    @app_commands.describe(query="Vehicle name")
    async def cars_name(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(ephemeral=True)
        matches = self.bot.gta.search_vehicles_by_name(query)
        await self._send_vehicle_results(
            interaction,
            matches,
            "No matching vehicles found for that name. Add permitted entries to data/vehicles.json.",
        )

    @cars_name.autocomplete("query")
    async def cars_name_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = self.bot.gta.autocomplete_vehicle_names(current)
        return [app_commands.Choice(name=name[:100], value=name[:100]) for name in choices[:25]]

    @cars.command(name="manufacturer", description="Search vehicles by manufacturer")
    @app_commands.describe(query="Manufacturer name")
    async def cars_manufacturer(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(ephemeral=True)
        matches = self.bot.gta.search_vehicles_by_manufacturer(query)
        await self._send_vehicle_results(
            interaction,
            matches,
            "No matching vehicles found for that manufacturer. Add permitted entries to data/vehicles.json.",
        )

    @cars_manufacturer.autocomplete("query")
    async def cars_manufacturer_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = self.bot.gta.autocomplete_manufacturers(current)
        return [app_commands.Choice(name=make[:100], value=make[:100]) for make in choices[:25]]

    @cars.command(name="class", description="Search vehicles by vehicle class")
    @app_commands.describe(query="Vehicle class")
    async def cars_class(self, interaction: discord.Interaction, query: str) -> None:
        await interaction.response.defer(ephemeral=True)
        matches = self.bot.gta.search_vehicles_by_class(query)
        await self._send_vehicle_results(
            interaction,
            matches,
            "No matching vehicles found for that class. Add permitted entries to data/vehicles.json.",
        )

    @cars_class.autocomplete("query")
    async def cars_class_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        choices = self.bot.gta.autocomplete_classes(current)
        return [app_commands.Choice(name=cls[:100], value=cls[:100]) for cls in choices[:25]]

    @app_commands.command(name="garage", description="Manage your personal vehicle collection")
    @app_commands.describe(action="What to do", vehicle="Vehicle name for add/remove")
    @app_commands.choices(action=[
        app_commands.Choice(name="View garage", value="view"),
        app_commands.Choice(name="Add vehicle", value="add"),
        app_commands.Choice(name="Remove vehicle", value="remove"),
    ])
    async def garage(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str],
        vehicle: str = "",
    ) -> None:
        if action.value == "view":
            rows = await self.bot.db.get_garage(interaction.user.id)
            await interaction.response.send_message(
                embed=self.bot.gta.garage_embed(rows, interaction.user), ephemeral=True
            )
            return
        if not vehicle.strip():
            await interaction.response.send_message(
                "Provide a vehicle name for this action.", ephemeral=True
            )
            return
        if action.value == "add":
            match = self.bot.gta.find_vehicle(vehicle)
            if not match:
                await interaction.response.send_message(
                    "Vehicle not found. Check names with /cars.", ephemeral=True
                )
                return
            await self.bot.db.add_garage(interaction.user.id, match["name"])
            await interaction.response.send_message(
                f"Added **{match['name']}** to your garage.", ephemeral=True
            )
            return
        removed = await self.bot.db.remove_garage(interaction.user.id, vehicle)
        await interaction.response.send_message(
            "Vehicle removed." if removed else "That vehicle isn't in your garage.",
            ephemeral=True,
        )

    @app_commands.command(name="compare", description="Compare two GTA Online vehicles")
    @app_commands.describe(vehicle_one="First vehicle", vehicle_two="Second vehicle")
    async def compare(
        self, interaction: discord.Interaction, vehicle_one: str, vehicle_two: str
    ) -> None:
        first = self.bot.gta.find_vehicle(vehicle_one)
        second = self.bot.gta.find_vehicle(vehicle_two)
        if not first or not second:
            await interaction.response.send_message(
                "Couldn't find both vehicles. Check names with /cars.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=self.bot.gta.compare_embed(first, second), ephemeral=True
        )

    @app_commands.command(name="crew", description="Look up a Rockstar Social Club crew by crew ID")
    @app_commands.describe(crew_id="Rockstar Social Club crew ID")
    async def crew(self, interaction: discord.Interaction, crew_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await self.bot.gta.crew_info(crew_id)
        await interaction.followup.send(embed=self.bot.gta.crew_embed(result), ephemeral=True)

    @app_commands.command(name="jobs", description="Look up GTA Online races/jobs by creator Rockstar ID")
    @app_commands.describe(creator_id="Creator's Rockstar Social Club ID")
    async def jobs(self, interaction: discord.Interaction, creator_id: str) -> None:
        await interaction.response.defer(ephemeral=True)
        result = await self.bot.gta.jobs_by_creator(creator_id)
        await interaction.followup.send(embed=self.bot.gta.jobs_embed(result), ephemeral=True)

    @app_commands.command(name="daily", description="Claim your daily GTA V HUB community reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        result = await self.bot.db.claim_daily(interaction.user.id)
        if result["claimed"]:
            message = (
                f"Daily reward claimed: **{result['reward']} HUB credits**. "
                f"Streak: **{result['streak']} day(s)**."
            )
        else:
            message = (
                "You've already claimed today's reward. "
                f"Next claim in approximately **{result['hours_left']} hour(s)**."
            )
        await interaction.response.send_message(message, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LegacyCommands(bot))
