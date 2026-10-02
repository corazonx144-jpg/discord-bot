"""
layout.py - single source of truth for the Nexus server.

Everything (roles, role order, categories, channels, who can see / write)
is defined in the data tables below. To change the server you edit the
tables, not the code, then run /setup.
"""
from __future__ import annotations

import logging
import re
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
# SMART RECONCILE ENGINE
#
# /setup never blindly creates. It first looks at what already
# exists, matches it to the layout (by name without emoji, and by
# "SECTOR NN" for categories), then repairs / renames / moves it,
# and only creates what is truly missing. Duplicates and leftovers
# inside Nexus sectors are removed. Tickets and temporary voice
# rooms are never touched.
# ============================================================

# guilds currently running /setup (event logging is muted meanwhile)
SETUP_ACTIVE: set[int] = set()


def slug(name: str) -> str:
    """'⚡-arrival-terminal' and '⌁-arrival-terminal' -> 'arrival-terminal'"""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _sector(name: str) -> int | None:
    match = re.search(r"sector\s*(\d+)", name, re.IGNORECASE)
    return int(match.group(1)) if match else None


class SetupReport:
    def __init__(self) -> None:
        self.created: list[str] = []
        self.renamed: list[str] = []
        self.moved: list[str] = []
        self.deleted: list[str] = []
        self.kept: list[str] = []
        self.notes: list[str] = []

    def summary(self, limit: int = 6) -> str:
        parts: list[str] = []

        def block(icon: str, title: str, items: list[str]) -> None:
            if not items:
                return

            shown = [item[:70] for item in items[:limit]]
            text = f"{icon} **{title}** ({len(items)})\n" + "\n".join(
                f"• {item}" for item in shown
            )

            if len(items) > limit:
                text += f"\n• …and {len(items) - limit} more"

            parts.append(text)

        block("➕", "Created", self.created)
        block("✏️", "Renamed / repaired", self.renamed)
        block("📦", "Moved", self.moved)
        block("🗑️", "Deleted (duplicates / leftovers)", self.deleted)
        block("📌", "Left untouched", self.kept)
        block("⚠️", "Notes", self.notes)

        if not parts:
            return "Everything already matches the layout. Nothing to change."

        return "\n\n".join(parts)[:1900]


class _Ctx:
    def __init__(self, guild, db, report, cleanup, panel_ids) -> None:
        self.guild = guild
        self.db = db
        self.report = report
        self.cleanup = cleanup
        self.panel_ids = panel_ids
        self.gone: set[int] = set()   # deleted this run
        self.kept: set[int] = set()   # channels that belong to the layout


async def _is_protected(ctx: _Ctx, channel) -> bool:
    """Tickets and temporary rooms must never be deleted or merged,
    even if the database was reset."""

    if isinstance(channel, discord.TextChannel) and channel.name.startswith("ticket-"):
        return True

    if isinstance(channel, discord.VoiceChannel) and channel.name.startswith("🎙"):
        return True

    try:
        if await ctx.db.ticket_owner(channel.id) is not None:
            return True

        if await ctx.db.room(channel.id):
            return True
    except Exception:
        log.exception("Protection lookup failed")

    return False


async def _delete(ctx: _Ctx, channel, reason: str) -> bool:
    if await _is_protected(ctx, channel):
        return False

    try:
        await channel.delete(reason=reason)
    except discord.NotFound:
        pass
    except discord.Forbidden:
        ctx.report.notes.append(f"No permission to delete #{channel.name}")
        return False

    ctx.gone.add(channel.id)
    ctx.report.deleted.append(f"#{channel.name}")
    return True


async def _create(ctx: _Ctx, name, category, topic, kind, overwrites):
    ow = overwrites if overwrites is not None else category.overwrites

    try:
        if kind == "text":
            return await ctx.guild.create_text_channel(
                name, category=category, topic=topic,
                overwrites=ow, reason="Nexus setup",
            )

        if kind == "voice":
            return await ctx.guild.create_voice_channel(
                name, category=category,
                overwrites=ow, reason="Nexus setup",
            )

        return await ctx.guild.create_stage_channel(
            name, category=category,
            overwrites=ow, reason="Nexus setup",
        )

    except discord.HTTPException as exc:
        # e.g. stage channels need a Community server
        ctx.report.notes.append(f"Could not create {name}: {exc}")
        return None


