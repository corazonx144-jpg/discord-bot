"""
layout.py - single source of truth for the Nexus server.

Everything (roles, role order, categories, channels, who can see / write)
is defined in the data tables below. To change the server you edit the
tables, not the code, then run /setup.
"""
from __future__ import annotations

import logging
from contextlib import suppress

import discord

log = logging.getLogger("nexus")


# ============================================================
# ROLES  (top of the list = highest in the hierarchy)
# key, name, colour, hoist, extra permissions
# ============================================================

ROLE_SPECS: list[tuple[str, str, int, bool, dict]] = [
    ("admin", "Admin", 0xFF0000, True, dict(administrator=True)),
    (
        "moderator", "Moderator", 0xFF0044, True,
        dict(
            kick_members=True, ban_members=True, moderate_members=True,
            manage_messages=True, view_audit_log=True, move_members=True,
            mute_members=True, deafen_members=True,
        ),
    ),
    ("support", "Support Team", 0x00FF41, True, dict(manage_messages=True)),
    ("developer", "Developer", 0x0088FF, True, {}),
    ("elite", "Elite Agent", 0xFFD700, True, {}),
    ("vip", "VIP", 0xFF00FF, True, {}),
    ("streamer", "Streamer", 0xFF4400, False, {}),
    ("artist", "Artist", 0x00FFAA, False, {}),
    ("musician", "Musician", 0xAA00FF, False, {}),
    ("verified", "Verified", 0x00F0FF, False, {}),
    ("guest", "Guest Node", 0xA0A0A0, False, {}),
    # cosmetic level roles (no access, given automatically by the XP system)
    ("lvl20", "Veteran", 0x9B59B6, False, {}),
    ("lvl10", "Operative", 0x3498DB, False, {}),
    ("lvl5", "Recruit", 0x95A5A6, False, {}),
]

# level required -> cosmetic role name (never grants channel access)
LEVEL_ROLES = {5: "Recruit", 10: "Operative", 20: "Veteran"}

STAFF = ("admin", "moderator")
CREATORS = ["vip", "streamer", "artist", "musician"]
MEMBERS = ["elite", *CREATORS, "support", "developer"]
VIEW_MAIN = [*MEMBERS, "guest"]
VAULT = ["elite", *CREATORS]


# ============================================================
# CATEGORIES
# text entry:  (name, topic) or (name, topic, {"view": [...], "write": [...]})
# an override on a channel replaces the category's access for that channel
# ============================================================

