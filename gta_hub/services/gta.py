"""GTA data adapters. Live Rockstar endpoints are undocumented and best-effort."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiohttp
import discord



class GTAService:
    def __init__(self, data_file: Path) -> None:
        self.data_file = Path(data_file)
        self.vehicles: list[dict[str, Any]] = self._load_vehicles()

    def _load_vehicles(self) -> list[dict[str, Any]]:
        if not self.data_file.exists():
            return []
        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        if isinstance(data, dict):
            return [v for v in data.values() if isinstance(v, dict)]
        if isinstance(data, list):
            return [v for v in data if isinstance(v, dict)]
        return []

    def search_vehicles(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        query = query.casefold().strip()
        if not query:
            return []
        ranked = []
        for vehicle in self.vehicles:
            name = str(vehicle.get("name", ""))
            searchable = " ".join(
                [name, str(vehicle.get("manufacturer", "")), str(vehicle.get("vehicle_class", vehicle.get("class", "")))]
            ).casefold()
            if query in searchable:
                score = 0 if name.casefold() == query else 1 if name.casefold().startswith(query) else 2
                ranked.append((score, name.casefold(), vehicle))
        ranked.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in ranked[:limit]]

    def find_vehicle(self, query: str) -> dict[str, Any] | None:
        matches = self.search_vehicles(query, limit=1)
        return matches[0] if matches else None

    @staticmethod
    def value(data: dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = data.get(key)
            if value not in (None, "", "None"):
                return str(value)
        return "Not available"

    def vehicle_list_embed(self, vehicles: list[dict[str, Any]]) -> discord.Embed:
        embed = discord.Embed(title="GTA Online Vehicles", color=0xE85D24)
        for vehicle in vehicles[:8]:
            embed.add_field(
                name=self.value(vehicle, "name")[:256],
                value=(
                    f"**Make:** {self.value(vehicle, 'manufacturer')}\n"
                    f"**Class:** {self.value(vehicle, 'vehicle_class')}\n"
                    f"**Price:** {self.value(vehicle, 'cost')}"
                )[:1024],
                inline=True,
            )
        embed.set_footer(text="Bundled reference data; verify availability and prices in-game.")
        return embed

    def compare_embed(self, first: dict[str, Any], second: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(title="Vehicle comparison", color=0xE85D24)
        fields = [
            ("Manufacturer", ("manufacturer",)),
            ("Class", ("vehicle_class", "class")),
            ("Price", ("cost",)),
            ("Drivetrain", ("drivetrain",)),
            ("Seats", ("seats",)),
            ("Top speed", ("top_speed_mph", "max_speed")),
            ("Lap time", ("lap_time",)),
            ("Race tier", ("race_tier",)),
            ("Storage", ("storage",)),
        ]
        for vehicle in (first, second):
            lines = [f"**{label}:** {self.value(vehicle, *keys)}" for label, keys in fields]
            embed.add_field(
                name=self.value(vehicle, "name")[:256], value="\n".join(lines)[:1024], inline=True
            )
        return embed

    def garage_embed(self, rows: list[tuple[str, str]], user: discord.abc.User) -> discord.Embed:
        embed = discord.Embed(title=f"{user.display_name}'s Garage", color=0xE85D24)
        embed.description = (
            "\n".join(f"• {name}" for name, _ in rows[:40])
            if rows
            else "Your garage is empty. Add vehicles with /garage."
        )
        if rows:
            embed.set_footer(text=f"{len(rows)} vehicle(s) saved")
        return embed

    async def _get_json(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        timeout = aiohttp.ClientTimeout(total=12)
        headers = {"User-Agent": "GTA-V-HUB-Discord-Bot/1.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                payload = await response.json(content_type=None)
                if not isinstance(payload, dict):
                    raise ValueError("Unexpected Rockstar response format")
                return payload

    async def player_profile(self, player: str) -> dict[str, str]:
        return {
            "query": player,
            "message": (
                "Rockstar does not provide a documented public endpoint for arbitrary "
                "GTA Online player profiles. This command will show real profile data "
                "only after a supported, permitted data provider is configured."
            ),
        }

    async def player_stats(self, player: str) -> dict[str, str]:
        return await self.player_profile(player)

    @staticmethod
    def profile_embed(data: dict[str, str]) -> discord.Embed:
        embed = discord.Embed(title=f"Player profile: {data['query']}", color=0xE85D24)
        embed.description = data["message"]
        embed.set_footer(text="No Rockstar credentials or private account data are collected.")
        return embed

    @staticmethod
    def stats_embed(data: dict[str, str]) -> discord.Embed:
        return GTAService.profile_embed(data)

    async def crew_info(self, crew_id: str) -> dict[str, Any]:
        try:
            payload = await self._get_json(
                "https://scapi.rockstargames.com/crew/ranksWithMembership",
                {
                    "crewId": crew_id,
                    "onlineService": "sc",
                    "searchTerm": "",
                    "memberCountToRetrieve": 1,
                },
            )
            return {"query": crew_id, "payload": payload}
        except (aiohttp.ClientError, ValueError, TimeoutError) as exc:
            return {"query": crew_id, "error": str(exc)}

    @staticmethod
    def crew_embed(data: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(title=f"Crew lookup: {data['query']}", color=0xE85D24)
        if data.get("error"):
            embed.description = f"Rockstar service error: {data['error'][:250]}"
            return embed
        payload = data.get("payload", {})
        # Rockstar's legacy response is not a documented stable API. Display only validated fields.
        ranks = payload.get("crewRanks", []) if isinstance(payload, dict) else []
        embed.description = f"Crew response received. Rank groups returned: **{len(ranks)}**."
        embed.set_footer(text="Legacy Rockstar endpoint; details may vary or become unavailable.")
        return embed

    async def jobs_by_creator(self, creator_id: str) -> dict[str, Any]:
        try:
            payload = await self._get_json(
                "https://scapi.rockstargames.com/search/mission",
                {
                    "dateRange": "any",
                    "sort": "date",
                    "platform": "pc",
                    "title": "gtav",
                    "missiontype": "race",
                    "creatorRockstarId": creator_id,
                    "pageIndex": 0,
                    "pageSize": 8,
                },
            )
            return {"query": creator_id, "payload": payload}
        except (aiohttp.ClientError, ValueError, TimeoutError) as exc:
            return {"query": creator_id, "error": str(exc)}

    @staticmethod
    def jobs_embed(data: dict[str, Any]) -> discord.Embed:
        embed = discord.Embed(title=f"Creator jobs: {data['query']}", color=0xE85D24)
        if data.get("error"):
            embed.description = f"Rockstar job lookup unavailable: {data['error'][:250]}"
            return embed
        payload = data.get("payload", {})
        content = payload.get("content", {}) if isinstance(payload, dict) else {}
        items = content.get("items", []) if isinstance(content, dict) else []
        if not items:
            embed.description = "No jobs returned. Check the creator ID and Rockstar service availability."
        for item in items[:8]:
            name = str(item.get("name", "Untitled job"))[:256]
            job_id = str(item.get("id", "unknown"))
            embed.add_field(name=name, value=f"Rockstar job ID: `{job_id[:100]}`", inline=False)
        embed.set_footer(text="Legacy Rockstar endpoint; this lookup is limited to PC races by creator ID.")
        return embed
