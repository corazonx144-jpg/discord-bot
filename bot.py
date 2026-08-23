from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from contextlib import suppress
from datetime import UTC, datetime

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from database import Database
from views import (
    ApprovalView,
    CloseTicketView,
    RoleView,
    RoomPanelView,
    StageTransitionView,
    TicketView,
    VerificationView,
    hx_embed,
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("nexus")

INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.members = True
INTENTS.message_content = True

# ANSI helpers
CYN = "\u001b[1;36m"
GRN = "\u001b[1;32m"
YLW = "\u001b[1;33m"
RED = "\u001b[1;31m"
WHT = "\u001b[1;37m"
BLK = "\u001b[0;30m"
RST = "\u001b[0m"
DIM = "\u001b[2m"
MAG = "\u001b[1;35m"
BLU = "\u001b[1;34m"


def _hash_id(uid: int) -> str:
    return hashlib.sha256(str(uid).encode()).hexdigest()[:16].upper()


class NexusBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(command_prefix="Sl", case_insensitive=True, intents=INTENTS, help_command=None)
        self.database = Database()
        self.web_runner: web.AppRunner | None = None
        self.room_expiry_task: asyncio.Task | None = None

    async def setup_hook(self) -> None:
        await self.database.initialize()
        self.add_view(VerificationView())
        self.add_view(ApprovalView(self.database))
        self.add_view(RoleView(self.database))
        self.add_view(TicketView(self.database))
        self.add_view(CloseTicketView(self.database))
        self.add_view(RoomPanelView(self.database))
        self.add_view(StageTransitionView(self.database))
        self.room_expiry_task = asyncio.create_task(self.expire_temporary_rooms())
        await self.start_health_server()
        development_guild = os.getenv("DEV_GUILD_ID")
        if development_guild:
            guild = discord.Object(id=int(development_guild))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to development guild %s", development_guild)
        else:
            await self.tree.sync()
            log.info("Synced global commands")

    async def start_health_server(self) -> None:
        app = web.Application()
        app.router.add_get("/", lambda _: web.Response(text="Nexus bot online"))
        app.router.add_get("/health", lambda _: web.json_response({"status": "ok", "discord_ready": self.is_ready()}))
        self.web_runner = web.AppRunner(app)
        await self.web_runner.setup()
        site = web.TCPSite(self.web_runner, "0.0.0.0", int(os.getenv("PORT", "10000")))
        await site.start()

    async def close(self) -> None:
        if self.room_expiry_task:
            self.room_expiry_task.cancel()
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().close()

    async def expire_temporary_rooms(self) -> None:
        while not self.is_closed():
            await asyncio.sleep(30)
            for channel_id in await self.database.expired_rooms(int(time.time())):
                channel = self.get_channel(channel_id)
                await self.database.remove_room(channel_id)
                if isinstance(channel, discord.VoiceChannel):
                    with suppress(discord.NotFound):
                        await channel.delete(reason="Temporary room timer expired")


bot = NexusBot()


async def ensure_role(guild: discord.Guild, name: str, colour: discord.Colour) -> discord.Role:
    return discord.utils.get(guild.roles, name=name) or await guild.create_role(name=name, colour=colour, reason="Nexus setup")


async def ensure_category(guild: discord.Guild, name: str, overwrites: dict, *legacy_names: str) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category is None:
        category = next((item for item in guild.categories if item.name in legacy_names), None)
    if category is None:
        category = await guild.create_category(name, overwrites=overwrites, reason="Nexus setup")
    else:
        await category.edit(name=name, overwrites=overwrites, reason="Nexus layout repair")
    return category


async def ensure_text(category: discord.CategoryChannel, name: str) -> discord.TextChannel:
    channel = discord.utils.get(category.text_channels, name=name)
    if channel is None:
        channel = await category.guild.create_text_channel(name, category=category, reason="Nexus setup")
    return channel


async def ensure_voice(category: discord.CategoryChannel, name: str) -> None:
    if not discord.utils.get(category.voice_channels, name=name):
        await category.guild.create_voice_channel(name, category=category, reason="Nexus setup")


async def ensure_panel(channel: discord.TextChannel, panel_key: str, embed: discord.Embed, view: discord.ui.View) -> None:
    stored = await bot.database.panel_message(channel.guild.id, panel_key)
    if stored:
        stored_channel = channel.guild.get_channel(stored[0])
        if isinstance(stored_channel, discord.TextChannel):
            with suppress(discord.NotFound, discord.Forbidden):
                message = await stored_channel.fetch_message(stored[1])
                await message.edit(embed=embed, view=view)
                return
    message = await channel.send(embed=embed, view=view)
    await bot.database.save_panel(channel.guild.id, panel_key, channel.id, message.id)


def _public_overwrites(guild: discord.Guild, me: discord.Member) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True),
        me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }


