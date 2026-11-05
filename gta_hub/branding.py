from __future__ import annotations

import discord

PURPLE = discord.Color(0xA855F7)
DARK = discord.Color(0x17131F)
MUTED = discord.Color(0x9B8AAE)

BRAND = "GTA V HUB"
FOOTER = "GTA V HUB • Los Santos Network"


def make_embed(
    title: str,
    description: str | None = None,
    *,
    color: discord.Color = PURPLE,
) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text=FOOTER)
    return embed


def truncate(value: object, limit: int = 100) -> str:
    text = str(value) if value is not None else ""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def safe_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.startswith(("https://", "http://")) and len(candidate) <= 500:
        return candidate
    return None
