from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed


class HubAdmin(commands.GroupCog, group_name="hubadmin", group_description="GTA V HUB owner tools"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = interaction.user.id in self.bot.settings.owner_ids
        if not allowed:
            await interaction.response.send_message("You are not authorized to use GTA V HUB owner tools.", ephemeral=True)
        return allowed

    @app_commands.command(name="reload-catalogs", description="Reload local vehicle, wheel, job, and creator catalogs")
    async def reload_catalogs(self, interaction: discord.Interaction) -> None:
        try:
            self.bot.catalog.load_all()
        except Exception as exc:
            await interaction.response.send_message(f"Catalog reload failed: `{type(exc).__name__}`.", ephemeral=True)
            return
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        await interaction.response.send_message(embed=make_embed("Catalogs reloaded", summary), ephemeral=True)

    @app_commands.command(name="status", description="Show bot status and catalog counts")
    async def status(self, interaction: discord.Interaction) -> None:
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        summary += f"\n**Guilds:** {len(self.bot.guilds)}"
        summary += f"\n**Latency:** {round(self.bot.latency * 1000)} ms"
        await interaction.response.send_message(embed=make_embed("GTA V HUB • Runtime Status", summary), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HubAdmin(bot))
