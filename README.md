# GTA V HUB

A fresh, modular Discord companion bot for GTA Online. The project uses a **black + neon-purple** visual identity, slash commands, interactive help menus, and searchable local catalogs.

> **Status:** modular Discord bot implementation. The bot framework, slash-command structure, embeds, interactive views, local catalog search, community links, public catalogue synchronization, and test suites are fully implemented. Vehicle, wheel, job, and creator records start with empty arrays; use `/hubadmin sync-catalogs` to import public datasets or add your own data. Live weather and Social Club job-sync require an optional provider endpoint.

## Feature map

| Area | Commands | Data source |
| --- | --- | --- |
| Help & setup | `/help`, `/invite`, `/support`, `/ping` | Built in |
| Community profile | `/community link`, `/community profile`, `/community stats` | SQLite |
| Vehicles | `/vehicle search`, `/vehicle class`, `/vehicle tier` | `data/vehicles.json` |
| Wheels | `/wheel search`, `/wheel type`, `/wheel effects` | `data/wheels.json` |
| Jobs | `/job search`, `/job random`, `/job sync` | `data/jobs.json` and optional sync provider |
| Creators | `/creator search`, `/creator playlists` | `data/creators.json` |
| GTA weather | `/weather current` | Optional weather provider |
| Garage & legacy | `/cars`, `/garage`, `/compare`, `/daily`, `/profile`, `/stats`, `/crew`, `/jobs` | SQLite & local catalogue |
| Owner tools | `/hubadmin status`, `/hubadmin sync`, `/hubadmin reload-catalogs`, `/hubadmin sync-catalogs`, `/hubadmin add-vehicle` | Runtime + public catalogue adapters |

Catalog search supports exact matches, partial matches, and typo-tolerant ranking. Matching results are shown in branded embeds with a dropdown selector for details. The help panel also uses a category dropdown and URL buttons when links are configured. Discord clients control the embed background and font, so the bot uses neon-purple accent colors and GTA V HUB copy rather than trying to force a custom typeface or black embed panel.

## Requirements

- Python 3.11+
- A Discord application and bot token
- The bot invited with the `bot` and `applications.commands` OAuth2 scopes, plus permission to send messages, embed links, and use application commands

The project targets modern `discord.py` (2.4.0+ / 2.7.1+).

## Quick start

```bash
git clone https://github.com/Vomkar2024/GTA-V-HUB-DBot.git
cd GTA-V-HUB-DBot
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, set `DISCORD_TOKEN` and your Discord user ID in `OWNER_IDS` (needed for `/hubadmin`), then start the bot:

```bash
python bot.py
```

For fast command registration during development, set `GUILD_ID` to your test server ID. When `GUILD_ID` is unset, commands are synced globally; global command propagation can take time.

## Command Line Interface (CLI)

The bot supports command-line actions for managing slash command registration and resolving server duplicates without starting the gateway:

```bash
# Clear all global slash commands (resolves duplicate commands in servers)
python bot.py --clear-global

# Clear slash commands registered to the GUILD_ID in .env
python bot.py --clear-guild