CATEGORIES: list[dict] = [
    {
        "name": "🔒 ─ SECTOR 00 │ GATEWAY",
        "public": True,
        "text": [
            ("⌁-arrival-terminal", "`[PUBLIC]` // Secure gateway for incoming transmissions"),
            ("🛡️-verify-access", "`[AUTH]` // Biometric identity verification required"),
            ("📜-protocol-rules", "`[PROTOCOL]` // Network rules and regulations"),
            ("📖-user-guide", "`[MANUAL]` // Command reference for all personnel"),
            ("🔒-admin-manual", "`[CLASSIFIED]` // Administrative operations manual", {"view": []}),
        ],
        "stage": ["📡-live-briefing"],
    },
    {
        "name": "🧬 ─ SECTOR 01 │ CLEARANCE",
        "view": ["verified"],
        "write": [],
        "text": [
            ("⚡-select-clearance", "`[RESTRICTED]` // Select operational clearance level"),
        ],
    },
    {
        "name": "⚡ ─ SECTOR 02 │ TERMINAL",
        "view": VIEW_MAIN,
        "write": MEMBERS,
        "text": [
            ("🌐-global-network", "`[ENCRYPTED]` // Global communications channel"),
            ("💻-command-shell", "`[ENCRYPTED]` // Command-line interface"),
            ("⭐-starboard", "`[ARCHIVE]` // Starred messages database", {"view": VIEW_MAIN, "write": []}),
            ("📊-community-hub", "`[BROADCAST]` // Community polls and announcements", {"view": VIEW_MAIN, "write": []}),
        ],
    },
    {
        "name": "🎧 ─ SECTOR 03 │ NODES",
        "view": MEMBERS,
        "write": MEMBERS,
        "voice": ["► net_00_safe_zone", "► net_01_black_ops", "► net_02_deep_web"],
    },
    {
        "name": "🎛️ ─ SECTOR 04 │ SERVICES",
        "view": ["verified"],
        "write": [],
        "text": [
            ("🎛️-create-your-room", "`[UTILITY]` // Generate temporary voice nodes"),
            ("🎫-open-a-ticket", "`[SUPPORT]` // Private support tickets"),
        ],
    },
    {
        "name": "📁 ─ SECTOR 05 │ ARCHIVE",
        "view": VIEW_MAIN,
        "write": MEMBERS,
        "text": [
            ("📁-mission-briefs", "`[DATABASE]` // Mission logs and intel", {"view": VIEW_MAIN, "write": []}),
            ("🏆-leaderboards", "`[DATABASE]` // Rankings and statistics", {"view": VIEW_MAIN, "write": []}),
            ("💡-suggestions", "`[COMMUNITY]` // Member suggestions and feedback"),
        ],
    },
    {
        # staff only (Admin + Moderator)
        "name": "👁️ ─ SECTOR 06 │ CONTROL",
        "view": [],
        "write": [],
        "text": [
            ("📊-surveillance-logs", "`[CLASSIFIED]` // All system events logged"),
            ("🛡️-mod-logs", "`[CLASSIFIED]` // Bans, kicks, warns, timeouts"),
            ("📋-message-logs", "`[CLASSIFIED]` // Message edits and deletes"),
            ("🎤-voice-logs", "`[CLASSIFIED]` // Voice joins and leaves"),
            ("👤-member-logs", "`[CLASSIFIED]` // Joins, leaves, bans"),
            ("🔐-approval-queue", "`[CLASSIFIED]` // Pending clearance requests"),
            ("👁️-control-panels", "`[CLASSIFIED]` // AutoMod & reaction role controls"),
        ],
    },
    {
        "name": "🧪 ─ SECTOR 07 │ DEV OPS",
        "view": ["developer"],
        "write": ["developer"],
        "text": [
            ("🧪-dev-terminal", "`[RESTRICTED]` // Development operations"),
        ],
    },
    {
        "name": "💎 ─ SECTOR 08 │ VAULT",
        "view": VAULT,
        "write": VAULT,
        "text": [
            (
                "💎-vip-lounge", "`[PREMIUM]` // Elite & VIP lounge",
                {"view": ["vip", "elite"], "write": ["vip", "elite"]},
            ),
            (
                "🎨-art-gallery", "`[PREMIUM]` // Visual arts showcase",
                {"view": ["artist", "vip", "elite"], "write": ["artist"]},
            ),
            (
                "🎵-music-lab", "`[PREMIUM]` // Audio production lab",
                {"view": ["musician", "vip", "elite"], "write": ["musician"]},
            ),
            (
                "📺-stream-deck", "`[PREMIUM]` // Content creator hub",
                {"view": ["streamer", "vip", "elite"], "write": ["streamer"]},
            ),
        ],
    },
]


SERVICES_CATEGORY = next(c["name"] for c in CATEGORIES if "SERVICES" in c["name"])


# ============================================================
# DERIVED WHITELISTS (used by /reset and /rebuild)
# ============================================================

KEEP_ROLES = {name for _, name, *_ in ROLE_SPECS}
KEEP_CATEGORIES = {c["name"] for c in CATEGORIES}
KEEP_TEXT = {entry[0] for c in CATEGORIES for entry in c.get("text", ())}
KEEP_VOICE = {name for c in CATEGORIES for name in c.get("voice", ())}
KEEP_STAGE = {name for c in CATEGORIES for name in c.get("stage", ())}


_DANGEROUS = discord.Permissions(
    administrator=True,
    manage_guild=True,
    manage_roles=True,
    manage_channels=True,
    manage_webhooks=True,
    kick_members=True,
    ban_members=True,
    moderate_members=True,
    manage_messages=True,
    mention_everyone=True,
)


def is_self_assignable(role: discord.Role) -> bool:
    """Reaction roles may only hand out harmless, non-Nexus roles."""
    if role.managed or role.name in KEEP_ROLES:
        return False
    return not (role.permissions.value & _DANGEROUS.value)


# ============================================================
# PERMISSIONS
# ============================================================

def make_overwrites(
    guild: discord.Guild,
    roles: dict[str, discord.Role],
    *,
    public: bool = False,
    view: list[str] | tuple = (),
    write: list[str] | tuple = (),
) -> dict:
    """Admin + Moderator always get full access, the bot always gets
    access, everybody else only what is listed in view / write."""

    ow: dict = {}

    if public:
        ow[guild.default_role] = discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=False,
        )
    else:
        ow[guild.default_role] = discord.PermissionOverwrite(
            view_channel=False,
        )

    ow[guild.me] = discord.PermissionOverwrite(
        view_channel=True,
        send_messages=True,
        embed_links=True,
        read_message_history=True,
        manage_channels=True,
        connect=True,
    )

    for key in STAFF:
        ow[roles[key]] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_messages=True,
            connect=True,
            speak=True,
        )

    for key in view:
        if key in STAFF:
            continue

        can_write = key in write

        ow[roles[key]] = discord.PermissionOverwrite(
            view_channel=True,
            read_message_history=True,
            send_messages=can_write,
            add_reactions=can_write,
            connect=True,
            speak=can_write,
        )

    return ow


