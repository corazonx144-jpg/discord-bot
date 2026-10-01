from __future__ import annotations

import asyncio
import os

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS panels (
    guild_id   INTEGER NOT NULL,
    panel_key  TEXT    NOT NULL,
    channel_id INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    PRIMARY KEY (guild_id, panel_key)
);

CREATE TABLE IF NOT EXISTS levels (
    guild_id      INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    xp            INTEGER NOT NULL DEFAULT 0,
    level         INTEGER NOT NULL DEFAULT 0,
    messages      INTEGER NOT NULL DEFAULT 0,
    voice_minutes INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);
CREATE INDEX IF NOT EXISTS idx_levels_rank
    ON levels (guild_id, level DESC, xp DESC);

CREATE TABLE IF NOT EXISTS economy (
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    wallet     INTEGER NOT NULL DEFAULT 0,
    bank       INTEGER NOT NULL DEFAULT 0,
    last_daily REAL    NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS warnings (
    case_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason       TEXT,
    timestamp    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_warnings_user ON warnings (guild_id, user_id);

CREATE TABLE IF NOT EXISTS bans (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason       TEXT,
    timestamp    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS timeouts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id     INTEGER NOT NULL,
    user_id      INTEGER NOT NULL,
    moderator_id INTEGER NOT NULL,
    reason       TEXT,
    until        REAL NOT NULL,
    timestamp    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id  INTEGER NOT NULL,
    action    TEXT NOT NULL,
    user_id   INTEGER,
    target_id INTEGER,
    reason    TEXT,
    details   TEXT,
    timestamp REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS automod (
    guild_id       INTEGER PRIMARY KEY,
    anti_spam      INTEGER NOT NULL DEFAULT 0,
    anti_link      INTEGER NOT NULL DEFAULT 0,
    anti_caps      INTEGER NOT NULL DEFAULT 0,
    spam_threshold INTEGER NOT NULL DEFAULT 5,
    mute_duration  INTEGER NOT NULL DEFAULT 300
);

CREATE TABLE IF NOT EXISTS raid_config (
    guild_id       INTEGER PRIMARY KEY,
    enabled        INTEGER NOT NULL DEFAULT 0,
    threshold      INTEGER NOT NULL DEFAULT 10,
    window         INTEGER NOT NULL DEFAULT 60,
    lockdown_until REAL    NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS member_stage (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    stage    TEXT    NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS verification (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    status   TEXT    NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS clearance (
    guild_id  INTEGER NOT NULL,
    user_id   INTEGER NOT NULL,
    role_name TEXT    NOT NULL,
    status    TEXT    NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

CREATE TABLE IF NOT EXISTS rooms (
    channel_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    owner_id   INTEGER NOT NULL,
    expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    channel_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'open',
    created_at REAL    NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets (guild_id, user_id, status);

CREATE TABLE IF NOT EXISTS reaction_roles (
    guild_id   INTEGER NOT NULL,
    message_id INTEGER NOT NULL,
    emoji      TEXT    NOT NULL,
    role_id    INTEGER NOT NULL,
    PRIMARY KEY (guild_id, message_id, emoji)
);

CREATE TABLE IF NOT EXISTS starboard (
    guild_id          INTEGER NOT NULL,
    message_id        INTEGER NOT NULL,
    channel_id        INTEGER NOT NULL,
    author_id         INTEGER NOT NULL,
    posted_message_id INTEGER,
    stars             INTEGER NOT NULL DEFAULT 0,
    content           TEXT,
    PRIMARY KEY (guild_id, message_id)
);

CREATE TABLE IF NOT EXISTS shop_items (
    item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id    INTEGER NOT NULL,
    name        TEXT    NOT NULL,
    description TEXT    NOT NULL DEFAULT '',
    price       INTEGER NOT NULL,
    role_id     INTEGER,
    item_type   TEXT    NOT NULL DEFAULT 'item'
);

CREATE TABLE IF NOT EXISTS inventory (
    guild_id INTEGER NOT NULL,
    user_id  INTEGER NOT NULL,
    item_id  INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (guild_id, user_id, item_id)
);

CREATE TABLE IF NOT EXISTS polls (
    message_id INTEGER PRIMARY KEY,
    guild_id   INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    user_id    INTEGER NOT NULL,
    question   TEXT    NOT NULL,
    options    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS suggestions (
    suggestion_id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id      INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    content       TEXT    NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'pending',
    upvotes       INTEGER NOT NULL DEFAULT 0,
    downvotes     INTEGER NOT NULL DEFAULT 0,
    timestamp     REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS suggestion_votes (
    suggestion_id INTEGER NOT NULL,
    user_id       INTEGER NOT NULL,
    vote          INTEGER NOT NULL,
    PRIMARY KEY (suggestion_id, user_id)
);
"""


class Database:
    """Async SQLite layer. One connection, one lock, so multi-step
    operations (pay, daily, buy, vote) are atomic."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or os.getenv("DB_PATH", "nexus.db")
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    # --------------------------------------------------------
    # lifecycle
    # --------------------------------------------------------

    async def initialize(self) -> None:
        folder = os.path.dirname(self.path)

        if folder:
            os.makedirs(folder, exist_ok=True)

        self._db = await aiosqlite.connect(self.path)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.executescript(SCHEMA)
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not initialized")
        return self._db

    # --------------------------------------------------------
    # low level helpers
    # --------------------------------------------------------

    async def execute(self, sql: str, params: tuple = ()) -> int:
        """Run a write statement. Returns the affected row count."""
        async with self._lock:
            cur = await self.db.execute(sql, params)
            await self.db.commit()
            count = cur.rowcount
            await cur.close()
            return count

    async def _insert(self, sql: str, params: tuple = ()) -> int:
        async with self._lock:
            cur = await self.db.execute(sql, params)
            await self.db.commit()
            row_id = cur.lastrowid
            await cur.close()
            return row_id

    async def _one(self, sql: str, params: tuple = ()):
        async with self._lock:
            cur = await self.db.execute(sql, params)
            row = await cur.fetchone()
            await cur.close()
            return tuple(row) if row else None

    async def _all(self, sql: str, params: tuple = ()) -> list[tuple]:
        async with self._lock:
            cur = await self.db.execute(sql, params)
            rows = await cur.fetchall()
            await cur.close()
            return [tuple(row) for row in rows]

    # --------------------------------------------------------
    # panels
    # --------------------------------------------------------

    async def panel_message(self, guild_id: int, key: str):
        """-> (channel_id, message_id) or None"""
        return await self._one(
            "SELECT channel_id, message_id FROM panels "
            "WHERE guild_id=? AND panel_key=?",
            (guild_id, key),
        )

    async def save_panel(
        self, guild_id: int, key: str, channel_id: int, message_id: int
    ) -> None:
        await self.execute(
            "INSERT INTO panels (guild_id, panel_key, channel_id, message_id) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(guild_id, panel_key) DO UPDATE SET "
            "channel_id=excluded.channel_id, message_id=excluded.message_id",
            (guild_id, key, channel_id, message_id),
        )

    # --------------------------------------------------------
    # levels
    # --------------------------------------------------------

    async def get_level(self, guild_id: int, user_id: int):
        """-> (xp, level, messages, voice_minutes)"""
        row = await self._one(
            "SELECT xp, level, messages, voice_minutes FROM levels "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        return row or (0, 0, 0, 0)

    async def set_level(
        self,
        guild_id: int,
        user_id: int,
        xp: int,
        level: int,
        messages: int,
        voice_minutes: int,
    ) -> None:
        await self.execute(
            "INSERT INTO levels "
            "(guild_id, user_id, xp, level, messages, voice_minutes) "
            "VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "xp=excluded.xp, level=excluded.level, "
            "messages=excluded.messages, voice_minutes=excluded.voice_minutes",
            (guild_id, user_id, xp, level, messages, voice_minutes),
        )

    async def leveling_top(self, guild_id: int, limit: int = 10):
        """-> [(user_id, xp, level)]"""
        return await self._all(
            "SELECT user_id, xp, level FROM levels WHERE guild_id=? "
            "ORDER BY level DESC, xp DESC LIMIT ?",
            (guild_id, limit),
        )

    # --------------------------------------------------------
    # economy
    # --------------------------------------------------------

    async def get_balance(self, guild_id: int, user_id: int):
        """-> (wallet, bank, last_daily)"""
        row = await self._one(
            "SELECT wallet, bank, last_daily FROM economy "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        return row or (0, 0, 0.0)

    async def set_balance(
        self,
        guild_id: int,
        user_id: int,
        wallet: int,
        bank: int,
        last_daily: float,
    ) -> None:
        await self.execute(
            "INSERT INTO economy (guild_id, user_id, wallet, bank, last_daily) "
            "VALUES (?,?,?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "wallet=excluded.wallet, bank=excluded.bank, "
            "last_daily=excluded.last_daily",
            (guild_id, user_id, wallet, bank, last_daily),
        )

    async def economy_top(self, guild_id: int, limit: int = 10):
        """-> [(user_id, total)]"""
        return await self._all(
            "SELECT user_id, wallet + bank AS total FROM economy "
            "WHERE guild_id=? AND wallet + bank > 0 "
            "ORDER BY total DESC LIMIT ?",
            (guild_id, limit),
        )

    async def add_wallet(self, guild_id: int, user_id: int, amount: int) -> int:
        """Atomic credit. Returns the new wallet."""
        async with self._lock:
            await self.db.execute(
                "INSERT INTO economy (guild_id, user_id, wallet) VALUES (?,?,?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                "wallet = wallet + excluded.wallet",
                (guild_id, user_id, amount),
            )
            cur = await self.db.execute(
                "SELECT wallet FROM economy WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            row = await cur.fetchone()
            await cur.close()
            await self.db.commit()
            return row[0]

    async def transfer(
        self, guild_id: int, sender: int, receiver: int, amount: int
    ) -> bool:
        """Atomic wallet to wallet payment. False if funds are missing."""
        if amount <= 0:
            return False

        async with self._lock:
            cur = await self.db.execute(
                "UPDATE economy SET wallet = wallet - ? "
                "WHERE guild_id=? AND user_id=? AND wallet >= ?",
                (amount, guild_id, sender, amount),
            )
            changed = cur.rowcount
            await cur.close()

            if not changed:
                await self.db.rollback()
                return False

            await self.db.execute(
                "INSERT INTO economy (guild_id, user_id, wallet) VALUES (?,?,?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                "wallet = wallet + excluded.wallet",
                (guild_id, receiver, amount),
            )
            await self.db.commit()
            return True

    async def claim_daily(
        self, guild_id: int, user_id: int, reward: int, now: float
    ):
        """-> (True, new_wallet) or (False, seconds_remaining)"""
        async with self._lock:
            cur = await self.db.execute(
                "SELECT last_daily FROM economy WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            row = await cur.fetchone()
            await cur.close()

            last = row[0] if row else 0

            if now - last < 86400:
                return False, int(86400 - (now - last))

            await self.db.execute(
                "INSERT INTO economy (guild_id, user_id, wallet, last_daily) "
                "VALUES (?,?,?,?) "
                "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
                "wallet = wallet + excluded.wallet, "
                "last_daily = excluded.last_daily",
                (guild_id, user_id, reward, now),
            )
            cur = await self.db.execute(
                "SELECT wallet FROM economy WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            wallet = (await cur.fetchone())[0]
            await cur.close()
            await self.db.commit()
            return True, wallet

    # --------------------------------------------------------
    # shop
    # --------------------------------------------------------

    async def get_shop_items(self, guild_id: int):
        """-> [(item_id, name, description, price, role_id, item_type)]"""
        return await self._all(
            "SELECT item_id, name, description, price, role_id, item_type "
            "FROM shop_items WHERE guild_id=? ORDER BY item_id",
            (guild_id,),
        )

    async def add_shop_item(
        self,
        guild_id: int,
        name: str,
        description: str,
        price: int,
        role_id: int | None,
        item_type: str,
    ) -> int:
        return await self._insert(
            "INSERT INTO shop_items "
            "(guild_id, name, description, price, role_id, item_type) "
            "VALUES (?,?,?,?,?,?)",
            (guild_id, name, description, price, role_id, item_type),
        )

    async def add_to_inventory(
        self, guild_id: int, user_id: int, item_id: int
    ) -> None:
        await self.execute(
            "INSERT INTO inventory (guild_id, user_id, item_id, quantity) "
            "VALUES (?,?,?,1) "
            "ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET "
            "quantity = quantity + 1",
            (guild_id, user_id, item_id),
        )

    async def purchase(self, guild_id: int, user_id: int, item_id: int):
        """Atomic buy.
        -> ("missing", None)
           ("poor", price)
           ("ok", (name, role_id, item_type, wallet_left))"""
        async with self._lock:
            cur = await self.db.execute(
                "SELECT name, price, role_id, item_type FROM shop_items "
                "WHERE guild_id=? AND item_id=?",
                (guild_id, item_id),
            )
            item = await cur.fetchone()
            await cur.close()

            if not item:
                return "missing", None

            name, price, role_id, item_type = item

            cur = await self.db.execute(
                "UPDATE economy SET wallet = wallet - ? "
                "WHERE guild_id=? AND user_id=? AND wallet >= ?",
                (price, guild_id, user_id, price),
            )
            changed = cur.rowcount
            await cur.close()

            if not changed:
                await self.db.rollback()
                return "poor", price

            await self.db.execute(
                "INSERT INTO inventory (guild_id, user_id, item_id, quantity) "
                "VALUES (?,?,?,1) "
                "ON CONFLICT(guild_id, user_id, item_id) DO UPDATE SET "
                "quantity = quantity + 1",
                (guild_id, user_id, item_id),
            )
            cur = await self.db.execute(
                "SELECT wallet FROM economy WHERE guild_id=? AND user_id=?",
                (guild_id, user_id),
            )
            wallet = (await cur.fetchone())[0]
            await cur.close()
            await self.db.commit()
            return "ok", (name, role_id, item_type, wallet)

    # --------------------------------------------------------
    # moderation
    # --------------------------------------------------------

    async def add_warning(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        timestamp: float,
    ) -> int:
        return await self._insert(
            "INSERT INTO warnings "
            "(guild_id, user_id, moderator_id, reason, timestamp) "
            "VALUES (?,?,?,?,?)",
            (guild_id, user_id, moderator_id, reason, timestamp),
        )

    async def get_warnings(self, guild_id: int, user_id: int):
        """-> [(case_id, moderator_id, reason, timestamp)]"""
        return await self._all(
            "SELECT case_id, moderator_id, reason, timestamp FROM warnings "
            "WHERE guild_id=? AND user_id=? ORDER BY case_id",
            (guild_id, user_id),
        )

    async def clear_warnings(self, guild_id: int, user_id: int) -> int:
        return await self.execute(
            "DELETE FROM warnings WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )

    async def add_ban(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        timestamp: float,
    ) -> None:
        await self.execute(
            "INSERT INTO bans "
            "(guild_id, user_id, moderator_id, reason, timestamp) "
            "VALUES (?,?,?,?,?)",
            (guild_id, user_id, moderator_id, reason, timestamp),
        )

    async def remove_ban(self, guild_id: int, user_id: int) -> None:
        await self.execute(
            "DELETE FROM bans WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )

    async def add_timeout(
        self,
        guild_id: int,
        user_id: int,
        moderator_id: int,
        reason: str,
        until: float,
        timestamp: float,
    ) -> None:
        await self.execute(
            "INSERT INTO timeouts "
            "(guild_id, user_id, moderator_id, reason, until, timestamp) "
            "VALUES (?,?,?,?,?,?)",
            (guild_id, user_id, moderator_id, reason, until, timestamp),
        )

    async def add_audit(
        self,
        guild_id: int,
        action: str,
        user_id: int | None,
        target_id: int | None,
        reason: str | None,
        details: str | None,
        timestamp: float,
    ) -> None:
        await self.execute(
            "INSERT INTO audit_log "
            "(guild_id, action, user_id, target_id, reason, details, timestamp) "
            "VALUES (?,?,?,?,?,?,?)",
            (guild_id, action, user_id, target_id, reason, details, timestamp),
        )

    # --------------------------------------------------------
    # automod / raid
    # --------------------------------------------------------

    async def get_automod(self, guild_id: int):
        """-> (guild_id, anti_spam, anti_link, anti_caps,
               spam_threshold, mute_duration) or None"""
        return await self._one(
            "SELECT guild_id, anti_spam, anti_link, anti_caps, "
            "spam_threshold, mute_duration FROM automod WHERE guild_id=?",
            (guild_id,),
        )

    async def set_automod(
        self,
        guild_id: int,
        anti_spam: int,
        anti_link: int,
        anti_caps: int,
        spam_threshold: int = 5,
        mute_duration: int = 300,
    ) -> None:
        await self.execute(
            "INSERT INTO automod "
            "(guild_id, anti_spam, anti_link, anti_caps, "
            "spam_threshold, mute_duration) VALUES (?,?,?,?,?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET "
            "anti_spam=excluded.anti_spam, anti_link=excluded.anti_link, "
            "anti_caps=excluded.anti_caps, "
            "spam_threshold=excluded.spam_threshold, "
            "mute_duration=excluded.mute_duration",
            (
                guild_id, anti_spam, anti_link, anti_caps,
                spam_threshold, mute_duration,
            ),
        )

    async def get_raid_config(self, guild_id: int):
        """-> (guild_id, enabled, threshold, window, lockdown_until) or None"""
        return await self._one(
            "SELECT guild_id, enabled, threshold, window, lockdown_until "
            "FROM raid_config WHERE guild_id=?",
            (guild_id,),
        )

    async def set_raid_config(
        self, guild_id: int, enabled: int, threshold: int, window: int
    ) -> None:
        await self.execute(
            "INSERT INTO raid_config (guild_id, enabled, threshold, window) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET "
            "enabled=excluded.enabled, threshold=excluded.threshold, "
            "window=excluded.window",
            (guild_id, enabled, threshold, window),
        )

    async def set_lockdown(self, guild_id: int, until: float) -> None:
        await self.execute(
            "INSERT INTO raid_config (guild_id, lockdown_until) VALUES (?,?) "
            "ON CONFLICT(guild_id) DO UPDATE SET "
            "lockdown_until=excluded.lockdown_until",
            (guild_id, until),
        )

    # --------------------------------------------------------
    # onboarding: stage / verification / clearance
    # --------------------------------------------------------

    async def get_member_stage(self, guild_id: int, user_id: int):
        row = await self._one(
            "SELECT stage FROM member_stage WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        return row[0] if row else None

    async def set_member_stage(
        self, guild_id: int, user_id: int, stage: str
    ) -> None:
        await self.execute(
            "INSERT INTO member_stage (guild_id, user_id, stage) "
            "VALUES (?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET stage=excluded.stage",
            (guild_id, user_id, stage),
        )

    async def verification_status(self, guild_id: int, user_id: int):
        row = await self._one(
            "SELECT status FROM verification WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )
        return row[0] if row else None

    async def set_verification_status(
        self, guild_id: int, user_id: int, status: str
    ) -> None:
        await self.execute(
            "INSERT INTO verification (guild_id, user_id, status) "
            "VALUES (?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "status=excluded.status",
            (guild_id, user_id, status),
        )

    async def clearance_status(self, guild_id: int, user_id: int):
        """-> (role_name, status) or None"""
        return await self._one(
            "SELECT role_name, status FROM clearance "
            "WHERE guild_id=? AND user_id=?",
            (guild_id, user_id),
        )

    async def set_clearance_status(
        self, guild_id: int, user_id: int, role_name: str, status: str
    ) -> None:
        await self.execute(
            "INSERT INTO clearance (guild_id, user_id, role_name, status) "
            "VALUES (?,?,?,?) "
            "ON CONFLICT(guild_id, user_id) DO UPDATE SET "
            "role_name=excluded.role_name, status=excluded.status",
            (guild_id, user_id, role_name, status),
        )

    # --------------------------------------------------------
    # temporary voice rooms
    # --------------------------------------------------------

    async def add_room(
        self, channel_id: int, guild_id: int, owner_id: int, expires_at: int
    ) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO rooms "
            "(channel_id, guild_id, owner_id, expires_at) VALUES (?,?,?,?)",
            (channel_id, guild_id, owner_id, expires_at),
        )

    async def room(self, channel_id: int):
        """-> (owner_id, expires_at) or None"""
        return await self._one(
            "SELECT owner_id, expires_at FROM rooms WHERE channel_id=?",
            (channel_id,),
        )

    async def remove_room(self, channel_id: int) -> None:
        await self.execute(
            "DELETE FROM rooms WHERE channel_id=?", (channel_id,)
        )

    async def expired_rooms(self, now: int) -> list[int]:
        rows = await self._all(
            "SELECT channel_id FROM rooms WHERE expires_at <= ?", (now,)
        )
        return [row[0] for row in rows]

    async def owner_rooms(self, guild_id: int, owner_id: int) -> list[int]:
        rows = await self._all(
            "SELECT channel_id FROM rooms WHERE guild_id=? AND owner_id=?",
            (guild_id, owner_id),
        )
        return [row[0] for row in rows]

    # --------------------------------------------------------
    # tickets
    # --------------------------------------------------------

    async def create_ticket(
        self, channel_id: int, guild_id: int, user_id: int
    ) -> None:
        import time

        await self.execute(
            "INSERT OR REPLACE INTO tickets "
            "(channel_id, guild_id, user_id, status, created_at) "
            "VALUES (?,?,?,'open',?)",
            (channel_id, guild_id, user_id, time.time()),
        )

    async def open_ticket_for(self, guild_id: int, user_id: int):
        row = await self._one(
            "SELECT channel_id FROM tickets "
            "WHERE guild_id=? AND user_id=? AND status='open' "
            "ORDER BY created_at DESC LIMIT 1",
            (guild_id, user_id),
        )
        return row[0] if row else None

    async def ticket_owner(self, channel_id: int):
        row = await self._one(
            "SELECT user_id FROM tickets WHERE channel_id=?", (channel_id,)
        )
        return row[0] if row else None

    async def close_ticket(self, channel_id: int) -> None:
        await self.execute(
            "UPDATE tickets SET status='closed' WHERE channel_id=?",
            (channel_id,),
        )

    # --------------------------------------------------------
    # reaction roles
    # --------------------------------------------------------

    async def add_reaction_role(
        self, guild_id: int, message_id: int, emoji: str, role_id: int
    ) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO reaction_roles "
            "(guild_id, message_id, emoji, role_id) VALUES (?,?,?,?)",
            (guild_id, message_id, emoji, role_id),
        )

    async def get_reaction_role(
        self, guild_id: int, message_id: int, emoji: str
    ):
        row = await self._one(
            "SELECT role_id FROM reaction_roles "
            "WHERE guild_id=? AND message_id=? AND emoji=?",
            (guild_id, message_id, emoji),
        )
        return row[0] if row else None

    # --------------------------------------------------------
    # starboard
    # --------------------------------------------------------

    async def get_starboard(self, guild_id: int, message_id: int):
        """-> (guild_id, message_id, channel_id, author_id,
               posted_message_id, stars, content) or None"""
        return await self._one(
            "SELECT guild_id, message_id, channel_id, author_id, "
            "posted_message_id, stars, content FROM starboard "
            "WHERE guild_id=? AND message_id=?",
            (guild_id, message_id),
        )

    async def add_starboard(
        self,
        guild_id: int,
        message_id: int,
        channel_id: int,
        author_id: int,
        content: str,
    ) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO starboard "
            "(guild_id, message_id, channel_id, author_id, content) "
            "VALUES (?,?,?,?,?)",
            (guild_id, message_id, channel_id, author_id, content),
        )

    async def update_starboard(
        self,
        guild_id: int,
        message_id: int,
        stars: int,
        posted_message_id: int | None,
    ) -> None:
        await self.execute(
            "UPDATE starboard SET stars=?, posted_message_id=? "
            "WHERE guild_id=? AND message_id=?",
            (stars, posted_message_id, guild_id, message_id),
        )

    async def remove_starboard(self, guild_id: int, message_id: int) -> None:
        await self.execute(
            "DELETE FROM starboard WHERE guild_id=? AND message_id=?",
            (guild_id, message_id),
        )

    # --------------------------------------------------------
    # polls
    # --------------------------------------------------------

    async def create_poll(
        self,
        guild_id: int,
        message_id: int,
        channel_id: int,
        user_id: int,
        question: str,
        options_json: str,
    ) -> None:
        await self.execute(
            "INSERT OR REPLACE INTO polls "
            "(message_id, guild_id, channel_id, user_id, question, options) "
            "VALUES (?,?,?,?,?,?)",
            (message_id, guild_id, channel_id, user_id, question, options_json),
        )

    # --------------------------------------------------------
    # suggestions
    # --------------------------------------------------------

    async def add_suggestion(
        self, guild_id: int, user_id: int, content: str, timestamp: float
    ) -> int:
        return await self._insert(
            "INSERT INTO suggestions (guild_id, user_id, content, timestamp) "
            "VALUES (?,?,?,?)",
            (guild_id, user_id, content, timestamp),
        )

    async def get_suggestion(self, suggestion_id: int):
        """-> (suggestion_id, guild_id, user_id, content, status,
               upvotes, downvotes, timestamp) or None"""
        return await self._one(
            "SELECT suggestion_id, guild_id, user_id, content, status, "
            "upvotes, downvotes, timestamp FROM suggestions "
            "WHERE suggestion_id=?",
            (suggestion_id,),
        )

    async def recent_suggestion_ids(self, limit: int = 200) -> list[int]:
        rows = await self._all(
            "SELECT suggestion_id FROM suggestions "
            "ORDER BY suggestion_id DESC LIMIT ?",
            (limit,),
        )
        return [row[0] for row in rows]

    async def get_suggestion_vote(self, suggestion_id: int, user_id: int):
        """-> 1, -1 or None"""
        row = await self._one(
            "SELECT vote FROM suggestion_votes "
            "WHERE suggestion_id=? AND user_id=?",
            (suggestion_id, user_id),
        )
        return row[0] if row else None

    async def vote_suggestion(
        self, suggestion_id: int, user_id: int, up: bool
    ) -> bool:
        """Record or change a vote and recount. False if the suggestion
        does not exist."""
        async with self._lock:
            cur = await self.db.execute(
                "SELECT 1 FROM suggestions WHERE suggestion_id=?",
                (suggestion_id,),
            )
            exists = await cur.fetchone()
            await cur.close()

            if not exists:
                return False

            await self.db.execute(
                "INSERT INTO suggestion_votes (suggestion_id, user_id, vote) "
                "VALUES (?,?,?) "
                "ON CONFLICT(suggestion_id, user_id) DO UPDATE SET "
                "vote=excluded.vote",
                (suggestion_id, user_id, 1 if up else -1),
            )
            await self.db.execute(
                "UPDATE suggestions SET "
                "upvotes=(SELECT COUNT(*) FROM suggestion_votes "
                "         WHERE suggestion_id=? AND vote=1), "
                "downvotes=(SELECT COUNT(*) FROM suggestion_votes "
                "           WHERE suggestion_id=? AND vote=-1) "
                "WHERE suggestion_id=?",
                (suggestion_id, suggestion_id, suggestion_id),
            )
            await self.db.commit()
            return True
