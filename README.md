# GTA V HUB

[![CI](https://github.com/Vomkar2024/GTA-V-HUB-DBot/actions/workflows/ci.yml/badge.svg)](https://github.com/Vomkar2024/GTA-V-HUB-DBot/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![discord.py 2.4+](https://img.shields.io/badge/discord.py-2.4+-5865F2.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A modular, asynchronous Discord companion bot for GTA Online communities and Discord servers. Built with `discord.py` 2.4+, **GTA V HUB** features an asynchronous SQLite persistence layer, typo-tolerant local catalog search, interactive UI menus with custom neon-purple branding, channel-scoped execution controls, and automated dataset synchronization.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Prerequisites](#prerequisites)
- [Installation & Setup](#installation--setup)
- [Command Line Interface (CLI)](#command-line-interface-cli)
- [Configuration Reference](#configuration-reference)
- [Channel Restriction & Access Control](#channel-restriction--access-control)
- [Command Reference](#command-reference)
  - [General Commands](#general-commands)
  - [Vehicles & Wheels](#vehicles--wheels)
  - [Jobs & Creators](#jobs--creators)
  - [Community, Garage & Economy](#community-garage--economy)
  - [Legacy & Lookups](#legacy--lookups)
  - [Owner & Administration (`/hubadmin`)](#owner--administration-hubadmin)
- [Catalog Data & Schema](#catalog-data--schema)
- [Public Catalogue Sync](#public-catalogue-sync)
- [Optional Provider Contracts](#optional-provider-contracts)
- [Development & Testing](#development--testing)
- [Contributing](#contributing)
- [Credits & Disclaimers](#credits--disclaimers)

---

## Overview

**GTA V HUB** provides Discord communities with tools to search GTA Online vehicles, analyze wheel performance effects, browse community jobs, track personal garages, and claim daily HUB credits.

All core catalog searches operate against local JSON datasets stored in `data/`, ensuring fast response times without mandatory third-party API dependencies. Server owners can populate datasets manually or import public catalog records via built-in sync tools.

---

## Key Features

- **Typo-Tolerant Catalog Search**: High-performance search powered by `difflib.SequenceMatcher` with exact-match and prefix boosts across vehicles, wheels, jobs, and creators.
- **Interactive Discord UI**: Embeds styled in a custom neon-purple theme (`#A855F7`) featuring interactive select menus, dynamic category navigation, and external URL buttons.
- **Persistent Garage & Community System**: Asynchronous SQLite storage (using `aiosqlite` in WAL mode) for personal player garages, linked Rockstar Social Club profiles, and daily reward streaks.
- **Channel Scoping & Thread Awareness**: Enforce bot interactions to designated channels (`ALLOWED_CHANNEL_ID`) with automatic ephemeral redirects and thread parent detection. Owner administration commands automatically bypass restrictions.
- **Slash Command Management**: Built-in CLI flags and owner commands to resolve duplicate command registrations and manage global vs. guild command tree propagation.
- **Atomic Catalog Ingestion**: Download and merge vehicle and wheel data from public endpoints (`gtacars.net` API and GTALens reference dataset) with atomic file operations that preserve local custom additions.
- **Modular Architecture**: Clean cog-based structure with an optional legacy command suite (`ENABLE_LEGACY_COMMANDS`).

---

## System Architecture

```
GTA-V-HUB-DBot/
├── bot.py                     # Entrypoint: GtaHubBot class, CLI options, command error handlers
├── requirements.txt           # Production dependencies
├── .env.example               # Environment configuration template
├── LICENSE                    # MIT License
├── README.md                  # Project documentation
├── assets/                    # Repository assets & documentation notes
├── data/                      # Local JSON catalogs & SQLite storage
│   ├── creators.json          # Creator profiles and playlist catalog
│   ├── gtavhub.sqlite3        # SQLite database (garages, profiles, daily rewards)
│   ├── jobs.json              # Job catalog
│   ├── vehicles.json          # Vehicle catalog
│   └── wheels.json            # Wheel catalog
├── gta_hub/                   # Core application package
│   ├── branding.py            # Theme constants (0xA855F7), embed factory, text sanitizers
│   ├── catalog.py             # Atomic CatalogStore, SequenceMatcher ranking, manual record addition
│   ├── config.py              # Strongly-typed Settings dataclass loaded from .env
│   ├── database.py            # aiosqlite manager, schema definitions, migrations, queries
│   ├── views.py               # Discord UI Components (HelpView, CatalogResultsView)
│   ├── cogs/                  # Application command extensions
│   │   ├── admin.py           # /hubadmin owner suite (sync, reload, status, catalog sync)
│   │   ├── common.py          # Shared catalog search presentation logic
│   │   ├── community.py       # /community group (link, profile, stats)
│   │   ├── general.py         # /help, /ping, /invite, /support
│   │   ├── jobs.py            # /job and /creator command groups
│   │   ├── legacy.py          # /cars, /garage, /compare, /daily, /crew, /jobs, /profile, /stats
│   │   ├── vehicles.py        # /vehicle command group
│   │   ├── weather.py         # /weather command group
│   │   └── wheels.py          # /wheel command group
│   └── services/              # External service adapters
│       ├── catalog_sync.py    # Public dataset sync (gtacars.net & GTALens reference)
│       └── gta.py             # Legacy GTA service, vehicle search/autocomplete, Rockstar API
└── tests/                     # Automated unit test suite (49 tests)
    ├── test_catalog.py        # CatalogStore loading, ranking, and atomic persistence
    ├── test_catalog_sync.py   # Data normalization and source-merging tests
    ├── test_channel_restriction.py # Channel gating and bypass tests
    ├── test_command_sync.py   # CLI args and tree sync logic tests
    ├── test_community.py      # Profile linking and stats tests
    ├── test_gta_service.py    # Vehicle lookup and autocomplete tests
    └── test_legacy_cars.py    # /cars command and autocomplete tests
```

---

## Prerequisites

- **Python**: Version 3.11 or newer (Python 3.12 recommended; 3.14 compatible).
- **Discord Bot Token**: Obtained from the [Discord Developer Portal](https://discord.com/developers/applications).
- **OAuth2 Configuration**:
  - Scopes: `bot`, `applications.commands`
  - Permissions: Send Messages, Embed Links, Read Message History, Use Application Commands.

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Vomkar2024/GTA-V-HUB-DBot.git
cd GTA-V-HUB-DBot
```

### 2. Create and Activate a Virtual Environment

**Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example configuration file and update it with your credentials:

**Windows PowerShell:**
```powershell
Copy-Item .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Open `.env` in your text editor and set:
- `DISCORD_TOKEN`: Your bot token.
- `OWNER_IDS`: Your numeric Discord user ID (required to access `/hubadmin`).
- `GUILD_ID`: (Recommended for development) Your test server ID for instant command registration.

### 5. Launch the Bot

```bash
python bot.py
```

---

## Command Line Interface (CLI)

`bot.py` provides command-line flags to manage Discord slash command registration and resolve duplicate command issues without starting the gateway connection:

```bash
# Clear all global slash commands (resolves duplicate command issues in guilds)
python bot.py --clear-global

# Clear slash commands registered to the GUILD_ID specified in .env
python bot.py --clear-guild

# Synchronize slash commands to Discord and exit immediately without starting the gateway
python bot.py --sync-only

# Run the bot daemon normally
python bot.py
```

---

## Configuration Reference

The following variables can be configured in `.env`:

| Variable | Required | Default | Description |
|---|:---:|:---:|---|
| `DISCORD_TOKEN` | **Yes** | — | Bot token from the Discord Developer Portal. |
| `GUILD_ID` | No | *None* | Target guild ID for instant slash command registration during development. If unset, commands sync globally. |
| `CLEAR_GLOBAL_ON_STARTUP` | No | `false` | When `true` and `GUILD_ID` is set, purges global commands on startup to eliminate duplicate slash commands. |
| `ENABLE_LEGACY_COMMANDS` | No | `true` | Enables legacy/starter commands (`/cars`, `/garage`, `/compare`, `/daily`, `/profile`, `/stats`, `/crew`, `/jobs`). |
| `OWNER_IDS` | No | *None* | Comma-separated list of Discord user IDs authorized to use `/hubadmin` tools. |
| `ALLOWED_CHANNEL_ID` | No | `1567917854341472387` | Comma- or semicolon-separated channel IDs where standard bot commands are allowed. Leave empty to allow commands in all channels. |
| `INVITE_URL` | No | *None* | Bot OAuth2 invite URL displayed by `/invite` and the `/help` menu button. |
| `SUPPORT_URL` | No | *None* | Support server invite URL or website displayed by `/support` and `/help`. |
| `DONATE_URL` | No | *None* | Optional developer support/donation link displayed by `/support` and `/help`. |
| `DATA_DIR` | No | `data` | Directory containing JSON catalogs and database storage. |
| `DATABASE_PATH` | No | `data/gtavhub.sqlite3` | File path for the SQLite database. |
| `GTA_HUB_WEATHER_API_URL` | No | *None* | Optional HTTPS JSON endpoint for live GTA Online weather data. |
| `GTA_HUB_SYNC_API_URL` | No | *None* | Optional HTTPS endpoint to resolve Rockstar Social Club job URLs. |
| `LOG_LEVEL` | No | `INFO` | Python logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`). |

> [!WARNING]
> Never commit your `.env` file, bot tokens, API keys, or private user databases to public repositories.

---

## Channel Restriction & Access Control

The bot includes built-in channel isolation to prevent spam across general server channels:

1. **Configuring Channels**: Set `ALLOWED_CHANNEL_ID` in `.env`. You can specify a single channel ID or multiple comma/semicolon-separated IDs:
   ```env
   ALLOWED_CHANNEL_ID=123456789012345678,987654321098765432
   ```
2. **Disabling Restriction**: Leave `ALLOWED_CHANNEL_ID=` empty to permit command execution across all server channels.
3. **Thread Inheritance**: Commands issued inside active threads automatically check against the thread's parent channel ID.
4. **Owner Exemption**: All commands under the `/hubadmin` command group are exempt from channel restrictions and can be executed from private administrative channels.
5. **User Feedback**: Non-admin commands executed in an unauthorized channel receive an ephemeral response detailing the approved channel mentions.

---

## Command Reference

### General Commands

| Command | Arguments | Description |
|---|---|---|
| `/help` | — | Opens the interactive GTA V HUB Command Center with category dropdown and resource buttons. |
| `/ping` | — | Checks Discord WebSocket gateway latency in milliseconds. |
| `/invite` | — | Displays the configured bot invite link. |
| `/support` | — | Displays community support and donation links. |

### Vehicles & Wheels

| Command | Arguments | Description |
|---|---|---|
| `/vehicle search` | `query: str` | Search vehicles by name or manufacturer with an interactive details menu. |
| `/vehicle class` | `name: str` | Browse vehicles within a specific class (e.g., `Sports`, `Super`, `Muscle`). |
| `/vehicle tier` | `class_name: str`, `tier: str` | Filter vehicles in a class by performance tier (e.g., `Sports`, tier `A`). |
| `/wheel search` | `query: str` | Search wheels by name with an interactive details menu. |
| `/wheel type` | `name: str` | List wheels belonging to a specific wheel type (e.g., `Sport`, `SUV`, `Tuner`). |
| `/wheel effects` | `[wheel_type]`, `[traction_bias]`, `[anti_roll]`, `[slip_angle]` | Filter wheels by handling characteristics and physics modifiers. |

### Jobs & Creators

| Command | Arguments | Description |
|---|---|---|
| `/job search` | `query: str` | Search the local job catalog by job title or creator name. |
| `/job random` | — | Picks and displays a random job from `data/jobs.json`. |
| `/job sync` | `url: str` | Resolves a Rockstar Social Club job URL via the configured provider (`GTA_HUB_SYNC_API_URL`). |
| `/creator search` | `query: str` | Search content creators in `data/creators.json`. |
| `/creator playlists`| `name: str` | Displays published job playlists for a content creator. |

### Community, Garage & Economy

| Command | Arguments | Description |
|---|---|---|
| `/community link` | `rockstar_name: str`, `platform: Choice[PC, PlayStation, Xbox]` | Links your Rockstar Social Club name and platform to your Discord account. |
| `/community profile` | `[member: discord.Member]` | Displays the linked community profile of yourself or another member. |
| `/community stats` | `[member: discord.Member]` | Displays community activity: total HUB credits, daily claims, streak, and last claim time. |
| `/garage` | `action: Choice[view, add, remove]`, `[vehicle: str]` | Manages your personal vehicle collection stored in SQLite. |
| `/compare` | `vehicle_one: str`, `vehicle_two: str` | Performs a side-by-side performance and specification comparison between two vehicles. |
| `/daily` | — | Claims daily HUB community credits (100–250 credits/day, streak bonus, resets at 00:00 UTC). |

### Legacy & Lookups

Enabled when `ENABLE_LEGACY_COMMANDS=true`:

| Command | Arguments | Description |
|---|---|---|
| `/cars name` | `query: str` (with autocomplete) | Search vehicles by name with dynamic autocomplete suggestions. |
| `/cars manufacturer` | `query: str` (with autocomplete) | Search vehicles by manufacturer with dynamic autocomplete suggestions. |
| `/cars class` | `query: str` (with autocomplete) | Search vehicles by class with dynamic autocomplete suggestions. |
| `/profile` | `player: str` | Player profile lookup (indicates requirement for a permitted external provider). |
| `/stats` | `player: str` | Player statistics lookup (indicates requirement for a permitted external provider). |
| `/crew` | `crew_id: str` | Queries the Rockstar Social Club crew membership API (best-effort). |
| `/jobs` | `creator_id: str` | Queries the Rockstar Social Club creator race mission API (best-effort). |

### Owner & Administration (`/hubadmin`)

Restricted to user IDs specified in `OWNER_IDS`. Allowed in any channel:

| Command | Arguments | Description |
|---|---|---|
| `/hubadmin status` | — | Displays bot uptime, guild count, gateway latency, catalog counts, and recent sync history. |
| `/hubadmin reload-catalogs` | — | Hot-reloads all local JSON catalogs from disk without restarting the bot process. |
| `/hubadmin sync` | `mode: Choice[clear-global, guild, global, clear-guild]` | Manages Discord application command tree registration and resolves duplicate commands. |
| `/hubadmin sync-catalogs` | `catalogue: Choice[all, vehicles, wheels]` | Imports public datasets from GTACars API and the GTALens wheel reference. |
| `/hubadmin add-vehicle` | `manufacturer: str`, `name: str`, `vehicle_class: str`, `price: int`, `[drivetrain: str]` | Manually appends a vehicle entry to `data/vehicles.json` atomically. |

---

## Catalog Data & Schema

Catalog data is stored as JSON arrays in `data/`. If a catalog file does not exist at startup, an empty array (`[]`) is generated. All manual additions and automated imports write through temporary files (`tempfile.mkstemp`) and replace existing files atomically (`os.replace`) to prevent file corruption.

### `data/vehicles.json`
```json
[
  {
    "name": "T20",
    "manufacturer": "Progen",
    "class": "Super",
    "tier": "S",
    "price": 2200000,
    "drivetrain": "AWD",
    "top_speed": 122.25,
    "lap_time": 61.89,
    "seats": 2,
    "url": "https://gtacars.net/gta5/t20",
    "image_url": "https://example.com/t20.png",
    "_catalog_source": "gtacars"
  }
]
```

### `data/wheels.json`
```json
[
  {
    "name": "Challenger",
    "type": "Muscle",
    "price": "$15,200",
    "suggested": "Recommended",
    "traction_bias": "rear",
    "anti_roll": "+",
    "slip_angle": "-",
    "description": "Increases rear traction bias while stabilizing corner exit.",
    "_catalog_source": "gtalens-wheel-reference"
  }
]
```

### `data/jobs.json`
```json
[
  {
    "name": "Cayo Perico GP",
    "creator": "TrackMaster",
    "platform": "PC",
    "url": "https://socialclub.rockstargames.com/job/gtav/example",
    "description": "High-speed stunt race around the island."
  }
]
```

### `data/creators.json`
```json
[
  {
    "name": "TrackMaster",
    "platform": "PC",
    "url": "https://socialclub.rockstargames.com/member/TrackMaster",
    "playlists": [
      {
        "name": "Stunt Series 2026",
        "url": "https://socialclub.rockstargames.com/games/gtav/pc/playlists/playlist/example"
      }
    ]
  }
]
```

---

## Public Catalogue Sync

The `/hubadmin sync-catalogs` command provides manual ingestion from public endpoints:

- **Vehicles**: Fetched from the public GTACars paginated API (`gtacars.net`). Ingestion runs with a 0.75-second rate-limiting delay between pages.
- **Wheels**: Downloaded from the public GTALens reference repository (`wheels.json`).

### Provenance & Deduplication
- Records imported from public providers are tagged with `_catalog_source`.
- Re-running the sync replaces only records previously imported from that specific provider, preserving any custom or manual records created with `/hubadmin add-vehicle` or labeled with `_catalog_source="manual"`.
- Sync runs with a descriptive `User-Agent` header and does not employ proxy rotation, credential harvesting, or scraping bypasses.

---

## Optional Provider Contracts

Live weather and job resolution require optional self-hosted or permitted third-party HTTPS endpoints.

### Weather Provider (`GTA_HUB_WEATHER_API_URL`)

The endpoint must return an HTTP 200 JSON response matching this schema:

```json
{
  "weather": "Clear",
  "details": "Sunny across Los Santos and Blaine County",
  "game_time": "14:20",
  "next_change": "in 12 minutes"
}
```

### Job Sync Provider (`GTA_HUB_SYNC_API_URL`)

The bot sends an HTTP GET request with a `url` query parameter containing the Rockstar Social Club job URL (`?url=https://socialclub.rockstargames.com/job/...`). The provider must return an HTTP 200 JSON response matching this schema:

```json
{
  "name": "Stunt - Canyon Drop",
  "creator": "SpeedDemon",
  "platform": "PC",
  "url": "https://socialclub.rockstargames.com/job/gtav/example",
  "description": "Precision stunt race descending Mount Chiliad."
}
```

> [!NOTE]
> The bot validates that the supplied URL belongs to the `rockstargames.com` domain before dispatching the request.

---

## Development & Testing

### Running Tests

The test suite contains 49 automated unit tests verifying catalog operations, sync adapters, channel restrictions, command tree synchronization, and autocomplete handlers.

Run using Python's built-in `unittest`:
```bash
python -m unittest discover -s tests -v
```

Or run using `pytest`:
```bash
python -m pytest
```

### Bytecode Compilation & Syntax Check

Verify that all modules compile cleanly:
```bash
python -m compileall -q bot.py gta_hub tests
```

### Continuous Integration (CI)

A GitHub Actions workflow is located at `.github/workflows/ci.yml`. It runs automatically on every push and pull request against Python 3.12, executing dependency installation, the unit test suite, and syntax verification.

---

## Contributing

Contributions to GTA V HUB are welcome. Please follow these steps:

1. **Fork the Repository** to your GitHub account.
2. **Create a Feature Branch**:
   ```bash
   git checkout -b feature/my-new-feature
   ```
3. **Commit Your Changes**: Follow clear and concise commit conventions.
4. **Run the Test Suite**: Ensure all 49 tests pass and add new tests for your feature:
   ```bash
   python -m unittest discover -s tests -v
   python -m compileall -q bot.py gta_hub tests
   ```
5. **Open a Pull Request**: Provide a detailed description of your changes and reference any related issues.

---

## Credits & Disclaimers

### Upstream References
- Architectural inspiration and catalog taxonomy were informed by the public [nosv1/GTALens](https://github.com/nosv1/GTALens) repository.
- This repository is an independent, clean-room implementation. It does **not** redistribute original source code, proprietary datasets, or third-party graphic assets from the GTALens project.

### Legal Disclaimer
- **Grand Theft Auto V**, **GTA Online**, **Rockstar Games**, and associated logos and marks are trademarks or registered trademarks of Take-Two Interactive Software, Inc. and Rockstar Games.
- **GTA V HUB** is an independent, unofficial open-source community companion and is not affiliated with, endorsed by, or sponsored by Rockstar Games or Take-Two Interactive.
- In-game rewards, profiles, and currency tracked in the bot are Discord-specific community points and bear no affiliation with in-game GTA$.

### License
This project is open-source software licensed under the [MIT License](LICENSE).
