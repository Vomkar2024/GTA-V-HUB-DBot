# GTA V HUB

A fresh, modular Discord companion bot for GTA Online. The project uses a **black + neon-purple** visual identity, slash commands, interactive help menus, and searchable local catalogs.

> **Status:** starter implementation. The bot framework, slash-command structure, embeds, menus, local catalog search, and tests are implemented. Vehicle, wheel, job, and creator records are intentionally not bundled; add data you have the right to use. Live weather and Social Club job-sync require a provider endpoint configured by you.

## Feature map

| Area | Commands | Data source |
| --- | --- | --- |
| Help & setup | `/help`, `/invite`, `/support`, `/ping` | Built in |
| Vehicles | `/vehicle search`, `/vehicle class`, `/vehicle tier` | `data/vehicles.json` |
| Wheels | `/wheel search`, `/wheel type`, `/wheel effects` | `data/wheels.json` |
| Jobs | `/job search`, `/job random`, `/job sync` | `data/jobs.json` and optional sync provider |
| Creators | `/creator search`, `/creator playlists` | `data/creators.json` |
| GTA weather | `/weather current` | Optional weather provider |
| Owner tools | `/hubadmin reload-catalogs`, `/hubadmin status` | Runtime |

Catalog search supports exact matches, partial matches, and typo-tolerant ranking. Matching results are shown in branded embeds with a dropdown selector for details. The help panel also uses a category dropdown and URL buttons when links are configured. Discord clients control the embed background and font, so the bot uses neon-purple accent colors and GTA V HUB copy rather than trying to force a custom typeface or black embed panel.

## Requirements

- Python 3.11+
- A Discord application and bot token
- The bot invited with the `bot` and `applications.commands` OAuth2 scopes, plus permission to send messages, embed links, and use application commands

The project targets `discord.py` 2.7.1 (released March 3, 2026). See the [discord.py package page](https://pypi.org/project/discord.py/). 

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

Copy `.env.example` to `.env`, set `DISCORD_TOKEN`, then start the bot:

```bash
python bot.py
```

For fast command registration during development, set `GUILD_ID` to your test server ID. When `GUILD_ID` is unset, commands are synced globally; global command propagation can take time.

## Configuration

| Variable | Required | Description |
| --- | --- | --- |
| `DISCORD_TOKEN` | Yes | Bot token from the Discord Developer Portal |
| `GUILD_ID` | No | Test guild ID for quick slash-command sync |
| `OWNER_IDS` | No | Comma-separated Discord user IDs allowed to use `/hubadmin` |
| `INVITE_URL` | No | Bot OAuth2 invite URL shown by `/invite` |
| `SUPPORT_URL` | No | Community/support invite or website |
| `DONATE_URL` | No | Optional donation link |
| `DATA_DIR` | No | Catalog directory; defaults to `data` |
| `GTA_HUB_WEATHER_API_URL` | No | Optional JSON endpoint for live GTA weather |
| `GTA_HUB_SYNC_API_URL` | No | Optional endpoint to resolve a Social Club job URL |
| `LOG_LEVEL` | No | Python logging level; defaults to `INFO` |

Do not commit `.env`, bot tokens, API keys, service-account files, database credentials, or private user data.

## Catalog data

The repository contains empty JSON arrays as safe starting points. Add records only from sources you are allowed to use, and document the source and its terms alongside your data.

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

## Development

Run tests and syntax checks:

```bash
python -m unittest discover -s tests -v
python -m compileall -q bot.py gta_hub tests
```

The GitHub Actions workflow runs the same checks on pushes and pull requests.

## Upstream feature reference and licensing

The feature areas were informed by functionality described in the public [nosv1/GTALens](https://github.com/nosv1/GTALens) project. The inspected `dev` branch did not include a license file. This repository is an independent implementation: it does **not** redistribute GTALens source code, bundled datasets, or artwork. Obtain permission or a suitable license from the relevant rights holders before porting those materials. Required notices and attributions must be retained for any third-party material added later.

The original GTALens project remains credited as a feature reference; no affiliation or endorsement is implied.

## Disclaimer

GTA V and related marks belong to their respective owners. GTA V HUB is an independent community project and is not affiliated with, endorsed by, or sponsored by Rockstar Games.


## Merged project notes

This consolidated project uses the modular `gta_hub/` bot as its runtime foundation. The starter version's SQLite garage and daily-reward persistence, vehicle comparison, player profile/stats command surfaces, and legacy crew/creator-job lookups are integrated as an additional command cog. The duplicate `/help` command was unified into the modular help menu. `/cars` and `/vehicle ...` are both available and read the same `data/vehicles.json` catalogue. The `/jobs` creator-ID lookup and `/job ...` local-catalog commands are distinct.

The Rockstar crew/job endpoints are undocumented and best-effort. Player profile/stat commands do not claim to retrieve private account data; a permitted public provider is required for real profiles. Daily rewards are community HUB credits, not in-game GTA$.
