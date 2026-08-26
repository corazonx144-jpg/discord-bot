import sqlite3
import os

DB_PATH = "nexus.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Levels Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS levels (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        messages_count INTEGER DEFAULT 0
    )
    """)
    
    # Economy Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS economy (
        user_id INTEGER PRIMARY KEY,
        balance INTEGER DEFAULT 100,
        bank INTEGER DEFAULT 0,
        last_daily TEXT
    )
    """)
    
    # Warnings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        guild_id INTEGER,
        reason TEXT,
        moderator_id INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # System Panels & Configs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS panels (
        guild_id INTEGER PRIMARY KEY,
        ticket_channel_id INTEGER,
        log_channel_id INTEGER,
        verify_role_id INTEGER,
        raid_mode INTEGER DEFAULT 0
    )
    """)
    
    # Temporary Voice Rooms
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS temp_channels (
        channel_id INTEGER PRIMARY KEY,
        owner_id INTEGER
    )
    """)
    
    conn.commit()
    conn.close()

# Database Helper Functions
def get_user_xp(user_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT xp, level FROM levels WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res if res else (0, 0)

def update_user_xp(user_id: int, added_xp: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT xp, level FROM levels WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    if not res:
        c.execute("INSERT INTO levels (user_id, xp, level, messages_count) VALUES (?, ?, ?, 1)", (user_id, added_xp, 0))
        new_xp, current_level = added_xp, 0
    else:
        new_xp = res["xp"] + added_xp
        current_level = res["level"]
        c.execute("UPDATE levels SET xp = ?, messages_count = messages_count + 1 WHERE user_id = ?", (new_xp, user_id))
    
    # Simple leveling formula: (level + 1) * 100 XP required
    next_level_xp = (current_level + 1) * 100
    leveled_up = False
    if new_xp >= next_level_xp:
        current_level += 1
        c.execute("UPDATE levels SET level = ? WHERE user_id = ?", (current_level, user_id))
        leveled_up = True
        
    conn.commit()
    conn.close()
    return leveled_up, current_level

def batch_add_xp(xp_map: dict):
    """حفظ الـ XP دفعة واحدة لمنع استهلاك sqlite أثناء وجود الأعضاء في الصوتيات"""
    conn = get_db()
    c = conn.cursor()
    for user_id, xp in xp_map.items():
        c.execute("SELECT xp, level FROM levels WHERE user_id = ?", (user_id,))
        res = c.fetchone()
        if not res:
            c.execute("INSERT INTO levels (user_id, xp, level) VALUES (?, ?, 0)", (user_id, xp))
        else:
            c.execute("UPDATE levels SET xp = xp + ? WHERE user_id = ?", (xp, user_id))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT user_id, xp, level FROM levels ORDER OR xp DESC LIMIT 10")
    rows = c.fetchall()
    conn.close()
    return rows

def add_warning(user_id: int, guild_id: int, reason: str, moderator_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO warnings (user_id, guild_id, reason, moderator_id) VALUES (?, ?, ?, ?)", 
              (user_id, guild_id, reason, moderator_id))
    conn.commit()
    conn.close()

def get_warnings(user_id: int, guild_id: int):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT reason, moderator_id, timestamp FROM warnings WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
    rows = c.fetchall()
    conn.close()
    return rows

def set_raid_mode(guild_id: int, status: bool):
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO panels (guild_id, raid_mode) VALUES (?, ?)", (guild_id, 1 if status else 0))
    conn.commit()
    conn.close()

def get_raid_mode(guild_id: int) -> bool:
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT raid_mode FROM panels WHERE guild_id = ?", (guild_id,))
    res = c.fetchone()
    conn.close()
    return bool(res["raid_mode"]) if res else False