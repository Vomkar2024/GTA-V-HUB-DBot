from __future__ import annotations

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed, truncate


class Weather(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    weather = app_commands.Group(name="weather", description="GTA Online weather and time")

    @weather.command(name="current", description="Get current GTA weather from your configured provider")
    async def current(self, interaction: discord.Interaction) -> None:
        endpoint = self.bot.settings.weather_api_url
        if not endpoint:
            await interaction.response.send_message(
                embed=make_embed("Weather provider not configured", "Set `GTA_HUB_WEATHER_API_URL` in `.env` to enable current GTA weather."),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            await interaction.followup.send(f"The configured weather provider could not complete the request: `{type(exc).__name__}`.", ephemeral=True)
            return
        if not isinstance(data, dict):
            await interaction.followup.send("The weather provider returned an unexpected response.", ephemeral=True)
            return
        weather = truncate(data.get("weather") or "Unknown", 100)
        embed = make_embed(f"GTA V HUB • {weather}", truncate(data.get("details") or "Current in-game conditions", 1000))
        for key, label in (("game_time", "Game time"), ("next_change", "Next change")):
            if data.get(key):
                embed.add_field(name=label, value=truncate(data[key], 200), inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Weather(bot))
