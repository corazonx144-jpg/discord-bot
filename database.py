from __future__ import annotations

import aiosqlite


class Database:
    """Persistent state. Use Postgres instead of SQLite for a 24/7 production host."""
    def __init__(self, path: str = "nexus.db") -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS tickets (channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open');
                CREATE TABLE IF NOT EXISTS panels (guild_id INTEGER NOT NULL, panel_key TEXT NOT NULL, channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL, PRIMARY KEY(guild_id, panel_key));
                CREATE TABLE IF NOT EXISTS verification_requests (guild_id INTEGER NOT NULL, member_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(guild_id, member_id));
                CREATE TABLE IF NOT EXISTS clearance_requests (guild_id INTEGER NOT NULL, member_id INTEGER NOT NULL, role_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(guild_id, member_id));
                CREATE TABLE IF NOT EXISTS temporary_rooms (channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, expires_at INTEGER NOT NULL);
            """)
            await db.commit()

    async def one(self, query: str, params: tuple) -> tuple | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def execute(self, query: str, params: tuple) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(query, params)
            await db.commit()

    async def open_ticket_for(self, guild_id: int, owner_id: int) -> int | None:
        row = await self.one("SELECT channel_id FROM tickets WHERE guild_id=? AND owner_id=? AND status='open' LIMIT 1", (guild_id, owner_id))
        return row[0] if row else None
    async def create_ticket(self, channel_id: int, guild_id: int, owner_id: int) -> None: await self.execute("INSERT OR REPLACE INTO tickets(channel_id,guild_id,owner_id,status) VALUES(?,?,?,'open')", (channel_id,guild_id,owner_id))
    async def ticket_owner(self, channel_id: int) -> int | None:
        row = await self.one("SELECT owner_id FROM tickets WHERE channel_id=?", (channel_id,)); return row[0] if row else None
    async def close_ticket(self, channel_id: int) -> None: await self.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (channel_id,))
    async def panel_message(self, guild_id: int, key: str) -> tuple[int, int] | None:
        row = await self.one("SELECT channel_id,message_id FROM panels WHERE guild_id=? AND panel_key=?", (guild_id,key)); return (row[0],row[1]) if row else None
    async def save_panel(self, guild_id: int, key: str, channel_id: int, message_id: int) -> None: await self.execute("INSERT OR REPLACE INTO panels VALUES(?,?,?,?)", (guild_id,key,channel_id,message_id))
    async def verification_status(self, guild_id: int, member_id: int) -> str | None:
        row = await self.one("SELECT status FROM verification_requests WHERE guild_id=? AND member_id=?", (guild_id,member_id)); return row[0] if row else None
    async def set_verification_status(self, guild_id: int, member_id: int, status: str) -> None: await self.execute("INSERT OR REPLACE INTO verification_requests VALUES(?,?,?)", (guild_id,member_id,status))
    async def clearance_status(self, guild_id: int, member_id: int) -> tuple[str, str] | None:
        row = await self.one("SELECT role_name,status FROM clearance_requests WHERE guild_id=? AND member_id=?", (guild_id,member_id)); return (row[0],row[1]) if row else None
    async def set_clearance_status(self, guild_id: int, member_id: int, role_name: str, status: str) -> None: await self.execute("INSERT OR REPLACE INTO clearance_requests VALUES(?,?,?,?)", (guild_id,member_id,role_name,status))
    async def add_room(self, channel_id: int, guild_id: int, owner_id: int, expires_at: int) -> None: await self.execute("INSERT OR REPLACE INTO temporary_rooms VALUES(?,?,?,?)", (channel_id,guild_id,owner_id,expires_at))
    async def room(self, channel_id: int) -> tuple[int,int] | None:
        row = await self.one("SELECT owner_id,expires_at FROM temporary_rooms WHERE channel_id=?", (channel_id,)); return (row[0],row[1]) if row else None
    async def expired_rooms(self, now: int) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT channel_id FROM temporary_rooms WHERE expires_at<=?", (now,)) as cursor: return [row[0] for row in await cursor.fetchall()]
    async def remove_room(self, channel_id: int) -> None: await self.execute("DELETE FROM temporary_rooms WHERE channel_id=?", (channel_id,))
