from __future__ import annotations

import aiosqlite
import json

class Database:
    """Persistent state. Use Postgres instead of SQLite for a 24/7 production host."""
    def __init__(self, path: str = "nexus.db") -> None:
        self.path = path

    async def initialize(self) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executescript("""
                PRAGMA journal_mode=WAL;

                -- Core tables
                CREATE TABLE IF NOT EXISTS tickets (channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'open');
                CREATE TABLE IF NOT EXISTS panels (guild_id INTEGER NOT NULL, panel_key TEXT NOT NULL, channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL, PRIMARY KEY(guild_id, panel_key));
                CREATE TABLE IF NOT EXISTS verification_requests (guild_id INTEGER NOT NULL, member_id INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(guild_id, member_id));
                CREATE TABLE IF NOT EXISTS clearance_requests (guild_id INTEGER NOT NULL, member_id INTEGER NOT NULL, role_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', PRIMARY KEY(guild_id, member_id));
                CREATE TABLE IF NOT EXISTS temporary_rooms (channel_id INTEGER PRIMARY KEY, guild_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, expires_at INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS member_stages (guild_id INTEGER NOT NULL, member_id INTEGER NOT NULL, stage TEXT NOT NULL DEFAULT 'arrival', PRIMARY KEY(guild_id, member_id));

                -- Moderation
                CREATE TABLE IF NOT EXISTS warnings (case_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, moderator_id INTEGER NOT NULL, reason TEXT NOT NULL, timestamp REAL NOT NULL);
                CREATE TABLE IF NOT EXISTS bans (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, moderator_id INTEGER NOT NULL, reason TEXT, timestamp REAL NOT NULL, PRIMARY KEY(guild_id, user_id));
                CREATE TABLE IF NOT EXISTS timeouts (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, moderator_id INTEGER NOT NULL, reason TEXT, until REAL NOT NULL, timestamp REAL NOT NULL, PRIMARY KEY(guild_id, user_id));

                -- Economy
                CREATE TABLE IF NOT EXISTS economy (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, wallet INTEGER NOT NULL DEFAULT 0, bank INTEGER NOT NULL DEFAULT 0, daily_timestamp REAL NOT NULL DEFAULT 0, PRIMARY KEY(guild_id, user_id));

                -- Leveling
                CREATE TABLE IF NOT EXISTS leveling (guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, xp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 0, total_messages INTEGER NOT NULL DEFAULT 0, voice_minutes INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(guild_id, user_id));

                -- Starboard
                CREATE TABLE IF NOT EXISTS starboard (guild_id INTEGER NOT NULL, message_id INTEGER NOT NULL, channel_id INTEGER NOT NULL, author_id INTEGER NOT NULL, content TEXT, star_count INTEGER NOT NULL DEFAULT 0, posted_message_id INTEGER, PRIMARY KEY(guild_id, message_id));

                -- Reaction Roles
                CREATE TABLE IF NOT EXISTS reaction_roles (guild_id INTEGER NOT NULL, message_id INTEGER NOT NULL, emoji TEXT NOT NULL, role_id INTEGER NOT NULL, PRIMARY KEY(guild_id, message_id, emoji));

                -- Polls
                CREATE TABLE IF NOT EXISTS polls (guild_id INTEGER NOT NULL, message_id INTEGER PRIMARY KEY, channel_id INTEGER NOT NULL, author_id INTEGER NOT NULL, question TEXT NOT NULL, options TEXT NOT NULL, votes TEXT NOT NULL DEFAULT '{}', active INTEGER NOT NULL DEFAULT 1);

                -- Suggestions
                CREATE TABLE IF NOT EXISTS suggestions (suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, user_id INTEGER NOT NULL, content TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', upvotes INTEGER NOT NULL DEFAULT 0, downvotes INTEGER NOT NULL DEFAULT 0, timestamp REAL NOT NULL);

                -- AutoMod Config
                CREATE TABLE IF NOT EXISTS automod_config (guild_id INTEGER PRIMARY KEY, anti_spam INTEGER NOT NULL DEFAULT 0, anti_link INTEGER NOT NULL DEFAULT 0, anti_caps INTEGER NOT NULL DEFAULT 0, spam_threshold INTEGER NOT NULL DEFAULT 5, mute_duration INTEGER NOT NULL DEFAULT 300);

                -- Audit Log
                CREATE TABLE IF NOT EXISTS audit_log (log_id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, action TEXT NOT NULL, user_id INTEGER, target_id INTEGER, reason TEXT, details TEXT, timestamp REAL NOT NULL);
            """)
            await db.commit()

    async def one(self, query: str, params: tuple) -> tuple | None:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def all(self, query: str, params: tuple) -> list:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()

    async def execute(self, query: str, params: tuple) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.execute(query, params)
            await db.commit()

    async def execute_many(self, query: str, params: list) -> None:
        async with aiosqlite.connect(self.path) as db:
            await db.executemany(query, params)
            await db.commit()

    async def last_row_id(self, query: str, params: tuple) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(query, params)
            await db.commit()
            return cursor.lastrowid

    # ── Tickets ──
    async def open_ticket_for(self, guild_id: int, owner_id: int) -> int | None:
        row = await self.one("SELECT channel_id FROM tickets WHERE guild_id=? AND owner_id=? AND status='open' LIMIT 1", (guild_id, owner_id))
        return row[0] if row else None
    async def create_ticket(self, channel_id: int, guild_id: int, owner_id: int) -> None:
        await self.execute("INSERT OR REPLACE INTO tickets(channel_id,guild_id,owner_id,status) VALUES(?,?,?,'open')", (channel_id,guild_id,owner_id))
    async def ticket_owner(self, channel_id: int) -> int | None:
        row = await self.one("SELECT owner_id FROM tickets WHERE channel_id=?", (channel_id,)); return row[0] if row else None
    async def close_ticket(self, channel_id: int) -> None:
        await self.execute("UPDATE tickets SET status='closed' WHERE channel_id=?", (channel_id,))

    # ── Panels ──
    async def panel_message(self, guild_id: int, key: str) -> tuple[int, int] | None:
        row = await self.one("SELECT channel_id,message_id FROM panels WHERE guild_id=? AND panel_key=?", (guild_id,key)); return (row[0],row[1]) if row else None
    async def save_panel(self, guild_id: int, key: str, channel_id: int, message_id: int) -> None:
        await self.execute("INSERT OR REPLACE INTO panels VALUES(?,?,?,?)", (guild_id,key,channel_id,message_id))

    # ── Verification ──
    async def verification_status(self, guild_id: int, member_id: int) -> str | None:
        row = await self.one("SELECT status FROM verification_requests WHERE guild_id=? AND member_id=?", (guild_id,member_id)); return row[0] if row else None
    async def set_verification_status(self, guild_id: int, member_id: int, status: str) -> None:
        await self.execute("INSERT OR REPLACE INTO verification_requests VALUES(?,?,?)", (guild_id,member_id,status))

    # ── Clearance ──
    async def clearance_status(self, guild_id: int, member_id: int) -> tuple[str, str] | None:
        row = await self.one("SELECT role_name,status FROM clearance_requests WHERE guild_id=? AND member_id=?", (guild_id,member_id)); return (row[0],row[1]) if row else None
    async def set_clearance_status(self, guild_id: int, member_id: int, role_name: str, status: str) -> None:
        await self.execute("INSERT OR REPLACE INTO clearance_requests VALUES(?,?,?,?)", (guild_id,member_id,role_name,status))

    # ── Rooms ──
    async def add_room(self, channel_id: int, guild_id: int, owner_id: int, expires_at: int) -> None:
        await self.execute("INSERT OR REPLACE INTO temporary_rooms VALUES(?,?,?,?)", (channel_id,guild_id,owner_id,expires_at))
    async def room(self, channel_id: int) -> tuple[int,int] | None:
        row = await self.one("SELECT owner_id,expires_at FROM temporary_rooms WHERE channel_id=?", (channel_id,)); return (row[0],row[1]) if row else None
    async def expired_rooms(self, now: int) -> list[int]:
        async with aiosqlite.connect(self.path) as db:
            async with db.execute("SELECT channel_id FROM temporary_rooms WHERE expires_at<=?", (now,)) as cursor: return [row[0] for row in await cursor.fetchall()]
    async def remove_room(self, channel_id: int) -> None:
        await self.execute("DELETE FROM temporary_rooms WHERE channel_id=?", (channel_id,))

    # ── Member stages ──
    async def get_member_stage(self, guild_id: int, member_id: int) -> str:
        row = await self.one("SELECT stage FROM member_stages WHERE guild_id=? AND member_id=?", (guild_id, member_id))
        return row[0] if row else "arrival"
    async def set_member_stage(self, guild_id: int, member_id: int, stage: str) -> None:
        await self.execute("INSERT OR REPLACE INTO member_stages VALUES(?,?,?)", (guild_id, member_id, stage))

    # ── Moderation ──
    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str, timestamp: float) -> int:
        return await self.last_row_id(
            "INSERT INTO warnings(guild_id,user_id,moderator_id,reason,timestamp) VALUES(?,?,?,?,?)",
            (guild_id, user_id, moderator_id, reason, timestamp)
        )
    async def get_warnings(self, guild_id: int, user_id: int) -> list:
        return await self.all("SELECT case_id, moderator_id, reason, timestamp FROM warnings WHERE guild_id=? AND user_id=? ORDER BY timestamp DESC", (guild_id, user_id))
    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
            await db.commit()
            return cursor.rowcount
    async def remove_warning(self, case_id: int) -> None:
        await self.execute("DELETE FROM warnings WHERE case_id=?", (case_id,))

    async def add_ban(self, guild_id: int, user_id: int, moderator_id: int, reason: str | None, timestamp: float) -> None:
        await self.execute("INSERT OR REPLACE INTO bans VALUES(?,?,?,?,?)", (guild_id, user_id, moderator_id, reason, timestamp))
    async def remove_ban(self, guild_id: int, user_id: int) -> None:
        await self.execute("DELETE FROM bans WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    async def add_timeout(self, guild_id: int, user_id: int, moderator_id: int, reason: str | None, until: float, timestamp: float) -> None:
        await self.execute("INSERT OR REPLACE INTO timeouts VALUES(?,?,?,?,?,?)", (guild_id, user_id, moderator_id, reason, until, timestamp))
    async def remove_timeout(self, guild_id: int, user_id: int) -> None:
        await self.execute("DELETE FROM timeouts WHERE guild_id=? AND user_id=?", (guild_id, user_id))

    # ── Economy ──
    async def get_balance(self, guild_id: int, user_id: int) -> tuple[int, int, float]:
        row = await self.one("SELECT wallet, bank, daily_timestamp FROM economy WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        return row if row else (0, 0, 0)
    async def set_balance(self, guild_id: int, user_id: int, wallet: int, bank: int, daily_timestamp: float) -> None:
        await self.execute("INSERT OR REPLACE INTO economy VALUES(?,?,?,?,?)", (guild_id, user_id, wallet, bank, daily_timestamp))
    async def economy_top(self, guild_id: int, limit: int = 10) -> list:
        return await self.all("SELECT user_id, wallet + bank as total FROM economy WHERE guild_id=? ORDER BY total DESC LIMIT ?", (guild_id, limit))

    # ── Leveling ──
    async def get_level(self, guild_id: int, user_id: int) -> tuple[int, int, int, int]:
        row = await self.one("SELECT xp, level, total_messages, voice_minutes FROM leveling WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        return row if row else (0, 0, 0, 0)
    async def set_level(self, guild_id: int, user_id: int, xp: int, level: int, total_messages: int, voice_minutes: int) -> None:
        await self.execute("INSERT OR REPLACE INTO leveling VALUES(?,?,?,?,?)", (guild_id, user_id, xp, level, total_messages, voice_minutes))
    async def leveling_top(self, guild_id: int, limit: int = 10) -> list:
        return await self.all("SELECT user_id, xp, level FROM leveling WHERE guild_id=? ORDER BY xp DESC LIMIT ?", (guild_id, limit))

    # ── Starboard ──
    async def get_starboard(self, guild_id: int, message_id: int) -> tuple | None:
        return await self.one("SELECT channel_id, author_id, content, star_count, posted_message_id FROM starboard WHERE guild_id=? AND message_id=?", (guild_id, message_id))
    async def add_starboard(self, guild_id: int, message_id: int, channel_id: int, author_id: int, content: str) -> None:
        await self.execute("INSERT OR REPLACE INTO starboard VALUES(?,?,?,?,?,0,NULL)", (guild_id, message_id, channel_id, author_id, content))
    async def update_starboard(self, guild_id: int, message_id: int, star_count: int, posted_message_id: int | None) -> None:
        await self.execute("UPDATE starboard SET star_count=?, posted_message_id=? WHERE guild_id=? AND message_id=?", (star_count, posted_message_id, guild_id, message_id))
    async def remove_starboard(self, guild_id: int, message_id: int) -> None:
        await self.execute("DELETE FROM starboard WHERE guild_id=? AND message_id=?", (guild_id, message_id))

    # ── Reaction Roles ──
    async def add_reaction_role(self, guild_id: int, message_id: int, emoji: str, role_id: int) -> None:
        await self.execute("INSERT OR REPLACE INTO reaction_roles VALUES(?,?,?,?)", (guild_id, message_id, emoji, role_id))
    async def remove_reaction_role(self, guild_id: int, message_id: int, emoji: str) -> None:
        await self.execute("DELETE FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?", (guild_id, message_id, emoji))
    async def get_reaction_roles(self, guild_id: int, message_id: int) -> list:
        return await self.all("SELECT emoji, role_id FROM reaction_roles WHERE guild_id=? AND message_id=?", (guild_id, message_id))
    async def get_reaction_role(self, guild_id: int, message_id: int, emoji: str) -> int | None:
        row = await self.one("SELECT role_id FROM reaction_roles WHERE guild_id=? AND message_id=? AND emoji=?", (guild_id, message_id, emoji))
        return row[0] if row else None

    # ── Polls ──
    async def create_poll(self, guild_id: int, message_id: int, channel_id: int, author_id: int, question: str, options: str) -> None:
        await self.execute("INSERT INTO polls VALUES(?,?,?,?,?,?,?,1)", (guild_id, message_id, channel_id, author_id, question, options, '{}'))
    async def get_poll(self, message_id: int) -> tuple | None:
        return await self.one("SELECT * FROM polls WHERE message_id=?", (message_id,))
    async def update_poll_votes(self, message_id: int, votes: str) -> None:
        await self.execute("UPDATE polls SET votes=? WHERE message_id=?", (votes, message_id))
    async def close_poll(self, message_id: int) -> None:
        await self.execute("UPDATE polls SET active=0 WHERE message_id=?", (message_id,))

    # ── Suggestions ──
    async def add_suggestion(self, guild_id: int, user_id: int, content: str, timestamp: float) -> int:
        return await self.last_row_id(
            "INSERT INTO suggestions(guild_id,user_id,content,timestamp) VALUES(?,?,?,?)",
            (guild_id, user_id, content, timestamp)
        )
    async def get_suggestion(self, suggestion_id: int) -> tuple | None:
        return await self.one("SELECT * FROM suggestions WHERE suggestion_id=?", (suggestion_id,))
    async def update_suggestion_status(self, suggestion_id: int, status: str) -> None:
        await self.execute("UPDATE suggestions SET status=? WHERE suggestion_id=?", (status, suggestion_id))
    async def vote_suggestion(self, suggestion_id: int, up: bool) -> None:
        col = "upvotes" if up else "downvotes"
        await self.execute(f"UPDATE suggestions SET {col} = {col} + 1 WHERE suggestion_id=?", (suggestion_id,))

    # ── AutoMod ──
    async def get_automod(self, guild_id: int) -> tuple | None:
        return await self.one("SELECT * FROM automod_config WHERE guild_id=?", (guild_id,))
    async def set_automod(self, guild_id: int, anti_spam: int, anti_link: int, anti_caps: int, spam_threshold: int, mute_duration: int) -> None:
        await self.execute("INSERT OR REPLACE INTO automod_config VALUES(?,?,?,?,?,?)", (guild_id, anti_spam, anti_link, anti_caps, spam_threshold, mute_duration))

    # ── Audit Log ──
    async def add_audit(self, guild_id: int, action: str, user_id: int | None, target_id: int | None, reason: str | None, details: str | None, timestamp: float) -> None:
        await self.execute("INSERT INTO audit_log(guild_id,action,user_id,target_id,reason,details,timestamp) VALUES(?,?,?,?,?,?,?)",
                           (guild_id, action, user_id, target_id, reason, details, timestamp))
