from __future__ import annotations

import math
from typing import Any

import discord

PURPLE = discord.Color(0xA855F7)
DARK = discord.Color(0x17131F)
MUTED = discord.Color(0x9B8AAE)

BRAND = "GTA V HUB"
FOOTER = "GTA V HUB • Los Santos Network"


def safe_latency_ms(latency: Any) -> str:
    """Format bot gateway latency safely into milliseconds, avoiding inf/nan overflow."""
    try:
        val = float(latency)
        if math.isinf(val) or math.isnan(val) or val < 0:
            return "N/A"
        return f"{round(val * 1000)} ms"
    except (TypeError, ValueError, OverflowError):
        return "N/A"


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
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit == 1:
        return text[:1]
    return text[: max(0, limit - 1)].rstrip() + "…"


def safe_url(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.strip()
    if candidate.startswith(("https://", "http://")) and len(candidate) <= 500:
        return candidate
    return None
