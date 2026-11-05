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

    @app_commands.command(name="sync", description="Manage Discord slash command registration and remove duplicates")
    @app_commands.describe(mode="Sync action: guild, global, clear-global (fixes duplicates), or clear-guild")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Clear global commands (fixes duplicates in guild)", value="clear-global"),
        app_commands.Choice(name="Sync to current guild", value="guild"),
        app_commands.Choice(name="Sync globally", value="global"),
        app_commands.Choice(name="Clear guild commands", value="clear-guild"),
    ])
    async def sync_commands(self, interaction: discord.Interaction, mode: app_commands.Choice[str]) -> None:
        await interaction.response.defer(ephemeral=True)
        try:
            if mode.value == "clear-global":
                self.bot.tree.clear_commands(guild=None)
                synced = await self.bot.tree.sync()
                await interaction.followup.send(
                    embed=make_embed(
                        "Commands Cleared",
                        f"Cleared all global commands ({len(synced)} active). Duplicate commands in your guild should now disappear.",
                    ),
                    ephemeral=True,
                )
            elif mode.value == "clear-guild":
                if not interaction.guild:
                    await interaction.followup.send("This action can only be run inside a guild.", ephemeral=True)
                    return
                self.bot.tree.clear_commands(guild=interaction.guild)
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    embed=make_embed("Guild Commands Cleared", f"Cleared commands for **{interaction.guild.name}** ({len(synced)} active)."),
                    ephemeral=True,
                )
            elif mode.value == "guild":
                if not interaction.guild:
                    await interaction.followup.send("This action can only be run inside a guild.", ephemeral=True)
                    return
                self.bot.tree.copy_global_to(guild=interaction.guild)
                synced = await self.bot.tree.sync(guild=interaction.guild)
                await interaction.followup.send(
                    embed=make_embed("Guild Commands Synced", f"Synced **{len(synced)}** command(s) to **{interaction.guild.name}**."),
                    ephemeral=True,
                )
            elif mode.value == "global":
                synced = await self.bot.tree.sync()
                await interaction.followup.send(
                    embed=make_embed("Global Commands Synced", f"Synced **{len(synced)}** global command(s). Propagation may take up to an hour across Discord."),
                    ephemeral=True,
                )
        except Exception as exc:
            await interaction.followup.send(f"Command sync failed: `{type(exc).__name__}`: {exc}", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HubAdmin(bot))