async def _place(
    ctx: _Ctx,
    pool: list,
    name: str,
    category,
    *,
    kind: str,
    topic: str = "",
    overwrites=None,
):
    """Find the channel that represents `name`, repair it, remove its
    duplicates. Create it only if nothing matches."""

    wanted = slug(name)

    candidates = [
        channel
        for channel in pool
        if channel.id not in ctx.gone and slug(channel.name) == wanted
    ]

    if not candidates:
        channel = await _create(ctx, name, category, topic, kind, overwrites)

        if channel:
            ctx.kept.add(channel.id)
            ctx.report.created.append(name)

        return channel

    # best = already in the right sector, exact name, owns a panel, oldest
    candidates.sort(
        key=lambda c: (
            c.category_id != category.id,
            c.name != name,
            c.id not in ctx.panel_ids,
            c.id,
        )
    )

    best, duplicates = candidates[0], candidates[1:]

    changes: dict = {}

    if best.name != name:
        changes["name"] = name
        ctx.report.renamed.append(f"{best.name} → {name}")

    if best.category_id != category.id:
        changes["category"] = category
        ctx.report.moved.append(name)

    if kind == "text" and (best.topic or "") != topic:
        changes["topic"] = topic

    if overwrites is not None:
        changes["overwrites"] = overwrites
    else:
        changes["sync_permissions"] = True

    try:
        await best.edit(reason="Nexus smart setup", **changes)
    except discord.Forbidden:
        ctx.report.notes.append(f"No permission to edit #{best.name}")
    except discord.HTTPException as exc:
        ctx.report.notes.append(f"Could not edit #{best.name}: {exc}")

    ctx.kept.add(best.id)

    for duplicate in duplicates:
        if ctx.cleanup:
            await _delete(ctx, duplicate, "Nexus setup: duplicate")
        else:
            ctx.report.kept.append(f"#{duplicate.name} (duplicate)")

    return best


async def _reconcile_category(ctx: _Ctx, cats: list, name: str, overwrites):
    number = _sector(name)

    candidates = [
        cat
        for cat in cats
        if cat.id not in ctx.gone
        and (
            cat.name.casefold() == name.casefold()
            or (number is not None and _sector(cat.name) == number)
        )
    ]

    if not candidates:
        category = await ctx.guild.create_category(
            name, overwrites=overwrites, reason="Nexus setup"
        )
        ctx.report.created.append(name)
        return category, []

    candidates.sort(key=lambda c: (c.name != name, -len(c.channels), c.position))
    best, extras = candidates[0], candidates[1:]

    if best.name != name:
        ctx.report.renamed.append(f"{best.name} → {name}")

    try:
        await best.edit(
            name=name, overwrites=overwrites, reason="Nexus smart setup"
        )
    except discord.HTTPException as exc:
        ctx.report.notes.append(f"Could not edit category {best.name}: {exc}")

    return best, extras


