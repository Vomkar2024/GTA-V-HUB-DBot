from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed, safe_latency_ms
from gta_hub.views import HELP_SECTIONS, HelpView


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Open the GTA V HUB command center")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = make_embed("GTA V HUB • Command Center", HELP_SECTIONS["Overview"])
        view = HelpView(
            invite_url=self.bot.settings.invite_url,
            support_url=self.bot.settings.support_url,
            donate_url=self.bot.settings.donate_url,
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="ping", description="Check GTA V HUB response latency")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency = safe_latency_ms(self.bot.latency)
        await interaction.response.send_message(
            embed=make_embed("GTA V HUB • Connection", f"🟣 Gateway latency: **{latency}**"),
            ephemeral=True,
        )

    @app_commands.command(name="invite", description="Get the GTA V HUB bot invite link")
    async def invite(self, interaction: discord.Interaction) -> None:
        url = self.bot.settings.invite_url
        description = f"[Add GTA V HUB to your server]({url})" if url else "Set `INVITE_URL` in `.env` to publish your bot invite link."
        await interaction.response.send_message(embed=make_embed("GTA V HUB • Invite", description), ephemeral=True)

    @app_commands.command(name="support", description="Open the GTA V HUB community and support links")
    async def support(self, interaction: discord.Interaction) -> None:
        links = []
        for label, url in (("Community", self.bot.settings.support_url), ("Support development", self.bot.settings.donate_url)):
            if url:
                links.append(f"[{label}]({url})")
        description = "\n".join(links) if links else "Set `SUPPORT_URL` or `DONATE_URL` in `.env` to add links here."
        await interaction.response.send_message(embed=make_embed("GTA V HUB • Support", description), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