def _verified_base_overwrites(guild: discord.Guild, me: discord.Member, roles: dict) -> dict:
    o = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
        roles["verified"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        roles["elite"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        roles["guest"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        roles["support"]: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True),
    }
    return o


def _add_role_overwrite(base: dict, role: discord.Role) -> dict:
    o = dict(base)
    o[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    return o


def cmd_embed(header: str, lines: str, colour: int = 0x00FF41) -> discord.Embed:
    """Clean CMD-style embed."""
    body = (
        f"{CYN}╔══════════════════════════════════════════════════════════════╗{RST}\n"
        f"{CYN}║{RST}  {WHT}{header:^56}{RST}  {CYN}║{RST}\n"
        f"{CYN}╠══════════════════════════════════════════════════════════════╣{RST}\n"
        f"{lines}\n"
        f"{CYN}╚══════════════════════════════════════════════════════════════╝{RST}"
    )
    embed = discord.Embed(description=f"```ansi\n{body}\n```", colour=colour)
    embed.set_footer(text="C:\\NEXUS> _")
    return embed


def arrival_terminal_embed(guild: discord.Guild) -> discord.Embed:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = (
        f"{CYN}[SYS]{RST}   {guild.name}  |  {ts}\n"
        f"{GRN}[OK]{RST}    Secure gateway online\n"
        f"{GRN}[OK]{RST}    Biometric scanner active\n"
        f"{YLW}[WARN]{RST} Clearance: PENDING APPROVAL\n\n"
        f"{WHT}> INITIATE VERIFY.EXE to begin identity scan{RST}\n"
        f"{DIM}> No automatic role grants. Admin review required.{RST}"
    )
    return cmd_embed("ARRIVAL TERMINAL", lines, colour=0x22D3EE)


def rules_embed(guild: discord.Guild) -> discord.Embed:
    lines = (
        f"{CYN}[01]{RST}  RESPECT ALL PERSONNEL  {DIM}— No harassment / toxicity{RST}\n"
        f"{CYN}[02]{RST}  CLEARANCE REQUIRED     {DIM}— No access beyond Sector 01{RST}\n"
        f"{CYN}[03]{RST}  CLASSIFIED MATERIAL    {DIM}— No doxxing or leaks{RST}\n"
        f"{CYN}[04]{RST}  COMMUNICATION PROTOCOL {DIM}— Use correct channels{RST}\n"
        f"{CYN}[05]{RST}  SECURITY BREACH        {DIM}— Report to Moderator{RST}\n"
        f"{CYN}[06]{RST}  VOICE NODE ETIQUETTE   {DIM}— No earrape / spam{RST}\n"
        f"{CYN}[07]{RST}  EXTERNAL LINKS         {DIM}— No malicious URLs{RST}\n"
        f"{CYN}[08]{RST}  BOT INTERACTION        {DIM}— Do not abuse commands{RST}\n\n"
        f"{RED}[VIOLATION]{RST} Immediate access termination."
    )
    return cmd_embed("PROTOCOL RULES", lines, colour=0xFF4444)


def role_matrix_embed() -> discord.Embed:
    lines = (
        f"{BLU}Verified{RST}      {DIM}Base access  |  Sectors 02-07{RST}\n"
        f"{YLW}Elite Agent{RST}   {DIM}Full access  |  All sectors{RST}\n"
        f"{WHT}Guest Node{RST}    {DIM}Read-only    |  Sector 03{RST}\n"
        f"{GRN}Support Team{RST}  {DIM}Tickets      |  Manage messages{RST}\n"
        f"{BLU}Developer{RST}     {DIM}Dev terminal |  Code & bot dev{RST}\n"
        f"{YLW}Moderator{RST}     {DIM}Mod ops      |  Kick, mute, warn{RST}\n"
        f"{MAG}VIP{RST}           {DIM}VIP lounge   |  Premium member{RST}\n"
        f"{RED}Streamer{RST}      {DIM}Stream deck  |  Content creator{RST}\n"
        f"{CYN}Artist{RST}        {DIM}Art gallery  |  Visual artist{RST}\n"
        f"{MAG}Musician{RST}      {DIM}Music lab    |  Music producer{RST}"
    )
    return cmd_embed("ROLE MATRIX", lines, colour=0x7C3AED)


async def build_layout(guild: discord.Guild) -> None:
    me = guild.me
    if not me:
        raise RuntimeError("Bot member unavailable")

    # ── Roles ──
    r = {
        "verified": await ensure_role(guild, "Verified", discord.Colour.blurple()),
        "elite": await ensure_role(guild, "Elite Agent", discord.Colour.gold()),
        "guest": await ensure_role(guild, "Guest Node", discord.Colour.light_grey()),
        "support": await ensure_role(guild, "Support Team", discord.Colour.green()),
        "developer": await ensure_role(guild, "Developer", discord.Colour.dark_blue()),
        "moderator": await ensure_role(guild, "Moderator", discord.Colour.orange()),
        "vip": await ensure_role(guild, "VIP", discord.Colour.magenta()),
        "streamer": await ensure_role(guild, "Streamer", discord.Colour.red()),
        "artist": await ensure_role(guild, "Artist", discord.Colour.teal()),
        "musician": await ensure_role(guild, "Musician", discord.Colour.purple()),
    }

    public = _public_overwrites(guild, me)
    vbase = _verified_base_overwrites(guild, me, r)

    # ── SECTOR 01 │ SYSTEM CORE (public) ──
    core = await ensure_category(
        guild, "🔒 ─ SECTOR 01 │ SYSTEM CORE", public,
        "🔒 -- [ SECTOR 01 ] SYSTEM CORE",
    )
    arrival = await ensure_text(core, "⌁-arrival-terminal")
    verify = await ensure_text(core, "🛡️-verify-access")
    await ensure_text(core, "📡-broadcasts")
    rules_ch = await ensure_text(core, "📜-protocol-rules")

    # ── SECTOR 02 │ CLEARANCE GATE (Verified only) ──
    clearance = await ensure_category(
        guild, "🧬 ─ SECTOR 02 │ CLEARANCE GATE", vbase,
        "🧬 -- [ SECTOR 02 ] CLEARANCE GATE",
    )
    roles_ch = await ensure_text(clearance, "⚡-select-clearance")
    await ensure_text(clearance, "📋-verification-logs")

    # ── SECTOR 03 │ TERMINAL CHAT (Verified+) ──
    terminal = await ensure_category(
        guild, "⚡ ─ SECTOR 03 │ TERMINAL CHAT", vbase,
        "⚡ -- [ SECTOR 02 ] TERMINAL CHAT",
        "⚡ ─ SECTOR 02 │ TERMINAL CHAT",
    )
    await ensure_text(terminal, "🌐-global-network")
    await ensure_text(terminal, "💻-command-shell")
    await ensure_text(terminal, "📦-payload-archive")

    # ── Role-specific categories ──
    dev_cat = await ensure_category(guild, "🧪 ─ DEV & MOD OPS", _add_role_overwrite(vbase, r["developer"]))
    await ensure_text(dev_cat, "🧪-dev-terminal")

    mod_cat = await ensure_category(guild, "🛡️ ─ MODERATOR OPS", _add_role_overwrite(vbase, r["moderator"]))
    await ensure_text(mod_cat, "🛡️-mod-ops")

    vip_cat = await ensure_category(guild, "👑 ─ VIP LOUNGE", _add_role_overwrite(vbase, r["vip"]))
    await ensure_text(vip_cat, "👑-vip-lounge")

    art_cat = await ensure_category(guild, "🎨 ─ CREATIVE HUB", _add_role_overwrite(vbase, r["artist"]))
    await ensure_text(art_cat, "🎨-art-gallery")

    music_cat = await ensure_category(guild, "🎵 ─ MUSIC LAB", _add_role_overwrite(vbase, r["musician"]))
    await ensure_text(music_cat, "🎵-music-lab")

    stream_cat = await ensure_category(guild, "📺 ─ STREAM DECK", _add_role_overwrite(vbase, r["streamer"]))
    await ensure_text(stream_cat, "📺-stream-deck")

    # ── SECTOR 04 │ SECURE NODES (voice, Verified+) ──
    secure = await ensure_category(
        guild, "🎧 ─ SECTOR 04 │ SECURE NODES", vbase,
        "🎧 -- [ SECTOR 03 ] SECURE NODES",
        "🎧 ─ SECTOR 03 │ SECURE NODES",
    )
    for name in ("🔒 Node 01 • Safe Zone", "🛡️ Node 02 • Operations", "⚡ Node 03 • Alpha"):
        await ensure_voice(secure, name)

    # ── SECTOR 05 │ ROOM GENERATOR (Verified+) ──
    rooms = await ensure_category(guild, "🎛️ ─ ROOM GENERATOR", vbase)
    room_panel = await ensure_text(rooms, "🎛️-create-your-room")

    # ── SECTOR 06 │ SUPPORT NODE (Verified+) ──
    support_cat = await ensure_category(guild, "🎫 ─ SUPPORT NODE", vbase)
    tickets_ch = await ensure_text(support_cat, "🎫-open-a-ticket")
    await ensure_text(support_cat, "📋-support-protocol")

    # ── SECTOR 07 │ INTELLIGENCE ARCHIVE (Verified+) ──
    intel = await ensure_category(
        guild, "📁 ─ SECTOR 07 │ INTELLIGENCE ARCHIVE", vbase,
        "📁 -- [ SECTOR 04 ] INTELLIGENCE ARCHIVE",
        "📁 ─ SECTOR 04 │ INTELLIGENCE ARCHIVE",
        "📁 ─ SECTOR 05 │ INTELLIGENCE ARCHIVE",
    )
    await ensure_text(intel, "📁-mission-briefs")
    await ensure_text(intel, "📊-data-logs")

    # ── SECTOR 08 │ CONTROL & LOGS (Owner + Admin only) ──
    control_ow = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    if guild.owner:
        control_ow[guild.owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    control = await ensure_category(
        guild, "👁️ ─ SECTOR 08 │ CONTROL & LOGS", control_ow,
        "👁️ -- [ SECTOR 05 ] CONTROL & LOGS",
        "👁️ ─ SECTOR 05 │ CONTROL & LOGS",
        "👁️ ─ CONTROL & LOGS",
    )
    await ensure_text(control, "📊-surveillance-logs")
    await ensure_text(control, "🔐-approval-queue")
    role_matrix_ch = await ensure_text(control, "📋-role-matrix")

    # ── Panels ──
    await ensure_panel(arrival, "arrival", arrival_terminal_embed(guild), VerificationView())

    await ensure_panel(verify, "verification", cmd_embed("ACCESS // STAGE 01",
        f"{CYN}[INFO]{RST}  Transmit an access request.\n"
        f"{YLW}[WARN]{RST}  Approval opens Clearance Gate only."), discord.ui.View())

    await ensure_panel(roles_ch, "roles", cmd_embed("CLEARANCE // STAGE 02",
        f"{CYN}[INFO]{RST}  Request one clearance.\n"
        f"{YLW}[WARN]{RST}  Owner must approve before final sectors unlock."), RoleView(bot.database))

    await ensure_panel(tickets_ch, "tickets", cmd_embed("SUPPORT TERMINAL",
        f"{GRN}[OK]{RST}  Open one private, persistent support ticket."), TicketView(bot.database))

    await ensure_panel(room_panel, "room_generator", cmd_embed("VOICE LAB",
        f"{CYN}[INFO]{RST}  Create a public or private voice room.\n"
        f"{YLW}[WARN]{RST}  Self-destructs on owner exit or timer expiry."), RoomPanelView(bot.database))

    # Rules panel (static)
    await ensure_panel(rules_ch, "rules", rules_embed(guild), discord.ui.View())

    # Role matrix panel (static, admin reference)
    await ensure_panel(role_matrix_ch, "role_matrix", role_matrix_embed(), discord.ui.View())


async def wipe_layout(guild: discord.Guild) -> None:
    for channel in [c for c in list(guild.channels) if not isinstance(c, discord.CategoryChannel)]:
        with suppress(discord.Forbidden, discord.NotFound):
            await channel.delete(reason="Owner-authorized Nexus rebuild")
    for category in list(guild.categories):
        with suppress(discord.Forbidden, discord.NotFound):
            await category.delete(reason="Owner-authorized Nexus rebuild")
    for name in ("Verified", "Elite Agent", "Guest Node", "Support Team", "Developer", "Moderator", "VIP", "Streamer", "Artist", "Musician"):
        role = discord.utils.get(guild.roles, name=name)
        if role and not role.managed:
            with suppress(discord.Forbidden):
                await role.delete(reason="Owner-authorized Nexus rebuild")


@bot.event
async def on_ready() -> None:
    log.info("Online as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


@bot.event
async def on_member_join(member: discord.Member) -> None:
    """Ultra-professional incoming scan with separator, @mention, avatar, hash."""
    await bot.database.set_member_stage(member.guild.id, member.id, "arrival")
    channel = discord.utils.get(member.guild.text_channels, name="⌁-arrival-terminal")
    if channel:
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

        # 1. Send separator
        sep = (
            f"{CYN}▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬{RST}\n"
            f"{WHT}  INCOMING TRANSMISSION  |  {ts}{RST}\n"
            f"{CYN}▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬{RST}"
        )
        sep_embed = discord.Embed(description=f"```ansi\n{sep}\n```", colour=0x22D3EE)
        sep_msg = await channel.send(embed=sep_embed)

        # 2. Main scan embed with @mention inside
        scan_lines = (
            f"{CYN}[SCAN]{RST}   Biometric lock engaged\n"
            f"{GRN}[TARGET]{RST} {member.mention}\n"
            f"{CYN}[UID]{RST}    {member.id}\n"
            f"{CYN}[HASH]{RST}   {_hash_id(member.id)}\n"
            f"{CYN}[TIME]{RST}   {ts}\n"
            f"{YLW}[STATUS]{RST} UNVERIFIED — SECTOR 01\n"
            f"{RED}[ALERT]{RST}  Clearance required for sector access\n\n"
            f"{GRN}[ACTION]{RST} Execute VERIFY.EXE below"
        )
        scan_embed = cmd_embed(f"WELCOME  {member.name.upper()}", scan_lines, colour=0xFF4444)
        scan_embed.set_thumbnail(url=member.display_avatar.url)
        scan_msg = await channel.send(content=member.mention, embed=scan_embed, view=VerificationView())

        # 4. Scan stays permanent — no auto-delete


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    if not before.channel or before.channel == after.channel:
        return
    record = await bot.database.room(before.channel.id)
    if not record:
        return
    owner_id, _ = record
    if member.id == owner_id or not before.channel.members:
        await bot.database.remove_room(before.channel.id)
        with suppress(discord.NotFound):
            await before.channel.delete(reason="Temporary room session ended")


@bot.tree.command(name="setup", description="Create or repair the Nexus server layout without deleting existing channels.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.administrator or not interaction.guild:
        return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
    guild = interaction.guild
    me = guild.me
    if not me or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
        return await interaction.response.send_message("I need Manage Channels and Manage Roles.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    await build_layout(guild)
    await interaction.followup.send("Nexus layout is ready. All sectors, roles and channels deployed/repaired.", ephemeral=True)


@bot.tree.command(name="clear", description="Delete a limited number of recent messages.")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(amount="Number of messages to delete (1–100)")
async def clear(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 100]) -> None:
    if not interaction.user.guild_permissions.manage_messages or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Manage Messages permission required.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Deleted {len(deleted)} messages.", ephemeral=True)


@bot.tree.command(name="status", description="Show the bot\'s current operational status.")
async def status(interaction: discord.Interaction) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    embed = cmd_embed(
        "NEXUS STATUS",
        f"{GRN}[OK]{RST}   Latency: `{round(bot.latency * 1000)} ms`\n"
        f"{GRN}[OK]{RST}   Database: `online`\n"
        f"{GRN}[OK]{RST}   Persistent controls: `armed`\n"
        f"{CYN}[TIME]{RST}  {ts}\n"
        f"{CYN}[INFO]{RST}  Sectors: 8  |  Roles: 10  |  Nodes: 3",
        colour=0x22D3EE,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
    log.exception("Application command failed", exc_info=error)
    message = "The command could not be completed. Check the Render logs for the exact error."
    if isinstance(error, app_commands.MissingPermissions):
        message = "You do not have permission to use this command."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


@bot.command(name="setup")
@commands.guild_only()
@commands.has_permissions(administrator=True)
async def prefix_setup(ctx: commands.Context) -> None:
    await build_layout(ctx.guild)
    await ctx.reply("Nexus repair complete.", mention_author=False)


@bot.command(name="clear")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def prefix_clear(ctx: commands.Context, amount: int = 10) -> None:
    amount = max(1, min(100, amount))
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"Purged {len(deleted) - 1} messages.", delete_after=4)


@bot.command(name="rebuild")
@commands.guild_only()
async def prefix_rebuild(ctx: commands.Context, confirmation: str = "") -> None:
    if ctx.author.id != ctx.guild.owner_id:
        return await ctx.reply("Only the server owner can rebuild the server.", mention_author=False)
    if confirmation != "NEXUS-RESET":
        return await ctx.reply("This permanently deletes every channel and bot-managed role. To continue: `Slrebuild NEXUS-RESET`", mention_author=False)
    await wipe_layout(ctx.guild)
    await build_layout(ctx.guild)


@prefix_setup.error
@prefix_clear.error
async def prefix_command_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.MissingPermissions):
        await ctx.reply("You do not have permission for this command.", mention_author=False)
    else:
        log.exception("Prefix command failed", exc_info=error)
        await ctx.reply("Command failed. Check Render logs.", mention_author=False)


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Add it as a Render environment variable.")
    bot.run(token, log_handler=None)
