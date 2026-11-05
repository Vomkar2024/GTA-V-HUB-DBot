"""SQLite persistence for garages and daily HUB rewards."""
from __future__ import annotations

import asyncio
import math
import os
import random
from datetime import datetime, timedelta, timezone

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None
        self._claim_lock = asyncio.Lock()

    async def initialize(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
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
                total_credits INTEGER NOT NULL DEFAULT 0
            );
            """
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
            (str(user_id), vehicle_name),
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
                    (now.date() - datetime.fromisoformat(row[0]).date()).days if row else 0
                )
                streak = row[1] + 1 if row and days_since_last == 1 else 1
                total = (row[2] if row else 0) + reward

                await conn.execute(
                    """INSERT INTO daily_claims(discord_user_id, claimed_on, streak, total_credits)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(discord_user_id) DO UPDATE SET
                         claimed_on=excluded.claimed_on,
                         streak=excluded.streak,
                         total_credits=excluded.total_credits""",
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
