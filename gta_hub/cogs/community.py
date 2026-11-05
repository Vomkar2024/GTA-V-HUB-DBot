from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed


class Community(commands.Cog):
    """Discord-side player links and community reward statistics."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    community = app_commands.Group(name="community", description="GTA V HUB player links and community stats")

    @community.command(name="link", description="Link your Rockstar nickname and platform to your Discord account")
    @app_commands.choices(platform=[
        app_commands.Choice(name="PC", value="PC"),
        app_commands.Choice(name="PlayStation", value="PlayStation"),
        app_commands.Choice(name="Xbox", value="Xbox"),
    ])
    async def link(
        self,
        interaction: discord.Interaction,
        rockstar_name: str,
        platform: app_commands.Choice[str],
    ) -> None:
        name = rockstar_name.strip()
        if not 2 <= len(name) <= 32:
            await interaction.response.send_message("Rockstar nickname must be 2–32 characters.", ephemeral=True)
            return
        await self.bot.db.set_profile(interaction.user.id, name, platform.value)
        await interaction.response.send_message(
            embed=make_embed("GTA V HUB • Profile Linked", f"Linked **{name}** on **{platform.value}** to your Discord account."),
            ephemeral=True,
        )

    @community.command(name="profile", description="View a linked GTA V HUB community profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        profile = await self.bot.db.get_profile(target.id)
        if not profile:
            await interaction.response.send_message(
                f"{target.display_name} has no linked community profile yet. Use `/community link`.",
                ephemeral=True,
            )
            return
        embed = make_embed(f"GTA V HUB • {target.display_name}", "Linked community profile")
        avatar_url = target.display_avatar.url if hasattr(target, "display_avatar") else None
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="Rockstar nickname", value=profile[0], inline=True)
        embed.add_field(name="Platform", value=profile[1], inline=True)
        embed.set_footer(text="A community link only; it does not access Rockstar account data.")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @community.command(name="stats", description="View community reward statistics")
    async def stats(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        stats = await self.bot.db.get_community_stats(target.id)
        if not stats:
            await interaction.response.send_message(
                f"{target.display_name} has no daily reward history yet. Use `/daily` to start.",
                ephemeral=True,
            )
            return
        embed = make_embed(f"GTA V HUB • {target.display_name} Stats", "Community activity, not official GTA Online statistics.")
        embed.add_field(name="HUB Credits earned", value=f"{stats['total_credits']:,}", inline=True)
        embed.add_field(name="Daily claims", value=f"{stats['claim_count']:,}", inline=True)
        embed.add_field(name="Current streak", value=f"{stats['streak']} day(s)", inline=True)
        embed.add_field(name="Last claim (UTC)", value=str(stats["last_claim"]), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Community(bot))