async def build_structure(
    guild: discord.Guild,
    roles: dict[str, discord.Role],
    db,
    report: SetupReport,
    cleanup: bool = True,
) -> dict[str, discord.abc.GuildChannel]:
    """Reconciles the live server with CATEGORIES.
    Returns {name: channel} so bot.py can attach panels."""

    fetched = await guild.fetch_channels()

    cats = [c for c in fetched if isinstance(c, discord.CategoryChannel)]
    texts = [c for c in fetched if isinstance(c, discord.TextChannel)]
    voices = [c for c in fetched if isinstance(c, discord.VoiceChannel)]
    stages = [c for c in fetched if isinstance(c, discord.StageChannel)]

    ctx = _Ctx(
        guild, db, report, cleanup, await db.panel_channel_ids(guild.id)
    )

    out: dict = {}
    best_by_number: dict[int, discord.CategoryChannel] = {}
    extra_cats: list = []
    managed_ids: set[int] = set()
    order: list[tuple] = []   # (category, [text/voice channels in order])

    for spec in CATEGORIES:
        category, extras = await _reconcile_category(
            ctx,
            cats,
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
        managed_ids.add(category.id)
        ctx.kept.add(category.id)

        number = _sector(spec["name"])

        if number is not None:
            best_by_number[number] = category

        for extra in extras:
            managed_ids.add(extra.id)
            extra_cats.append((extra, number))

        placed: list = []

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

            channel = await _place(
                ctx, texts, name, category,
                kind="text", topic=topic, overwrites=overwrites,
            )

            if channel:
                out[name] = channel
                placed.append(channel)

        for name in spec.get("voice", ()):
            channel = await _place(ctx, voices, name, category, kind="voice")

            if channel:
                out[name] = channel
                placed.append(channel)

        for name in spec.get("stage", ()):
            channel = await _place(ctx, stages, name, category, kind="stage")

            if channel:
                out[name] = channel

        order.append((category, placed))

    # ---- leftovers inside Nexus sectors --------------------------------

    sector_of = {cat.id: number for cat, number in extra_cats}

    for channel in fetched:
        if isinstance(channel, discord.CategoryChannel):
            continue

        if channel.id in ctx.kept or channel.id in ctx.gone:
            continue

        if channel.category_id not in managed_ids:
            continue

        if await _is_protected(ctx, channel):
            # live ticket / room sitting in a duplicate sector: rescue it
            number = sector_of.get(channel.category_id)
            target = best_by_number.get(number) if number is not None else None

            if target:
                with suppress(discord.HTTPException):
                    await channel.edit(category=target, reason="Nexus setup")

            continue

        if cleanup:
            await _delete(ctx, channel, "Nexus setup: not part of the layout")
        else:
            report.kept.append(f"#{channel.name} (not in layout)")

    for extra, _number in extra_cats:
        if not cleanup:
            report.kept.append(f"{extra.name} (duplicate sector)")
            continue

        still_used = any(
            c.category_id == extra.id and c.id not in ctx.gone
            for c in fetched
            if not isinstance(c, discord.CategoryChannel)
        )

        if still_used:
            continue

        try:
            await extra.delete(reason="Nexus setup: duplicate sector")
            ctx.gone.add(extra.id)
            report.deleted.append(extra.name)
        except discord.HTTPException:
            pass

    # ---- ordering ----------------------------------------------------------

    try:
        final = {c.id: c for c in await guild.fetch_channels()}

        ordered = [out[spec["name"]] for spec in CATEGORIES]
        positions = [final[c.id].position for c in ordered if c.id in final]

        if positions != sorted(positions):
            for category in ordered:
                await category.move(end=True)

            report.notes.append("Sectors re-ordered")

        for category, placed in order:
            positions = [final[c.id].position for c in placed if c.id in final]

            if positions != sorted(positions):
                for channel in placed:
                    await channel.move(end=True, category=category)

                report.notes.append(f"Channels re-ordered in {category.name}")

    except discord.HTTPException:
        log.exception("Reordering failed")

    return out


async def sync_roles(
    guild: discord.Guild,
    report: SetupReport | None = None,
    cleanup: bool = True,
) -> dict[str, discord.Role]:
    report = report or SetupReport()
    me = guild.me
    roles: dict[str, discord.Role] = {}

    for key, name, colour, hoist, perms in ROLE_SPECS:
        kwargs = dict(
            colour=discord.Colour(colour),
            hoist=hoist,
            permissions=discord.Permissions(**perms),
        )

        candidates = [
            role
            for role in guild.roles
            if not role.managed
            and role != guild.default_role
            and role.name.strip().casefold() == name.casefold()
        ]

        if not candidates:
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

            report.created.append(f"role {name}")
            roles[key] = role
            continue

        # keep the role that already has the most members
        candidates.sort(key=lambda r: (-len(r.members), r.name != name, r.id))
        role, duplicates = candidates[0], candidates[1:]

        if role < me.top_role:
            if role.name != name:
                report.renamed.append(f"role {role.name} → {name}")

            with suppress(discord.Forbidden, discord.HTTPException):
                await role.edit(name=name, reason="Nexus role sync", **kwargs)

        for duplicate in duplicates:
            if not cleanup:
                report.kept.append(f"role {duplicate.name} (duplicate)")
                continue

            if duplicate >= me.top_role:
                report.notes.append(
                    f"Duplicate role {duplicate.name} is above my role"
                )
                continue

            for member in list(duplicate.members):
                if role not in member.roles:
                    with suppress(discord.Forbidden, discord.HTTPException):
                        await member.add_roles(role, reason="Nexus: merge duplicate role")

            with suppress(discord.Forbidden, discord.HTTPException):
                await duplicate.delete(reason="Nexus: duplicate role")
                report.deleted.append(f"role {duplicate.name}")

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
