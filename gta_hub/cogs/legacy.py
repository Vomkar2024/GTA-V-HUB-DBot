from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed
from gta_hub.services.gta import GTAService


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

    @app_commands.command(name="cars", description="Search GTA Online vehicles")
    @app_commands.describe(query="Vehicle name, manufacturer, or class")
    async def cars(self, interaction: discord.Interaction, query: str) -> None:
        matches = self.bot.gta.search_vehicles(query)
        if not matches:
            await interaction.response.send_message(
                "No matching vehicles found. Add permitted entries to data/vehicles.json.",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            embed=self.bot.gta.vehicle_list_embed(matches), ephemeral=True
        )

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
