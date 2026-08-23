"""Small persistent store for tickets and server configuration."""

from __future__ import annotations

import aiosqlite


class Database:
    def __init__(self, path: str = "nexus.db") -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tickets (
                    channel_id INTEGER PRIMARY KEY,
                    guild_id INTEGER NOT NULL,
                    owner_id INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_open_ticket
                    ON tickets(guild_id, owner_id, status);
                CREATE TABLE IF NOT EXISTS panels (
                    guild_id INTEGER NOT NULL,
                    panel_key TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, panel_key)
                );
                """
            )
            await db.commit()

    async def open_ticket_for(self, guild_id: int, owner_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT channel_id FROM tickets WHERE guild_id=? AND owner_id=? AND status='open' LIMIT 1",
                (guild_id, owner_id),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def create_ticket(self, channel_id: int, guild_id: int, owner_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO tickets(channel_id, guild_id, owner_id, status) VALUES (?, ?, ?, 'open')",
                (channel_id, guild_id, owner_id),
            )
            await db.commit()

    async def ticket_owner(self, channel_id: int) -> int | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT owner_id FROM tickets WHERE channel_id=?", (channel_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None

    async def close_ticket(self, channel_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (channel_id,))
            await db.commit()

    async def panel_message(self, guild_id: int, panel_key: str) -> tuple[int, int] | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(
                "SELECT channel_id, message_id FROM panels WHERE guild_id=? AND panel_key=?",
                (guild_id, panel_key),
            ) as cursor:
                row = await cursor.fetchone()
                return (row[0], row[1]) if row else None

    async def save_panel(self, guild_id: int, panel_key: str, channel_id: int, message_id: int) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO panels(guild_id, panel_key, channel_id, message_id) VALUES (?, ?, ?, ?)",
                (guild_id, panel_key, channel_id, message_id),
            )
            await db.commit()
