from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed, safe_latency_ms
from gta_hub.views import AdminPanelView, make_admin_panel_embed


class HubAdmin(commands.GroupCog, group_name="hubadmin", group_description="GTA V HUB owner tools"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = interaction.user.id in self.bot.settings.owner_ids
        if not allowed:
            if hasattr(interaction, "response") and not interaction.response.is_done():
                await interaction.response.send_message(
                    "You are not authorized to use GTA V HUB owner tools.",
                    ephemeral=True,
                )
        return allowed

    @app_commands.command(name="reload-catalogs", description="Reload local vehicle, wheel, job, and creator catalogs")
    async def reload_catalogs(self, interaction: discord.Interaction) -> None:
        try:
            self.bot.catalog.load_all()
            if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "reload_vehicles"):
                self.bot.gta.reload_vehicles()
        except Exception as exc:
            await interaction.response.send_message(f"Catalog reload failed: `{type(exc).__name__}`: {exc}", ephemeral=True)
            return
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        await interaction.response.send_message(embed=make_embed("Catalogs reloaded", summary), ephemeral=True)

    @app_commands.command(name="status", description="Show bot status, catalog counts, and sync history")
    async def status(self, interaction: discord.Interaction) -> None:
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        summary += f"\n**Guilds:** {len(self.bot.guilds)}"
        summary += f"\n**Latency:** {safe_latency_ms(self.bot.latency)}"
        if hasattr(self.bot, "catalog_sync") and hasattr(self.bot.catalog_sync, "history"):
            history = self.bot.catalog_sync.history()
            if history:
                lines = [
                    f"• {str(item.get('catalogue', 'catalogue')).title()}: "
                    f"{item.get('records', 0)} records • {str(item.get('synced_at', ''))[:16]} UTC"
                    for item in history
                ]
                summary += "\n**Recent catalogue syncs:**\n" + "\n".join(lines)
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

    @app_commands.command(name="add-vehicle", description="Add a vehicle to the local catalogue")
    async def add_vehicle(
        self,
        interaction: discord.Interaction,
        manufacturer: str,
        name: str,
        vehicle_class: str,
        price: app_commands.Range[int, 0, 100_000_000],
        drivetrain: str = "Unknown",
    ) -> None:
        row = {
            "manufacturer": manufacturer.strip(),
            "name": name.strip(),
            "class": vehicle_class.strip(),
            "price": price,
            "drivetrain": drivetrain.strip(),
        }
        if not row["manufacturer"] or not row["name"] or not row["class"]:
            await interaction.response.send_message("Manufacturer, name, and class cannot be empty.", ephemeral=True)
            return
        try:
            self.bot.catalog.add("vehicles", row)
            if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "reload_vehicles"):
                self.bot.gta.reload_vehicles()
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(
            embed=make_embed("Vehicle added", f"Added **{manufacturer} {name}** to the local catalogue."),
            ephemeral=True,
        )

    @app_commands.command(name="sync-catalogs", description="Synchronize vehicle and wheel catalogues from the configured catalogue API")
    @app_commands.choices(catalogue=[
        app_commands.Choice(name="Vehicles and wheels", value="all"),
        app_commands.Choice(name="Vehicles only", value="vehicles"),
        app_commands.Choice(name="Wheels only", value="wheels"),
    ])
    async def sync_catalogs(
        self, interaction: discord.Interaction, catalogue: app_commands.Choice[str]
    ) -> None:
        if not hasattr(self.bot, "catalog_sync"):
            await interaction.response.send_message("Catalogue sync service is not available.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            results = await self.bot.catalog_sync.sync(catalogue.value)
            self.bot.catalog.load_all()
            if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "reload_vehicles"):
                self.bot.gta.reload_vehicles()
        except Exception as exc:
            try:
                self.bot.catalog.load_all()
                if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "reload_vehicles"):
                    self.bot.gta.reload_vehicles()
            except Exception:
                pass
            await interaction.followup.send(
                embed=make_embed(
                    "Catalogue sync failed",
                    f"`{type(exc).__name__}`: {str(exc)[:700]}\n\n"
                    "Check the terminal for details. Existing local catalogue files are retained when a sync request fails.",
                ),
                ephemeral=True,
            )
            return
        summary = "\n".join(f"**{kind.title()}:** {count:,} records imported" for kind, count in results.items())
        summary += "\n\nLocal/manual records were preserved. Run `/hubadmin status` to see current totals."
        await interaction.followup.send(
            embed=make_embed("GTA V HUB • Catalogue Sync Complete", summary),
            ephemeral=True,
        )

    @app_commands.command(name="panel", description="Open the GTA V HUB owner and admin control panel")
    async def admin_panel(self, interaction: discord.Interaction) -> None:
        embed = make_admin_panel_embed()
        view = AdminPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AdminSecret(commands.Cog):
    """Hidden admin triggers and secret commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="hub9575", description="Open the hidden GTA V HUB admin control panel")
    @app_commands.default_permissions(administrator=True)
    async def secret_admin_panel(self, interaction: discord.Interaction) -> None:
        allowed = bool(self.bot.settings.owner_ids and interaction.user.id in self.bot.settings.owner_ids)
        if not allowed:
            await interaction.response.send_message(
                "You are not authorized to access the GTA V HUB admin panel.",
                ephemeral=True,
            )
            return

        embed = make_admin_panel_embed()
        view = AdminPanelView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @commands.Cog.listener("on_message")
    async def on_secret_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        content = message.content.strip().lower()
        if content in ("!hub9575", "hub9575", "!9575", "9575", "/hub9575", "/9575"):
            allowed = bool(self.bot.settings.owner_ids and message.author.id in self.bot.settings.owner_ids)
            if not allowed:
                return
            try:
                await message.delete()
            except Exception:
                pass
            embed = make_admin_panel_embed()
            view = AdminPanelView(self.bot)
            try:
                await message.channel.send(embed=embed, view=view, delete_after=300)
            except Exception:
                await message.author.send(embed=embed, view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HubAdmin(bot))
    await bot.add_cog(AdminSecret(bot))
