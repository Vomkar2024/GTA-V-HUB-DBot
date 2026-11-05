from __future__ import annotations

from typing import Any

import discord

from gta_hub.branding import make_embed, truncate
from gta_hub.views import CatalogResultsView, build_entry_embed_and_file


async def show_catalog_results(
    interaction: discord.Interaction,
    *,
    kind: str,
    query: str,
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        embed = make_embed("No matches found", f"No **{kind}** matched `{truncate(query, 100)}`. Try another search or add entries to the matching JSON catalog.")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if len(rows) == 1:
        embed, file = build_entry_embed_and_file(kind, rows[0])
        files = [file] if file is not None else []
        view = CatalogResultsView(rows, kind=kind)
        await interaction.response.send_message(embed=embed, files=files, view=view, ephemeral=True)
        return

    embed = make_embed(
        f"GTA V HUB • {kind.title()} Search",
        f"Found **{len(rows)}** result(s) for `{truncate(query, 100)}`. Choose an entry below to inspect it.",
    )
    for row in rows[:8]:
        name = row.get("name") or row.get("title") or "Unnamed entry"
        extra = row.get("manufacturer") or row.get("creator") or row.get("class") or row.get("type") or ""
        embed.add_field(name=truncate(name, 200), value=truncate(extra or "GTA V HUB catalog entry", 300), inline=True)
    view = CatalogResultsView(rows, kind=kind)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
