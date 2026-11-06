"""SQLite persistence for garages, player profiles, and daily HUB rewards."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
import random
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self.conn: aiosqlite.Connection | None = None
        self._claim_lock = asyncio.Lock()

    async def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        await self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS garages (
                discord_user_id TEXT NOT NULL,
                vehicle_name TEXT NOT NULL,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (discord_user_id, vehicle_name)
            );
            CREATE TABLE IF NOT EXISTS daily_claims (
                discord_user_id TEXT PRIMARY KEY,
                claimed_on TEXT NOT NULL,
                streak INTEGER NOT NULL DEFAULT 1,
                total_credits INTEGER NOT NULL DEFAULT 0,
                claim_count INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS profiles (
                discord_user_id TEXT PRIMARY KEY,
                rockstar_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                linked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        # Safe additive migration for databases created by earlier schema versions.
        async with self.conn.execute("PRAGMA table_info(daily_claims)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "claim_count" not in columns:
            await self.conn.execute(
                "ALTER TABLE daily_claims ADD COLUMN claim_count INTEGER NOT NULL DEFAULT 0"
            )
        await self.conn.commit()

    def _connection(self) -> aiosqlite.Connection:
        if self.conn is None:
            raise RuntimeError("Database has not been initialized")
        return self.conn

    async def get_garage(self, user_id: int) -> list[tuple[str, str]]:
        conn = self._connection()
        async with conn.execute(
            "SELECT vehicle_name, added_at FROM garages "
            "WHERE discord_user_id=? ORDER BY added_at DESC",
            (str(user_id),),
        ) as cursor:
            return await cursor.fetchall()

    async def add_garage(self, user_id: int, vehicle_name: str) -> None:
        conn = self._connection()
        await conn.execute(
            "INSERT OR IGNORE INTO garages(discord_user_id, vehicle_name) VALUES (?, ?)",
            (str(user_id), vehicle_name.strip()),
        )
        await conn.commit()

    async def remove_garage(self, user_id: int, vehicle_name: str) -> bool:
        conn = self._connection()
        cursor = await conn.execute(
            "DELETE FROM garages WHERE discord_user_id=? AND lower(vehicle_name)=lower(?)",
            (str(user_id), vehicle_name.strip()),
        )
        await conn.commit()
        return cursor.rowcount > 0

    async def set_profile(self, user_id: int, rockstar_name: str, platform: str) -> None:
        conn = self._connection()
        await conn.execute(
            """INSERT INTO profiles(discord_user_id, rockstar_name, platform)
               VALUES (?, ?, ?)
               ON CONFLICT(discord_user_id) DO UPDATE SET
                 rockstar_name=excluded.rockstar_name,
                 platform=excluded.platform,
                 linked_at=CURRENT_TIMESTAMP""",
            (str(user_id), rockstar_name.strip(), platform.strip()),
        )
        await conn.commit()

    async def get_profile(self, user_id: int) -> tuple[str, str] | None:
        conn = self._connection()
        async with conn.execute(
            "SELECT rockstar_name, platform FROM profiles WHERE discord_user_id=?",
            (str(user_id),),
        ) as cursor:
            return await cursor.fetchone()

    async def get_community_stats(self, user_id: int) -> dict[str, Any] | None:
        conn = self._connection()
        async with conn.execute(
            "SELECT claimed_on, streak, total_credits, claim_count "
            "FROM daily_claims WHERE discord_user_id=?",
            (str(user_id),),
        ) as cursor:
            row = await cursor.fetchone()
        if not row:
            return None
        return {
            "last_claim": row[0],
            "streak": row[1],
            "total_credits": row[2],
            "claim_count": row[3],
        }

    async def claim_daily(self, user_id: int) -> dict[str, int | bool]:
        """Atomically allow at most one daily claim per UTC calendar day."""
        conn = self._connection()
        async with self._claim_lock:
            now = datetime.now(timezone.utc)
            today = now.date().isoformat()
            await conn.execute("BEGIN IMMEDIATE")
            try:
                async with conn.execute(
                    "SELECT claimed_on, streak, total_credits FROM daily_claims "
                    "WHERE discord_user_id=?",
                    (str(user_id),),
                ) as cursor:
                    row = await cursor.fetchone()

                if row and row[0] == today:
                    next_midnight = (now + timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    hours_left = max(1, math.ceil((next_midnight - now).total_seconds() / 3600))
                    await conn.commit()
                    return {"claimed": False, "hours_left": hours_left, "reward": 0}

                reward = random.randint(100, 250)
                days_since_last = (
                    (now.date() - date.fromisoformat(row[0])).days if row else 0
                )
                streak = row[1] + 1 if row and days_since_last == 1 else 1
                total = (row[2] if row else 0) + reward

                await conn.execute(
                    """INSERT INTO daily_claims(discord_user_id, claimed_on, streak, total_credits, claim_count)
                       VALUES (?, ?, ?, ?, 1)
                       ON CONFLICT(discord_user_id) DO UPDATE SET
                         claimed_on=excluded.claimed_on,
                         streak=excluded.streak,
                         total_credits=excluded.total_credits,
                         claim_count=daily_claims.claim_count+1""",
                    (str(user_id), today, streak, total),
                )
                await conn.commit()
                return {"claimed": True, "reward": reward, "streak": streak, "total": total}
            except Exception:
                await conn.rollback()
                raise

    async def close(self) -> None:
        if self.conn is not None:
            await self.conn.close()
            self.conn = None