# ============================================================
# ENSURE HELPERS (create if missing, repair if present)
# ============================================================

async def sync_roles(guild: discord.Guild) -> dict[str, discord.Role]:
    me = guild.me
    roles: dict[str, discord.Role] = {}

    for key, name, colour, hoist, perms in ROLE_SPECS:
        kwargs = dict(
            colour=discord.Colour(colour),
            hoist=hoist,
            permissions=discord.Permissions(**perms),
        )

        role = discord.utils.get(guild.roles, name=name)

        if role is None:
            try:
                role = await guild.create_role(
                    name=name, reason="Nexus setup", **kwargs
                )
            except discord.Forbidden:
                # the bot cannot hand out permissions it does not have
                kwargs["permissions"] = discord.Permissions.none()
                role = await guild.create_role(
                    name=name, reason="Nexus setup", **kwargs
                )

        elif not role.managed and role < me.top_role:
            with suppress(discord.Forbidden, discord.HTTPException):
                await role.edit(reason="Nexus role sync", **kwargs)

        roles[key] = role

    # hierarchy: first entry directly under the bot's top role
    top = me.top_role.position
    positions = {
        roles[spec[0]]: max(1, top - 1 - index)
        for index, spec in enumerate(ROLE_SPECS)
    }

    with suppress(discord.Forbidden, discord.HTTPException):
        await guild.edit_role_positions(positions)

    return roles


async def ensure_category(guild, name, overwrites):
    category = discord.utils.get(guild.categories, name=name)

    if category is None:
        return await guild.create_category(
            name, overwrites=overwrites, reason="Nexus setup"
        )

    await category.edit(
        overwrites=overwrites, reason="Nexus layout repair"
    )
    return category


async def ensure_text(category, name, topic="", overwrites=None):
    channel = discord.utils.get(category.text_channels, name=name)

    if channel is None:
        kwargs = {"category": category, "topic": topic, "reason": "Nexus setup"}

        if overwrites is not None:
            kwargs["overwrites"] = overwrites

        return await category.guild.create_text_channel(name, **kwargs)

    kwargs = {"topic": topic, "reason": "Nexus layout repair"}

    if overwrites is not None:
        kwargs["overwrites"] = overwrites
    else:
        kwargs["sync_permissions"] = True  # inherit from category

    await channel.edit(**kwargs)
    return channel


async def ensure_voice(category, name):
    channel = discord.utils.get(category.voice_channels, name=name)

    if channel is None:
        return await category.guild.create_voice_channel(
            name, category=category, reason="Nexus setup"
        )

    await channel.edit(sync_permissions=True, reason="Nexus layout repair")
    return channel


async def ensure_stage(guild, name, category):
    channel = discord.utils.get(guild.stage_channels, name=name)

    try:
        if channel is None:
            return await guild.create_stage_channel(
                name, category=category, reason="Nexus setup"
            )

        await channel.edit(
            category=category, sync_permissions=True,
            reason="Nexus layout repair",
        )
        return channel

    except discord.HTTPException:
        # stage channels need the server to be a Community server
        log.warning("Could not create stage channel %s", name)
        return None


# ============================================================
# BUILD
# ============================================================

async def build_structure(
    guild: discord.Guild,
    roles: dict[str, discord.Role],
) -> dict[str, discord.abc.GuildChannel]:
    """Creates / repairs every category and channel from CATEGORIES.
    Returns {channel_name: channel} so bot.py can attach panels."""

    out: dict = {}

    for spec in CATEGORIES:
        category = await ensure_category(
            guild,
            spec["name"],
            make_overwrites(
                guild,
                roles,
                public=spec.get("public", False),
                view=spec.get("view", ()),
                write=spec.get("write", ()),
            ),
        )

        out[spec["name"]] = category

        for entry in spec.get("text", ()):
            name, topic, *rest = entry
            overwrites = None

            if rest and rest[0] is not None:
                override = rest[0]
                overwrites = make_overwrites(
                    guild,
                    roles,
                    view=override.get("view", ()),
                    write=override.get("write", ()),
                )

            out[name] = await ensure_text(category, name, topic, overwrites)

        for name in spec.get("voice", ()):
            out[name] = await ensure_voice(category, name)

        for name in spec.get("stage", ()):
            stage = await ensure_stage(guild, name, category)

            if stage:
                out[name] = stage

    return out
