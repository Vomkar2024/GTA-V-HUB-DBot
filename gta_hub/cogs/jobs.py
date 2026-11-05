from __future__ import annotations

import random
from urllib.parse import urlparse

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

from gta_hub.branding import make_embed, safe_url, truncate
from gta_hub.cogs.common import show_catalog_results


class Jobs(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    job = app_commands.Group(name="job", description="Search GTA V HUB jobs")
    creator = app_commands.Group(name="creator", description="Search creators and playlists")

    @job.command(name="search", description="Search jobs by name or creator")
    async def search_job(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("jobs", query)
        await show_catalog_results(interaction, kind="jobs", query=query, rows=rows)

    @job.command(name="random", description="Pick a random job from your catalog")
    async def random_job(self, interaction: discord.Interaction) -> None:
        rows = self.bot.catalog.all("jobs")
        if not rows:
            await interaction.response.send_message(
                embed=make_embed("Job catalog is empty", "Add permitted job records to `data/jobs.json` first."),
                ephemeral=True,
            )
            return
        row = random.choice(rows)
        name = truncate(row.get("name") or "Random Job", 200)
        description = str(row.get("description") or "A random pick from your local job catalog.")
        embed = make_embed(f"GTA V HUB • {name}", description)
        creator = row.get("creator")
        if creator:
            embed.add_field(name="Creator", value=truncate(creator), inline=True)
        if row.get("platform"):
            embed.add_field(name="Platform", value=truncate(row["platform"]), inline=True)
        link = safe_url(row.get("url"))
        if link:
            embed.add_field(name="Job link", value=f"[Open job]({link})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @job.command(name="sync", description="Resolve a Social Club job URL through your configured provider")
    @app_commands.describe(url="Public Social Club job URL")
    async def sync_job(self, interaction: discord.Interaction, url: str) -> None:
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        host = (parsed.hostname or "").casefold()
        trusted_host = host == "rockstargames.com" or host.endswith(".rockstargames.com")
        if parsed.scheme != "https" or not trusted_host:
            await interaction.response.send_message("Enter an HTTPS Rockstar Games Social Club URL.", ephemeral=True)
            return
        endpoint = self.bot.settings.sync_api_url
        if not endpoint:
            await interaction.response.send_message(
                embed=make_embed("Job sync is not configured", "Set `GTA_HUB_SYNC_API_URL` in `.env` to connect your own provider."),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(endpoint, params={"url": clean_url}) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            await interaction.followup.send(f"The configured job provider could not complete the request: `{type(exc).__name__}`.", ephemeral=True)
            return
        if not isinstance(data, dict):
            await interaction.followup.send("The job provider returned an unexpected response.", ephemeral=True)
            return
        embed = make_embed(truncate(data.get("name") or "Synced Job", 240), truncate(data.get("description") or "Resolved by your configured provider.", 3000))
        for key in ("creator", "platform"):
            if data.get(key):
                embed.add_field(name=key.title(), value=truncate(data[key]), inline=True)
        result_url = safe_url(data.get("url")) or clean_url
        embed.add_field(name="Job link", value=f"[Open job]({result_url})", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @creator.command(name="search", description="Search creators in your local catalog")
    async def search_creator(self, interaction: discord.Interaction, query: str) -> None:
        rows = self.bot.catalog.search("creators", query)
        await show_catalog_results(interaction, kind="creators", query=query, rows=rows)

    @creator.command(name="playlists", description="Show playlist entries for a creator")
    async def creator_playlists(self, interaction: discord.Interaction, name: str) -> None:
        creators = self.bot.catalog.search("creators", name, limit=5)
        match = next((row for row in creators if str(row.get("name", "")).casefold() == name.casefold()), None)
        if match is None and creators:
            match = creators[0]
        if not match:
            await interaction.response.send_message("No matching creator was found in `data/creators.json`.", ephemeral=True)
            return
        playlists = match.get("playlists") or []
        embed = make_embed(f"GTA V HUB • {truncate(match.get('name') or 'Creator', 180)} Playlists")
        if not isinstance(playlists, list) or not playlists:
            embed.description = "No playlists are listed for this creator."
        else:
            for playlist in playlists[:20]:
                if isinstance(playlist, dict):
                    label = truncate(playlist.get("name") or "Untitled Playlist", 200)
                    link = safe_url(playlist.get("url"))
                    embed.add_field(name=label, value=f"[Open playlist]({link})" if link else "No link supplied", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Jobs(bot))
