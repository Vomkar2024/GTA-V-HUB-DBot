from __future__ import annotations

from typing import Any

import discord

from gta_hub.branding import make_embed, safe_url, truncate

HELP_SECTIONS: dict[str, str] = {
    "Overview": (
        "**GTA V HUB** is your Los Santos companion. Use the menu to browse command groups.\n\n"
        "All catalog searches use the JSON files in the bot's `data/` directory."
    ),
    "Vehicles": (
        "`/vehicle search query` — Find a vehicle by name or manufacturer.\n"
        "`/vehicle class name` — Browse vehicles in a class.\n"
        "`/vehicle tier class_name tier` — Filter a class by a performance tier."
    ),
    "Wheels": (
        "`/wheel search query` — Find a wheel.\n"
        "`/wheel type name` — Browse a wheel type.\n"
        "`/wheel effects` — Filter by type, traction bias, anti-roll, or slip angle."
    ),
    "Jobs & Creators": (
        "`/job search query` — Search your job catalog.\n"
        "`/job random` — Pick a random catalog job.\n"
        "`/job sync url` — Resolve a job URL through your configured provider.\n"
        "`/creator search query` — Search creators.\n"
        "`/creator playlists name` — Show a creator's playlists."
    ),
    "Weather": (
        "`/weather current` — Show current GTA weather from your configured provider.\n\n"
        "Set `GTA_HUB_WEATHER_API_URL` in `.env` to enable live weather data."
    ),
    "Garage & Community": (
        "`/community link` — Link your Rockstar nickname and platform.\n"
        "`/community profile` — View a linked community profile.\n"
        "`/community stats` — View HUB credits, daily claims, and streak.\n"
        "`/cars` — Search vehicles using the shared vehicle catalogue.\n"
        "`/garage` — View, add, and remove saved vehicles.\n"
        "`/compare` — Compare two vehicles.\n"
        "`/profile` and `/stats` — Player lookup surfaces.\n"
        "`/crew` and `/jobs` — Best-effort legacy lookup commands.\n"
        "`/daily` — Claim daily HUB credits (not GTA$)."
    ),
    "Links & Help": (
        "`/invite` — Get the bot invite link.\n"
        "`/support` — Open the community/support link.\n"
        "`/ping` — Check bot latency.\n"
        "`/hubadmin status` — Owner-only runtime status.\n"
        "`/hubadmin sync` — Sync application commands and resolve duplicates.\n"
        "`/hubadmin sync-catalogs` — Synchronize vehicle and wheel catalogues.\n"
        "`/hubadmin add-vehicle` — Add a local vehicle entry."
    ),
}


class HelpSelect(discord.ui.Select):
    def __init__(self) -> None:
        options = [
            discord.SelectOption(label=label, description=f"Show {label.lower()} commands", value=label)
            for label in HELP_SECTIONS
        ]
        super().__init__(
            placeholder="Choose a GTA V HUB category…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="gtavhub:help:section",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        section = self.values[0]
        embed = make_embed(f"GTA V HUB • {section}", HELP_SECTIONS[section])
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, *, invite_url: str | None, support_url: str | None, donate_url: str | None):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())
        for label, url, emoji in (
            ("Invite Bot", invite_url, "🚀"),
            ("Support", support_url, "💬"),
            ("Support Dev", donate_url, "💜"),
        ):
            valid = safe_url(url)
            if valid:
                self.add_item(discord.ui.Button(label=label, url=valid, emoji=emoji))


class CatalogSelect(discord.ui.Select):
    def __init__(self, rows: list[dict[str, Any]], *, kind: str):
        self.rows = rows
        self.kind = kind
        options: list[discord.SelectOption] = []
        for index, row in enumerate(rows[:25]):
            name = truncate(row.get("name") or row.get("title") or "Unnamed entry", 100)
            detail = row.get("manufacturer") or row.get("class") or row.get("creator") or row.get("type")
            description = truncate(detail or f"Open {kind[:-1] if kind.endswith('s') else kind} details", 100)
            options.append(discord.SelectOption(label=name or "Unnamed entry", description=description, value=str(index)))

        if not options:
            options.append(discord.SelectOption(label="No entries available", value="none", default=True))

        super().__init__(
            placeholder="Select a result to view details…",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.values[0] == "none" or not self.rows:
            await interaction.response.defer()
            return
        row = self.rows[int(self.values[0])]
        await interaction.response.edit_message(embed=entry_embed(self.kind, row), view=self.view)


class CatalogResultsView(discord.ui.View):
    def __init__(self, rows: list[dict[str, Any]], *, kind: str):
        super().__init__(timeout=150)
        self.add_item(CatalogSelect(rows, kind=kind))


def entry_embed(kind: str, row: dict[str, Any]) -> discord.Embed:
    title = str(row.get("name") or row.get("title") or "GTA V HUB Entry")
    description = row.get("description")
    embed = make_embed(title, truncate(description, 3500) if description else None)

    labels = {
        "vehicles": ("manufacturer", "class", "tier", "price", "drivetrain", "top_speed", "lap_time", "seats"),
        "wheels": ("type", "price", "traction_bias", "anti_roll", "slip_angle", "suggested"),
        "jobs": ("creator", "platform"),
        "creators": ("platform",),
    }.get(kind, ())
    for key in labels:
        value = row.get(key)
        if value is not None and str(value).strip():
            embed.add_field(name=key.replace("_", " ").title(), value=truncate(value, 900), inline=True)

    link = safe_url(row.get("url"))
    if link:
        embed.add_field(name="Link", value=f"[Catalogue details]({link})", inline=False)
    image = safe_url(row.get("image_url"))
    if kind == "vehicles" and image:
        embed.set_thumbnail(url=image)
    return embed
