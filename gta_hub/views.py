from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import discord

from gta_hub.branding import make_embed, safe_latency_ms, safe_url, truncate

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
        "`/community leaderboard` — View top members by credits or streaks.\n"
        "`/cars` — Search vehicles using the shared vehicle catalogue.\n"
        "`/garage` — View, add, and remove saved vehicles.\n"
        "`/compare` — Compare two vehicles.\n"
        "`/profile` and `/stats` — Player lookup surfaces.\n"
        "`/crew` and `/jobs` — Best-effort legacy lookup commands.\n"
        "`/daily` — Claim daily HUB credits (not GTA$)."
    ),
    "Links & Help": (
        "`/help` — Open the GTA V HUB command center.\n"
        "`/invite` — Get the bot invite link.\n"
        "`/support` — Open the community/support link.\n"
        "`/ping` — Check bot latency."
    ),
}

ADMIN_PANEL_TEXT: str = (
    "Privileged operations reserved for bot owners (`OWNER_IDS`).\n"
    "Admin commands bypass channel restrictions and can be executed anywhere.\n\n"
    "**Core Admin Privileges & Tools:**\n"
    "• `/hubadmin status` — Show bot uptime, gateway latency, catalog records, and sync history.\n"
    "• `/hubadmin reload-catalogs` — Hot-reload local vehicle, wheel, job, and creator catalogs.\n"
    "• `/hubadmin sync` — Sync Discord slash command tree (guild, global, clear-global, clear-guild).\n"
    "• `/hubadmin sync-catalogs` — Synchronize vehicle and wheel databases with configured API.\n"
    "• `/hubadmin add-vehicle` — Manually append a new vehicle to local catalog.\n"
    "• `!hub9575` — Reopen this secret control panel anytime."
)


def make_admin_panel_embed() -> discord.Embed:
    embed = make_embed(
        "GTA V HUB • Owner & Admin Control Panel",
        ADMIN_PANEL_TEXT,
    )
    embed.set_footer(text="Confidential • Restricted to bot owners (OWNER_IDS)")
    return embed


class AdminPanelView(discord.ui.View):
    def __init__(self, bot: Any):
        super().__init__(timeout=300)
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        allowed = bool(self.bot.settings.owner_ids and interaction.user.id in self.bot.settings.owner_ids)
        if not allowed:
            if hasattr(interaction, "response") and not interaction.response.is_done():
                await interaction.response.send_message(
                    "You are not authorized to interact with the GTA V HUB admin panel.",
                    ephemeral=True,
                )
        return allowed

    @discord.ui.button(label="Status", style=discord.ButtonStyle.primary, emoji="📊", custom_id="gtavhub:admin:status_btn")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        summary += f"\n**Guilds:** {len(self.bot.guilds)}"
        summary += f"\n**Latency:** {safe_latency_ms(getattr(self.bot, 'latency', None))}"
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

    @discord.ui.button(label="Reload Catalogs", style=discord.ButtonStyle.secondary, emoji="🔄", custom_id="gtavhub:admin:reload_btn")
    async def reload_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        try:
            self.bot.catalog.load_all()
            if hasattr(self.bot, "gta") and hasattr(self.bot.gta, "reload_vehicles"):
                self.bot.gta.reload_vehicles()
        except Exception as exc:
            await interaction.response.send_message(f"Catalog reload failed: `{type(exc).__name__}`: {exc}", ephemeral=True)
            return
        counts = self.bot.catalog.counts()
        summary = "\n".join(f"**{kind.title()}:** {count}" for kind, count in counts.items())
        await interaction.response.send_message(embed=make_embed("Catalogs Reloaded", summary), ephemeral=True)

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True


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

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True


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
        embed, file = build_entry_embed_and_file(self.kind, row)
        attachments = [file] if file is not None else []
        await interaction.response.edit_message(embed=embed, attachments=attachments, view=None)


class CatalogResultsView(discord.ui.View):
    def __init__(self, rows: list[dict[str, Any]], *, kind: str):
        super().__init__(timeout=150)
        self.add_item(CatalogSelect(rows, kind=kind))

    async def on_timeout(self) -> None:
        for child in self.children:
            if hasattr(child, "disabled"):
                child.disabled = True


ROMAN_NUMERALS: dict[str, str] = {
    "viii": "8",
    "vii": "7",
    "vi": "6",
    "iv": "4",
    "v": "5",
    "iii": "3",
    "ii": "2",
    "i": "1",
}

_RE_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]")
_RE_NON_ALPHANUMERIC_SLUG = re.compile(r"[^a-z0-9]+")
_RE_SAFE_SLUG = re.compile(r"[^a-z0-9_]+")
_RE_PARENTHETICAL = re.compile(r"\(.*?\)")

_IMAGE_INDEX_CACHE: dict[Path, dict[str, Path]] = {}
_IMAGE_RESOLVE_CACHE: dict[tuple[Path, str, str, str, str, str], Path | None] = {}


def clear_image_cache() -> None:
    """Clear the cached asset image index and vehicle resolution cache."""
    _IMAGE_INDEX_CACHE.clear()
    _IMAGE_RESOLVE_CACHE.clear()


def _get_image_index(base_dir: Path) -> dict[str, Path]:
    try:
        resolved = base_dir.resolve()
    except OSError:
        resolved = base_dir
    cached = _IMAGE_INDEX_CACHE.get(resolved)
    if cached is not None:
        return cached
    if not resolved.is_dir():
        return {}
    index: dict[str, Path] = {}
    try:
        for entry in resolved.iterdir():
            if entry.is_file() and entry.suffix.lower() == ".png":
                index[entry.name.lower()] = entry
    except OSError:
        pass
    _IMAGE_INDEX_CACHE[resolved] = index
    return index