# Synchronize slash commands without launching the bot gateway
python bot.py --sync-only
```

Or run `/hubadmin sync mode:Clear global commands (fixes duplicates in guild)` directly in Discord.

You can also set `CLEAR_GLOBAL_ON_STARTUP=true` in `.env` to automatically purge global commands whenever syncing to a guild.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | Bot token from the Discord Developer Portal |
| `GUILD_ID` | No | Test guild ID for quick slash-command sync |
| `CLEAR_GLOBAL_ON_STARTUP` | No | Clear global commands on startup when `GUILD_ID` is set (`true`/`false`) |
| `ENABLE_LEGACY_COMMANDS` | No | Enable legacy starter commands (`/cars`, `/garage`, `/daily`, etc.) |
| `OWNER_IDS` | No | Comma-separated Discord user IDs allowed to use `/hubadmin` |
| `ALLOWED_CHANNEL_ID` | No | Restrict bot commands to specific channel ID(s); leave empty for all channels |
| `INVITE_URL` | No | Bot OAuth2 invite URL shown by `/invite` |
| `SUPPORT_URL` | No | Community/support invite or website |
| `DONATE_URL` | No | Optional donation link |
| `DATA_DIR` | No | Catalog directory; defaults to `data` |
| `DATABASE_PATH` | No | SQLite file for garages, profiles, and daily rewards; defaults to `data/gtavhub.sqlite3` |
| `GTA_HUB_WEATHER_API_URL` | No | Optional JSON endpoint for live GTA weather |
| `GTA_HUB_SYNC_API_URL` | No | Optional endpoint to resolve a Social Club job URL |
| `LOG_LEVEL` | No | Python logging level; defaults to `INFO` |

Do not commit `.env`, bot tokens, API keys, service-account files, database credentials, or private user data.

## Catalog data

The repository contains empty JSON arrays as safe starting points. Run `/hubadmin sync-catalogs` to import vehicles, wheels, or both; use `/hubadmin add-vehicle` for a manual entry. This downloads public catalogue data on demand; it does not run automatically at startup. Add records only from sources you are allowed to use, and document the source and its terms alongside your data.

Each catalog file is a JSON array:

**`data/vehicles.json`**

```json
[
  {
    "name": "Example Vehicle",
    "manufacturer": "Example Manufacturer",
    "class": "Sports",
    "tier": "A",
    "price": "$1,000,000",
    "top_speed": "Example value",
    "lap_time": "Example value",
    "url": "https://example.com/vehicle",
    "image_url": "https://example.com/vehicle.png"
  }
]
```

**`data/wheels.json`**

```json
[
  {
    "name": "Example Wheel",
    "type": "Sport",
    "price": "$10,000",
    "traction_bias": "rear",
    "anti_roll": "+",
    "slip_angle": "-",
    "suggested": "Recommended",
    "url": "https://example.com/wheel"
  }
]
```

**`data/jobs.json`**

```json
[
  {
    "name": "Example Stunt Race",
    "creator": "Example Creator",
    "platform": "PC",
    "url": "https://example.com/job",
    "description": "Replace this sample with licensed data."
  }
]
```

**`data/creators.json`**

```json
[
  {
    "name": "Example Creator",
    "platform": "PC",
    "url": "https://example.com/creator",
    "playlists": [
      {"name": "Example Playlist", "url": "https://example.com/playlist"}
    ]
  }
]
```

Unknown fields are retained and displayed when possible. Missing optional fields are simply omitted.

## Public catalogue sync

`/hubadmin sync-catalogs` can import:
- Vehicles from the public GTACars API endpoint pattern used by the GTALens reference adapter.
- Wheels from the public GTALens `wheels.json` reference file.

Sync is manual, uses a descriptive User-Agent and a 0.75-second pause between vehicle pages, and does not use proxy rotation, Tor, credential harvesting, or rate-limit bypasses. Imported records are tagged internally; later syncs replace only records previously imported from the same provider and preserve local/manual entries. The `vehicles.json` and `wheels.json` files are updated atomically.

**Data rights note:** public availability does not automatically grant redistribution rights. Review GTACars and GTALens source terms and obtain any required permission before redistributing imported data or running a public hosted service. The GTALens repository's licensing status should be verified independently. The bot is not affiliated with either provider or Rockstar Games.

## Optional live providers

### Weather

Set `GTA_HUB_WEATHER_API_URL` to an HTTPS endpoint returning JSON such as:

```json
{
  "weather": "Clear",
  "game_time": "12:30",
  "next_change": "in 18 minutes",
  "details": "Los Santos"
}
```

### Job sync

Set `GTA_HUB_SYNC_API_URL` to an HTTPS endpoint. The bot sends a GET request with a `url` query parameter containing the supplied Social Club job URL. The provider should return JSON such as:

```json
{
  "name": "Example Stunt Race",
  "creator": "Example Creator",
  "platform": "PC",
  "url": "https://example.com/job",
  "description": "Optional description"
}
```

The endpoint contract is configurable and is not an official Rockstar API. This project does not scrape Rockstar services, bypass rate limits, or ship provider credentials.

## Development & Testing

Run tests and syntax checks:

```bash
# Run unit tests
python -m unittest discover -s tests -v

# Or run with pytest
python -m pytest

# Run syntax/compilation check
python -m compileall -q bot.py gta_hub tests
```

The GitHub Actions workflow runs the same checks on pushes and pull requests.

## Upstream feature reference and licensing

The feature areas were informed by functionality described in the public [nosv1/GTALens](https://github.com/nosv1/GTALens) project. The inspected `dev` branch did not include a license file. This repository is an independent implementation: it does **not** redistribute GTALens source code, bundled datasets, or artwork. Obtain permission or a suitable license from the relevant rights holders before porting those materials. Required notices and attributions must be retained for any third-party material added later.

The original GTALens project remains credited as a feature reference; no affiliation or endorsement is implied.

## Disclaimer

GTA V and related marks belong to their respective owners. GTA V HUB is an independent community project and is not affiliated with, endorsed by, or sponsored by Rockstar Games.

## Merged project notes

This consolidated project uses the modular `gta_hub/` bot as its runtime foundation and integrates the vehicle/wheel catalogue sync into that architecture. The SQLite garage and daily-reward persistence, vehicle comparison, community profile linking, HUB reward statistics, and legacy crew/creator-job lookups are integrated into the modular bot. The duplicate `/help` command was unified into the modular help menu. The profile-linking and community-stat features are housed under the non-conflicting `/community` command group; the catalogue add/status/sync tools and Discord command synchronization tools are consolidated under `/hubadmin`. The modular SQLite garage/profile/reward database remains the single persistence layer, while searchable catalogues remain JSON files. `/cars` and `/vehicle ...` are both available and read the same `data/vehicles.json` catalogue. The `/jobs` creator-ID lookup and `/job ...` local-catalog commands are distinct.

The Rockstar crew/job endpoints are undocumented and best-effort. Player profile/stat commands do not claim to retrieve private account data; a permitted public provider is required for real profiles. Daily rewards are community HUB credits, not in-game GTA$.