def resolve_vehicle_image(row: dict[str, Any], assets_dir: Path | str | None = None) -> Path | None:
    """Find a matching vehicle image file from the assets/images directory."""
    if assets_dir is None:
        base_dir = Path("assets/images")
    else:
        base_dir = Path(assets_dir)
        if base_dir.name != "images":
            base_dir = base_dir / "images"

    if not base_dir.is_dir():
        base_dir = Path.cwd() / "assets" / "images"
        if not base_dir.is_dir():
            return None

    try:
        resolved_base = base_dir.resolve()
    except OSError:
        resolved_base = base_dir

    direct_img = str(row.get("image_url") or "").strip()
    name = str(row.get("name") or "").strip().lower()
    model = str(row.get("model") or "").strip().lower()
    vid = str(row.get("id") or "").strip().lower()
    manuf = str(row.get("manufacturer") or "").strip().lower()

    cache_key = (resolved_base, direct_img, name, model, vid, manuf)
    if cache_key in _IMAGE_RESOLVE_CACHE:
        return _IMAGE_RESOLVE_CACHE[cache_key]

    img_index = _get_image_index(resolved_base)

    # Check direct image_url if provided
    if direct_img:
        cand_name = Path(direct_img).name.lower()
        if cand_name in img_index:
            result = img_index[cand_name]
            _IMAGE_RESOLVE_CACHE[cache_key] = result
            return result

    candidates: list[str] = []

    # Model and ID candidates
    for token in (model, vid):
        if not token:
            continue
        candidates.append(f"{token}.png")
        clean_tok = _RE_NON_ALPHANUMERIC.sub("", token)
        if clean_tok:
            candidates.append(f"{clean_tok}.png")

    if name:
        # Build variants of name: original, with Roman numerals converted, and without parentheticals
        name_variants: list[str] = [name]

        # Convert Roman numerals (e.g. "baller ii" -> "baller 2")
        words = name.split()
        converted_words = [ROMAN_NUMERALS.get(w.strip("()"), w.strip("()")) for w in words]
        name_converted = " ".join(converted_words)
        if name_converted != name:
            name_variants.append(name_converted)

        # Strip parentheticals (e.g. "daemon (custom)" -> "daemon")
        no_paren = _RE_PARENTHETICAL.sub("", name).strip()
        if no_paren and no_paren != name:
            name_variants.append(no_paren)
            words_np = no_paren.split()
            conv_np = " ".join(ROMAN_NUMERALS.get(w.strip("()"), w.strip("()")) for w in words_np)
            if conv_np != no_paren:
                name_variants.append(conv_np)

        for n in name_variants:
            clean_name = _RE_NON_ALPHANUMERIC_SLUG.sub("-", n).strip("-")
            if clean_name:
                candidates.append(f"{clean_name}.png")
            clean_name_num = _RE_NON_ALPHANUMERIC.sub("", n)
            if clean_name_num:
                candidates.append(f"{clean_name_num}.png")

            # Strip manufacturer prefix (e.g. "Albany Alpha" -> "Alpha", "Western Daemon" -> "Daemon")
            if manuf and n.startswith(manuf):
                stripped = n[len(manuf):].strip()
                stripped_slug = _RE_NON_ALPHANUMERIC_SLUG.sub("-", stripped).strip("-")
                if stripped_slug:
                    candidates.append(f"{stripped_slug}.png")
                clean_stripped = _RE_NON_ALPHANUMERIC.sub("", stripped)
                if clean_stripped:
                    candidates.append(f"{clean_stripped}.png")

    for cand in candidates:
        if not cand or cand == ".png":
            continue
        matched = img_index.get(cand.lower())
        if matched is not None:
            _IMAGE_RESOLVE_CACHE[cache_key] = matched
            return matched

    _IMAGE_RESOLVE_CACHE[cache_key] = None
    return None


def build_entry_embed_and_file(
    kind: str,
    row: dict[str, Any],
    assets_dir: Path | str | None = None,
) -> tuple[discord.Embed, discord.File | None]:
    """Build the detail embed and attach a matching vehicle image file if available."""
    file: discord.File | None = None
    attachment_filename: str | None = None

    if kind == "vehicles":
        image_path = resolve_vehicle_image(row, assets_dir=assets_dir)
        if image_path:
            slug = str(row.get("id") or row.get("model") or "vehicle").strip().lower()
            slug = _RE_SAFE_SLUG.sub("_", slug) or "vehicle"
            attachment_filename = f"{slug}.png"
            file = discord.File(fp=str(image_path), filename=attachment_filename)

    embed = entry_embed(kind, row, attachment_filename=attachment_filename)
    return embed, file


def entry_embed(
    kind: str,
    row: dict[str, Any],
    attachment_filename: str | None = None,
) -> discord.Embed:
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

    if kind == "vehicles":
        if attachment_filename:
            embed.set_image(url=f"attachment://{attachment_filename}")
        else:
            image = safe_url(row.get("image_url"))
            if image:
                embed.set_image(url=image)
    else:
        thumb = safe_url(row.get("image_url") or row.get("thumbnail"))
        if thumb:
            embed.set_thumbnail(url=thumb)

    return embed
