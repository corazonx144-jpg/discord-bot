from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import re
import time
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from database import Database
from views import (
    ApprovalView,
    AutoModConfigView,
    CloseTicketView,
    ReactionRoleCreateView,
    RoleView,
    RoomPanelView,
    StageTransitionView,
    SuggestionVoteView,
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
INTENTS.bans = True
INTENTS.voice_states = True
INTENTS.reactions = True

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
        self.automod_cache: dict[int, tuple] = {}
        self.spam_tracker: dict[tuple[int, int], list[float]] = {}

    async def setup_hook(self) -> None:
        await self.database.initialize()
        self.add_view(VerificationView())
        self.add_view(ApprovalView(self.database))
        self.add_view(RoleView(self.database))
        self.add_view(TicketView(self.database))
        self.add_view(CloseTicketView(self.database))
        self.add_view(RoomPanelView(self.database))
        self.add_view(StageTransitionView(self.database))
        self.add_view(ReactionRoleCreateView(self.database))
        self.add_view(AutoModConfigView(self.database))
        self.room_expiry_task = asyncio.create_task(self.expire_temporary_rooms())
        asyncio.create_task(self._automod_refresh_loop())
        asyncio.create_task(self._voice_xp_loop())
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

    async def _automod_refresh_loop(self) -> None:
        while not self.is_closed():
            self.automod_cache = {}
            await asyncio.sleep(60)

    async def _voice_xp_loop(self) -> None:
        while not self.is_closed():
            await asyncio.sleep(60)
            for guild in self.guilds:
                for member in guild.members:
                    if member.voice and member.voice.channel and not member.voice.self_mute and not member.voice.deaf:
                        xp, level, msgs, vmins = await self.database.get_level(guild.id, member.id)
                        vmins += 1
                        xp += random.randint(5, 15)
                        new_level = level
                        while xp >= (new_level + 1) * 100:
                            new_level += 1
                            xp -= new_level * 100
                        await self.database.set_level(guild.id, member.id, xp, new_level, msgs, vmins)

    async def _get_automod(self, guild_id: int) -> tuple | None:
        if guild_id not in self.automod_cache:
            self.automod_cache[guild_id] = await self.database.get_automod(guild_id)
        return self.automod_cache[guild_id]

    async def _log(self, guild_id: int, action: str, user_id: int | None = None, target_id: int | None = None, reason: str | None = None, details: str | None = None) -> None:
        await self.database.add_audit(guild_id, action, user_id, target_id, reason, details, time.time())
        guild = self.get_guild(guild_id)
        if guild:
            log_ch = discord.utils.get(guild.text_channels, name="📊-surveillance-logs")
            if log_ch:
                ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
                embed = discord.Embed(title=f"🔍 {action}", colour=0x5865F2, timestamp=datetime.now(UTC))
                if user_id:
                    embed.add_field(name="User", value=f"<@{user_id}>", inline=True)
                if target_id:
                    embed.add_field(name="Target", value=f"<@{target_id}>", inline=True)
                if reason:
                    embed.add_field(name="Reason", value=reason, inline=False)
                if details:
                    embed.add_field(name="Details", value=details[:1000], inline=False)
                embed.set_footer(text=f"ID: {guild_id} • {ts}")
                await log_ch.send(embed=embed)


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



def user_guide_embed() -> discord.Embed:
    """Complete user guide for all members."""
    lines = (
        f"{CYN}╔══════════════════════════════════════════════════════════════╗{RST}\n"
        f"{CYN}║{RST}  {WHT}{'NEXUS USER MANUAL':^56}{RST}  {CYN}║{RST}\n"
        f"{CYN}╠══════════════════════════════════════════════════════════════╣{RST}\n"
        f"{GRN}[01]{RST}  /rank              {DIM}— Check your level & XP{RST}\n"
        f"{GRN}[02]{RST}  /leaderboard       {DIM}— Top 10 members by level{RST}\n"
        f"{GRN}[03]{RST}  /balance           {DIM}— Check your credits{RST}\n"
        f"{GRN}[04]{RST}  /daily             {DIM}— Claim daily reward (24h){RST}\n"
        f"{GRN}[05]{RST}  /pay @user amount  {DIM}— Send credits{RST}\n"
        f"{GRN}[06]{RST}  /work              {DIM}— Work to earn credits{RST}\n"
        f"{GRN}[07]{RST}  /economyboard      {DIM}— Top 10 richest{RST}\n"
        f"{GRN}[08]{RST}  /poll question ... {DIM}— Create a poll in 📊-community-hub{RST}\n"
        f"{GRN}[09]{RST}  /suggest content   {DIM}— Submit a suggestion{RST}\n"
        f"{GRN}[10]{RST}  /8ball question    {DIM}— Magic 8-ball{RST}\n"
        f"{GRN}[11]{RST}  /coinflip          {DIM}— Flip a coin{RST}\n\n"
        f"{YLW}[TICKETS]{RST}  Click 🎫 in 🎫-open-a-ticket\n"
        f"{YLW}[ROOMS]{RST}    Click 🎛️ in 🎛️-create-your-room\n"
        f"{YLW}[CLEARANCE]{RST} 1. VERIFY.EXE → 2. Wait approval → 3. ⚡-select-clearance\n\n"
        f"{RED}[RULES]{RST}    Read 📜-protocol-rules"
    )
    return cmd_embed("USER MANUAL // V2.0", lines, colour=0x00FF41)


def admin_manual_embed() -> discord.Embed:
    """Admin/Mod manual with all moderation commands."""
    lines = (
        f"{CYN}╔══════════════════════════════════════════════════════════════╗{RST}\n"
        f"{CYN}║{RST}  {WHT}{'ADMIN & MOD MANUAL':^56}{RST}  {CYN}║{RST}\n"
        f"{CYN}╠══════════════════════════════════════════════════════════════╣{RST}\n"
        f"{RED}[MODERATION]{RST}\n"
        f"{GRN}[01]{RST}  /warn @user reason       {DIM}— Issue warning{RST}\n"
        f"{GRN}[02]{RST}  /warnings @user          {DIM}— View warnings{RST}\n"
        f"{GRN}[03]{RST}  /clearwarns @user        {DIM}— Clear warnings{RST}\n"
        f"{GRN}[04]{RST}  /kick @user reason       {DIM}— Kick member{RST}\n"
        f"{GRN}[05]{RST}  /ban @user reason days   {DIM}— Ban (0-7d delete){RST}\n"
        f"{GRN}[06]{RST}  /unban user_id           {DIM}— Unban by ID{RST}\n"
        f"{GRN}[07]{RST}  /timeout @user dur       {DIM}— Timeout 30m/1h/1d{RST}\n"
        f"{GRN}[08]{RST}  /purge amount @user(opt) {DIM}— Mass delete{RST}\n"
        f"{GRN}[09]{RST}  /clear amount            {DIM}— Delete 1-100{RST}\n\n"
        f"{RED}[ADMIN]{RST}\n"
        f"{YLW}[01]{RST}  /setup                   {DIM}— Repair layout{RST}\n"
        f"{YLW}[02]{RST}  /verify @user            {DIM}— Instant verify{RST}\n"
        f"{YLW}[03]{RST}  /automod                 {DIM}— AutoMod config{RST}\n"
        f"{YLW}[04]{RST}  /say #ch text            {DIM}— Bot message{RST}\n"
        f"{YLW}[05]{RST}  /embed #ch title ...     {DIM}— Custom embed{RST}\n"
        f"{YLW}[06]{RST}  /status                  {DIM}— Health check{RST}\n\n"
        f"{RED}[AUTOMOD]{RST}  Toggle in 👁️-control-panels or /automod\n"
        f"  • Anti-Spam  • Anti-Link  • Anti-Caps\n\n"
        f"{RED}[LOGS]{RST}  📊-surveillance-logs (all actions)\n"
        f"{RED}[REACTION ROLES]{RST}  👁️-control-panels"
    )
    return cmd_embed("ADMIN MANUAL // V2.0", lines, colour=0xFF4444)


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
    core = await ensure_category(guild, "🔒 ─ SECTOR 01 │ SYSTEM CORE", public, "🔒 -- [ SECTOR 01 ] SYSTEM CORE")
    arrival = await ensure_text(core, "⌁-arrival-terminal")
    verify = await ensure_text(core, "🛡️-verify-access")
    rules_ch = await ensure_text(core, "📜-protocol-rules")
    user_guide = await ensure_text(core, "📖-user-guide")
    admin_manual = await ensure_text(core, "🔒-admin-manual")

    # ── SECTOR 02 │ CLEARANCE GATE (Verified only) ──
    clearance = await ensure_category(guild, "🧬 ─ SECTOR 02 │ CLEARANCE GATE", vbase, "🧬 -- [ SECTOR 02 ] CLEARANCE GATE")
    roles_ch = await ensure_text(clearance, "⚡-select-clearance")

    # ── SECTOR 03 │ TERMINAL CHAT (Verified+) ──
    terminal = await ensure_category(guild, "⚡ ─ SECTOR 03 │ TERMINAL CHAT", vbase, "⚡ -- [ SECTOR 02 ] TERMINAL CHAT", "⚡ ─ SECTOR 02 │ TERMINAL CHAT")
    await ensure_text(terminal, "🌐-global-network")
    await ensure_text(terminal, "💻-command-shell")
    await ensure_text(terminal, "⭐-starboard")
    await ensure_text(terminal, "📊-community-hub")

    # ── SECTOR 04 │ SECURE NODES (voice, Verified+) ──
    secure = await ensure_category(guild, "🎧 ─ SECTOR 04 │ SECURE NODES", vbase, "🎧 -- [ SECTOR 03 ] SECURE NODES", "🎧 ─ SECTOR 03 │ SECURE NODES")
    for name in ("🔒 Node 01 • Safe Zone", "🛡️ Node 02 • Operations", "⚡ Node 03 • Alpha"):
        await ensure_voice(secure, name)

    # ── SECTOR 05 │ SERVICES (Verified+) ──
    services = await ensure_category(guild, "🎛️ ─ SECTOR 05 │ SERVICES", vbase)
    room_panel = await ensure_text(services, "🎛️-create-your-room")
    tickets_ch = await ensure_text(services, "🎫-open-a-ticket")

    # ── SECTOR 06 │ ARCHIVE (Verified+) ──
    archive = await ensure_category(guild, "📁 ─ SECTOR 06 │ ARCHIVE", vbase, "📁 -- [ SECTOR 04 ] INTELLIGENCE ARCHIVE", "📁 ─ SECTOR 04 │ INTELLIGENCE ARCHIVE", "📁 ─ SECTOR 05 │ INTELLIGENCE ARCHIVE")
    await ensure_text(archive, "📁-mission-briefs")
    await ensure_text(archive, "🏆-leaderboards")

    # ── SECTOR 07 │ CONTROL (Admin only) ──
    control_ow = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }
    if guild.owner:
        control_ow[guild.owner] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
    control = await ensure_category(guild, "👁️ ─ SECTOR 07 │ CONTROL", control_ow, "👁️ -- [ SECTOR 05 ] CONTROL & LOGS", "👁️ ─ SECTOR 05 │ CONTROL & LOGS", "👁️ ─ CONTROL & LOGS")
    await ensure_text(control, "📊-surveillance-logs")
    await ensure_text(control, "🔐-approval-queue")
    await ensure_text(control, "👁️-control-panels")

    # ── Role-specific categories ──
    dev_cat = await ensure_category(guild, "🧪 ─ DEV & MOD OPS", _add_role_overwrite(vbase, r["developer"]))
    await ensure_text(dev_cat, "🧪-dev-terminal")

    vip_cat = await ensure_category(guild, "👑 ─ VIP & CREATIVE", _add_role_overwrite(vbase, r["vip"]))
    await ensure_text(vip_cat, "👑-vip-lounge")
    await ensure_text(vip_cat, "🎨-art-gallery")
    await ensure_text(vip_cat, "🎵-music-lab")
    await ensure_text(vip_cat, "📺-stream-deck")

    # ── SECTOR 08 │ DEPARTURE ──
    depart = await ensure_category(guild, "🚪 ─ SECTOR 08 │ DEPARTURE", vbase)
    await ensure_text(depart, "🚪-departure-terminal")

    # ── Panels ──
    await ensure_panel(arrival, "arrival", arrival_terminal_embed(guild), VerificationView())
    await ensure_panel(verify, "verification", cmd_embed("ACCESS // STAGE 01",
        f"{CYN}[INFO]{RST}  Transmit an access request.\n"
        f"{YLW}[WARN]{RST}  Approval opens Clearance Gate only."), discord.ui.View())
    await ensure_panel(roles_ch, "roles", cmd_embed("CLEARANCE // STAGE 02",
        f"{CYN}[INFO]{RST}  Request one clearance.\n"
        f"{YLW}[WARN]{RST}  Admin must approve."), RoleView(bot.database))
    await ensure_panel(tickets_ch, "tickets", cmd_embed("SUPPORT TERMINAL",
        f"{GRN}[OK]{RST}  Open one private support ticket."), TicketView(bot.database))
    await ensure_panel(room_panel, "room_generator", cmd_embed("VOICE LAB",
        f"{CYN}[INFO]{RST}  Create a public or private voice room.\n"
        f"{YLW}[WARN]{RST}  Self-destructs on owner exit or timer expiry."), RoomPanelView(bot.database))
    await ensure_panel(rules_ch, "rules", rules_embed(guild), discord.ui.View())
    await ensure_panel(user_guide, "user_guide", user_guide_embed(), discord.ui.View())
    await ensure_panel(admin_manual, "admin_manual", admin_manual_embed(), discord.ui.View())

    # Control panels
    ctrl_ch = discord.utils.get(guild.text_channels, name="👁️-control-panels")
    if ctrl_ch:
        await ensure_panel(ctrl_ch, "automod", cmd_embed("AUTOMOD CONFIG",
            f"{CYN}[INFO]{RST}  Toggle protection modules.\n"
            f"{YLW}[01]{RST} Anti-Spam\n"
            f"{YLW}[02]{RST} Anti-Link\n"
            f"{YLW}[03]{RST} Anti-Caps"), AutoModConfigView(bot.database))

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
    await bot.database.set_member_stage(member.guild.id, member.id, "arrival")
    channel = discord.utils.get(member.guild.text_channels, name="⌁-arrival-terminal")
    if channel:
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        sep = (
            f"{CYN}▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬{RST}\n"
            f"{WHT}  INCOMING TRANSMISSION  |  {ts}{RST}\n"
            f"{CYN}▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬{RST}"
        )
        sep_embed = discord.Embed(description=f"```ansi\n{sep}\n```", colour=0x22D3EE)
        await channel.send(embed=sep_embed)
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
        await channel.send(content=member.mention, embed=scan_embed, view=VerificationView())
    await bot._log(member.guild.id, "Member Join", target_id=member.id, details=f"{member} joined the server")


@bot.event
async def on_member_remove(member: discord.Member) -> None:
    channel = discord.utils.get(member.guild.text_channels, name="🚪-departure-terminal")
    if channel:
        ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = (
            f"{RED}[DEPART]{RST} {member.mention}\n"
            f"{CYN}[UID]{RST}    {member.id}\n"
            f"{CYN}[HASH]{RST}   {_hash_id(member.id)}\n"
            f"{DIM}[TIME]{RST}   {ts}\n"
            f"{YLW}[NOTE]{RST}   Access revoked."
        )
        embed = cmd_embed("DEPARTURE TERMINAL", lines, colour=0xFF4444)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)
    await bot._log(member.guild.id, "Member Leave", target_id=member.id, details=f"{member} left the server")


@bot.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState) -> None:
    # Temp rooms cleanup
    if before.channel and before.channel != after.channel:
        record = await bot.database.room(before.channel.id)
        if record:
            owner_id, _ = record
            if member.id == owner_id or not before.channel.members:
                await bot.database.remove_room(before.channel.id)
                with suppress(discord.NotFound):
                    await before.channel.delete(reason="Temporary room session ended")
    # Log voice joins/leaves
    if before.channel != after.channel:
        if after.channel and not before.channel:
            await bot._log(member.guild.id, "Voice Join", user_id=member.id, details=f"Joined {after.channel.name}")
        elif before.channel and not after.channel:
            await bot._log(member.guild.id, "Voice Leave", user_id=member.id, details=f"Left {before.channel.name}")


@bot.event
async def on_message(message: discord.Message) -> None:
    if message.author.bot or not message.guild:
        return

    # Leveling (text)
    xp, level, msgs, vmins = await bot.database.get_level(message.guild.id, message.author.id)
    msgs += 1
    xp += random.randint(10, 25)
    new_level = level
    while xp >= (new_level + 1) * 100:
        new_level += 1
        xp -= new_level * 100
    await bot.database.set_level(message.guild.id, message.author.id, xp, new_level, msgs, vmins)

    if new_level > level:
        lvl_ch = discord.utils.get(message.guild.text_channels, name="🏆-leaderboard")
        if lvl_ch:
            embed = hx_embed(
                "LEVEL UP // RANK INCREASE",
                f"{GRN}[SUCCESS]{RST}  {message.author.mention} reached **Level {new_level}**\n"
                f"{CYN}[XP]{RST}     {xp}/{(new_level+1)*100}",
                colour=0xFFD700,
                member=message.author,
            )
            await lvl_ch.send(embed=embed)

    # Economy (random chance)
    if random.random() < 0.1:  # 10% chance per message
        wallet, bank, _ = await bot.database.get_balance(message.guild.id, message.author.id)
        wallet += random.randint(1, 5)
        await bot.database.set_balance(message.guild.id, message.author.id, wallet, bank, 0)

    # AutoMod
    config = await bot._get_automod(message.guild.id)
    if config:
        anti_spam, anti_link, anti_caps, spam_threshold, mute_duration = config[1], config[2], config[3], config[4], config[5]

        # Anti-link
        if anti_link and re.search(r"http[s]?://|www\.", message.content):
            await message.delete()
            await message.channel.send(f"{message.author.mention} Links are not allowed here.", delete_after=5)
            await bot._log(message.guild.id, "AutoMod: Link Removed", user_id=message.author.id, target_id=message.author.id, details=message.content[:200])
            return

        # Anti-caps
        if anti_caps:
            text = re.sub(r"[^A-Za-z]", "", message.content)
            if len(text) > 10 and sum(1 for c in text if c.isupper()) / len(text) > 0.7:
                await message.delete()
                await message.channel.send(f"{message.author.mention} Excessive caps are not allowed.", delete_after=5)
                await bot._log(message.guild.id, "AutoMod: Caps Removed", user_id=message.author.id, target_id=message.author.id)
                return

        # Anti-spam
        if anti_spam:
            key = (message.guild.id, message.author.id)
            now = time.time()
            if key not in bot.spam_tracker:
                bot.spam_tracker[key] = []
            bot.spam_tracker[key].append(now)
            bot.spam_tracker[key] = [t for t in bot.spam_tracker[key] if now - t < 10]
            if len(bot.spam_tracker[key]) >= spam_threshold:
                await message.channel.send(f"{message.author.mention} Stop spamming!", delete_after=5)
                try:
                    muted_role = discord.utils.get(message.guild.roles, name="Muted")
                    if not muted_role:
                        muted_role = await message.guild.create_role(name="Muted", reason="AutoMod mute role")
                        for ch in message.guild.channels:
                            await ch.set_permissions(muted_role, send_messages=False, speak=False)
                    await message.author.add_roles(muted_role, reason="AutoMod anti-spam")
                    await asyncio.sleep(mute_duration)
                    await message.author.remove_roles(muted_role, reason="AutoMod mute expired")
                except Exception:
                    pass
                await bot._log(message.guild.id, "AutoMod: Spam Mute", user_id=message.author.id, target_id=message.author.id, details=f"Muted for {mute_duration}s")

    await bot.process_commands(message)


@bot.event
async def on_message_delete(message: discord.Message) -> None:
    if message.author.bot or not message.guild:
        return
    await bot._log(message.guild.id, "Message Delete", user_id=message.author.id, details=f"In #{message.channel.name}: {message.content[:500]}")


@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message) -> None:
    if before.author.bot or not before.guild or before.content == after.content:
        return
    await bot._log(before.guild.id, "Message Edit", user_id=before.author.id, details=f"In #{before.channel.name}\n**Before:** {before.content[:400]}\n**After:** {after.content[:400]}")


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    await bot._log(guild.id, "Member Ban", target_id=user.id, details=f"{user} was banned")


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User) -> None:
    await bot._log(guild.id, "Member Unban", target_id=user.id, details=f"{user} was unbanned")


@bot.event
async def on_guild_channel_create(channel: discord.abc.GuildChannel) -> None:
    await bot._log(channel.guild.id, "Channel Create", details=f"#{channel.name} ({channel.type})")


@bot.event
async def on_guild_channel_delete(channel: discord.abc.GuildChannel) -> None:
    await bot._log(channel.guild.id, "Channel Delete", details=f"#{channel.name}")


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    if payload.user_id == bot.user.id:
        return
    role_id = await bot.database.get_reaction_role(payload.guild_id, payload.message_id, str(payload.emoji))
    if role_id:
        guild = bot.get_guild(payload.guild_id)
        if guild:
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            if member and role:
                await member.add_roles(role, reason="Reaction role")

    # Starboard
    if str(payload.emoji) == "⭐":
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return
        if message.author.bot:
            return
        star_count = sum(1 for r in message.reactions if str(r.emoji) == "⭐")
        if star_count < 3:
            return

        sb = await bot.database.get_starboard(payload.guild_id, payload.message_id)
        star_ch = discord.utils.get(guild.text_channels, name="⭐-starboard")
        if not star_ch:
            return

        embed = discord.Embed(colour=0xFFD700, timestamp=message.created_at)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url)
        embed.add_field(name="Source", value=f"[Jump to message]({message.jump_url})", inline=False)
        if message.content:
            embed.description = message.content[:1000]
        if message.attachments and message.attachments[0].content_type and message.attachments[0].content_type.startswith("image"):
            embed.set_image(url=message.attachments[0].url)
        embed.set_footer(text=f"⭐ {star_count} | {message.id}")

        if sb:
            posted_msg = await star_ch.fetch_message(sb[4])
            if posted_msg:
                await posted_msg.edit(embed=embed)
                await bot.database.update_starboard(payload.guild_id, payload.message_id, star_count, sb[4])
        else:
            posted = await star_ch.send(embed=embed)
            await bot.database.add_starboard(payload.guild_id, payload.message_id, payload.channel_id, message.author.id, message.content[:500])
            await bot.database.update_starboard(payload.guild_id, payload.message_id, star_count, posted.id)


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    role_id = await bot.database.get_reaction_role(payload.guild_id, payload.message_id, str(payload.emoji))
    if role_id:
        guild = bot.get_guild(payload.guild_id)
        if guild:
            member = guild.get_member(payload.user_id)
            role = guild.get_role(role_id)
            if member and role:
                await member.remove_roles(role, reason="Reaction role removed")

    # Starboard update on remove
    if str(payload.emoji) == "⭐":
        guild = bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        try:
            message = await channel.fetch_message(payload.message_id)
        except Exception:
            return
        star_count = sum(1 for r in message.reactions if str(r.emoji) == "⭐")
        sb = await bot.database.get_starboard(payload.guild_id, payload.message_id)
        if sb and sb[4]:
            star_ch = discord.utils.get(guild.text_channels, name="⭐-starboard")
            if star_ch:
                try:
                    posted_msg = await star_ch.fetch_message(sb[4])
                    if star_count < 3:
                        await posted_msg.delete()
                        await bot.database.remove_starboard(payload.guild_id, payload.message_id)
                    else:
                        embed = posted_msg.embeds[0]
                        embed.set_footer(text=f"⭐ {star_count} | {message.id}")
                        await posted_msg.edit(embed=embed)
                        await bot.database.update_starboard(payload.guild_id, payload.message_id, star_count, sb[4])
                except Exception:
                    pass


# ── MODERATION COMMANDS ──

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(member="Member to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Manage Messages required.", ephemeral=True)
    case_id = await bot.database.add_warning(interaction.guild.id, member.id, interaction.user.id, reason, time.time())
    await bot._log(interaction.guild.id, "Warn", user_id=interaction.user.id, target_id=member.id, reason=reason, details=f"Case #{case_id}")

    # DM the user
    try:
        embed = hx_embed("WARNING ISSUED",
            f"{YLW}[WARN]{RST}  You received a warning in **{interaction.guild.name}**\n"
            f"{CYN}[REASON]{RST} {reason}\n"
            f"{CYN}[CASE]{RST}   #{case_id}\n"
            f"{CYN}[BY]{RST}     {interaction.user.mention}",
            colour=0xFF4444)
        await member.send(embed=embed)
    except discord.Forbidden:
        pass

    await interaction.response.send_message(f"⚠️ Warned {member.mention} (Case #{case_id}): {reason}", ephemeral=True)


@bot.tree.command(name="warnings", description="View warnings for a member")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(member="Member to check")
async def warnings(interaction: discord.Interaction, member: discord.Member) -> None:
    warns = await bot.database.get_warnings(interaction.guild.id, member.id)
    if not warns:
        return await interaction.response.send_message(f"{member.mention} has no warnings.", ephemeral=True)
    lines = ""
    for case_id, mod_id, reason, ts in warns:
        dt = datetime.fromtimestamp(ts, UTC).strftime("%Y-%m-%d")
        lines += f"{RED}[#{case_id}]{RST} {dt} | <@{mod_id}> | {reason[:40]}\n"
    embed = cmd_embed(f"WARNINGS // {member.name.upper()}", lines, colour=0xFF4444)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="clearwarns", description="Clear all warnings for a member")
@app_commands.guild_only()
@app_commands.default_permissions(manage_channels=True)
@app_commands.describe(member="Member to clear warnings for")
async def clearwarns(interaction: discord.Interaction, member: discord.Member) -> None:
    if not interaction.user.guild_permissions.manage_channels:
        return await interaction.response.send_message("Manage Channels required.", ephemeral=True)
    count = await bot.database.clear_warnings(interaction.guild.id, member.id)
    await bot._log(interaction.guild.id, "Clear Warnings", user_id=interaction.user.id, target_id=member.id, details=f"Cleared {count} warnings")
    await interaction.response.send_message(f"🗑️ Cleared {count} warnings for {member.mention}.", ephemeral=True)


@bot.tree.command(name="kick", description="Kick a member from the server")
@app_commands.guild_only()
@app_commands.default_permissions(kick_members=True)
@app_commands.describe(member="Member to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided") -> None:
    if not interaction.user.guild_permissions.kick_members:
        return await interaction.response.send_message("Kick Members required.", ephemeral=True)
    await member.kick(reason=f"{interaction.user}: {reason}")
    await bot._log(interaction.guild.id, "Kick", user_id=interaction.user.id, target_id=member.id, reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention}: {reason}", ephemeral=True)


@bot.tree.command(name="ban", description="Ban a member from the server")
@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(member="Member to ban", reason="Reason for ban", delete_days="Days of messages to delete (0-7)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided", delete_days: app_commands.Range[int, 0, 7] = 0) -> None:
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("Ban Members required.", ephemeral=True)
    await member.ban(reason=f"{interaction.user}: {reason}", delete_message_days=delete_days)
    await bot.database.add_ban(interaction.guild.id, member.id, interaction.user.id, reason, time.time())
    await bot._log(interaction.guild.id, "Ban", user_id=interaction.user.id, target_id=member.id, reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.mention}: {reason}", ephemeral=True)


@bot.tree.command(name="unban", description="Unban a user")
@app_commands.guild_only()
@app_commands.default_permissions(ban_members=True)
@app_commands.describe(user_id="User ID to unban", reason="Reason for unban")
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided") -> None:
    if not interaction.user.guild_permissions.ban_members:
        return await interaction.response.send_message("Ban Members required.", ephemeral=True)
    try:
        uid = int(user_id)
        user = discord.Object(id=uid)
        await interaction.guild.unban(user, reason=f"{interaction.user}: {reason}")
        await bot.database.remove_ban(interaction.guild.id, uid)
        await bot._log(interaction.guild.id, "Unban", user_id=interaction.user.id, target_id=uid, reason=reason)
        await interaction.response.send_message(f"🔓 Unbanned <@{uid}>.", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("Invalid user ID.", ephemeral=True)


@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.guild_only()
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(member="Member to timeout", duration="Duration (e.g. 1h, 30m, 1d)", reason="Reason")
async def timeout_cmd(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason provided") -> None:
    if not interaction.user.guild_permissions.moderate_members:
        return await interaction.response.send_message("Moderate Members required.", ephemeral=True)

    # Parse duration
    match = re.match(r"^(\d+)([mhd])$", duration.lower())
    if not match:
        return await interaction.response.send_message("Invalid duration format. Use: 30m, 1h, 1d", ephemeral=True)

    value, unit = int(match.group(1)), match.group(2)
    delta = timedelta(minutes=value) if unit == "m" else timedelta(hours=value) if unit == "h" else timedelta(days=value)
    until = datetime.now(UTC) + delta

    await member.timeout(until, reason=f"{interaction.user}: {reason}")
    await bot.database.add_timeout(interaction.guild.id, member.id, interaction.user.id, reason, until.timestamp(), time.time())
    await bot._log(interaction.guild.id, "Timeout", user_id=interaction.user.id, target_id=member.id, reason=reason, details=f"Duration: {duration}")
    await interaction.response.send_message(f"⏱️ Timed out {member.mention} for {duration}: {reason}", ephemeral=True)


@bot.tree.command(name="purge", description="Delete a large number of messages")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(amount="Number of messages (1-1000)", member="Only delete messages from this member")
async def purge(interaction: discord.Interaction, amount: app_commands.Range[int, 1, 1000], member: discord.Member = None) -> None:
    if not interaction.user.guild_permissions.manage_messages or not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("Manage Messages required.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)

    def check(m: discord.Message):
        if member:
            return m.author.id == member.id
        return True

    deleted = await interaction.channel.purge(limit=amount, check=check)
    await bot._log(interaction.guild.id, "Purge", user_id=interaction.user.id, details=f"Deleted {len(deleted)} messages in #{interaction.channel.name}")
    await interaction.followup.send(f"🗑️ Deleted {len(deleted)} messages.", ephemeral=True)


# ── ECONOMY COMMANDS ──

@bot.tree.command(name="balance", description="Check your economy balance")
@app_commands.guild_only()
async def balance(interaction: discord.Interaction, member: discord.Member = None) -> None:
    target = member or interaction.user
    wallet, bank, _ = await bot.database.get_balance(interaction.guild.id, target.id)
    embed = hx_embed("ECONOMY // BALANCE",
        f"{CYN}[USER]{RST}   {target.mention}\n"
        f"{GRN}[WALLET]{RST} {wallet:,} credits\n"
        f"{BLU}[BANK]{RST}   {bank:,} credits\n"
        f"{YLW}[TOTAL]{RST}  {wallet + bank:,} credits",
        colour=0x00FF41,
        member=target,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="daily", description="Claim your daily reward")
@app_commands.guild_only()
async def daily(interaction: discord.Interaction) -> None:
    wallet, bank, last_daily = await bot.database.get_balance(interaction.guild.id, interaction.user.id)
    now = time.time()
    if now - last_daily < 86400:
        remaining = int(86400 - (now - last_daily))
        hours, remainder = divmod(remaining, 3600)
        minutes, _ = divmod(remainder, 60)
        return await interaction.response.send_message(f"⏳ Come back in {hours}h {minutes}m.", ephemeral=True)

    reward = random.randint(100, 500)
    wallet += reward
    await bot.database.set_balance(interaction.guild.id, interaction.user.id, wallet, bank, now)
    embed = hx_embed("DAILY REWARD",
        f"{GRN}[SUCCESS]{RST}  Claimed **{reward:,}** credits!\n"
        f"{CYN}[BALANCE]{RST} {wallet:,} credits",
        colour=0xFFD700,
        member=interaction.user,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="pay", description="Pay credits to another member")
@app_commands.guild_only()
@app_commands.describe(member="Member to pay", amount="Amount to pay")
async def pay(interaction: discord.Interaction, member: discord.Member, amount: int) -> None:
    if amount <= 0:
        return await interaction.response.send_message("Amount must be positive.", ephemeral=True)
    if member.id == interaction.user.id:
        return await interaction.response.send_message("You can't pay yourself.", ephemeral=True)

    wallet, bank, _ = await bot.database.get_balance(interaction.guild.id, interaction.user.id)
    if wallet < amount:
        return await interaction.response.send_message("Insufficient funds.", ephemeral=True)

    target_wallet, target_bank, _ = await bot.database.get_balance(interaction.guild.id, member.id)
    wallet -= amount
    target_wallet += amount
    await bot.database.set_balance(interaction.guild.id, interaction.user.id, wallet, bank, 0)
    await bot.database.set_balance(interaction.guild.id, member.id, target_wallet, target_bank, 0)

    await interaction.response.send_message(f"💸 Paid {member.mention} **{amount:,}** credits.", ephemeral=True)


@bot.tree.command(name="work", description="Work to earn credits")
@app_commands.guild_only()
async def work(interaction: discord.Interaction) -> None:
    jobs = ["Hacker", "Engineer", "Pilot", "Spy", "Merchant", "Scientist"]
    job = random.choice(jobs)
    earnings = random.randint(10, 100)
    wallet, bank, _ = await bot.database.get_balance(interaction.guild.id, interaction.user.id)
    wallet += earnings
    await bot.database.set_balance(interaction.guild.id, interaction.user.id, wallet, bank, 0)
    embed = hx_embed("WORK COMPLETE",
        f"{GRN}[JOB]{RST}     {job}\n"
        f"{GRN}[PAY]{RST}     {earnings:,} credits\n"
        f"{CYN}[BALANCE]{RST} {wallet:,} credits",
        colour=0x00FF41,
        member=interaction.user,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── LEVELING COMMANDS ──

@bot.tree.command(name="rank", description="Check your level and XP")
@app_commands.guild_only()
async def rank(interaction: discord.Interaction, member: discord.Member = None) -> None:
    target = member or interaction.user
    xp, level, msgs, vmins = await bot.database.get_level(interaction.guild.id, target.id)
    next_level_xp = (level + 1) * 100
    pct = int((xp / next_level_xp) * 100)
    bar = _bar(pct)

    embed = hx_embed("RANK // PROFILE",
        f"{CYN}[USER]{RST}   {target.mention}\n"
        f"{YLW}[LEVEL]{RST}  {level}\n"
        f"{GRN}[XP]{RST}     {xp}/{next_level_xp}\n"
        f"{bar}\n"
        f"{CYN}[MESSAGES]{RST} {msgs:,}\n"
        f"{CYN}[VOICE]{RST}   {vmins} min",
        colour=0x7C3AED,
        member=target,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="View the top members by level")
@app_commands.guild_only()
async def leaderboard(interaction: discord.Interaction) -> None:
    top = await bot.database.leveling_top(interaction.guild.id, 10)
    if not top:
        return await interaction.response.send_message("No data yet.", ephemeral=True)
    lines = ""
    for i, (uid, xp, level) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lines += f"{medal} <@{uid}> — Lvl {level} ({xp:,} XP)\n"
    embed = cmd_embed("🏆 LEADERBOARD // TOP 10", lines, colour=0xFFD700)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="economyboard", description="View the top members by wealth")
@app_commands.guild_only()
async def economyboard(interaction: discord.Interaction) -> None:
    top = await bot.database.economy_top(interaction.guild.id, 10)
    if not top:
        return await interaction.response.send_message("No data yet.", ephemeral=True)
    lines = ""
    for i, (uid, total) in enumerate(top, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lines += f"{medal} <@{uid}> — {total:,} credits\n"
    embed = cmd_embed("💰 ECONOMY LEADERBOARD // TOP 10", lines, colour=0x00FF41)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ── POLL COMMANDS ──

@bot.tree.command(name="poll", description="Create a poll")
@app_commands.guild_only()
@app_commands.describe(question="Poll question", option1="Option 1", option2="Option 2", option3="Option 3", option4="Option 4")
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None) -> None:
    options = [o for o in [option1, option2, option3, option4] if o]
    if len(options) < 2:
        return await interaction.response.send_message("Need at least 2 options.", ephemeral=True)

    embed = discord.Embed(title=f"📊 {question}", colour=0x5865F2)
    for i, opt in enumerate(options, 1):
        embed.add_field(name=f"Option {i}", value=f"{['1️⃣','2️⃣','3️⃣','4️⃣'][i-1]} {opt}", inline=False)
    embed.set_footer(text=f"Poll by {interaction.user.display_name}")

    msg = await interaction.channel.send(embed=embed)
    for i in range(len(options)):
        await msg.add_reaction(['1️⃣','2️⃣','3️⃣','4️⃣'][i])

    await bot.database.create_poll(interaction.guild.id, msg.id, interaction.channel.id, interaction.user.id, question, json.dumps(options))
    await interaction.response.send_message("Poll created.", ephemeral=True)


# ── SUGGESTION COMMANDS ──

@bot.tree.command(name="suggest", description="Submit a suggestion")
@app_commands.guild_only()
@app_commands.describe(content="Your suggestion")
async def suggest(interaction: discord.Interaction, content: str) -> None:
    sid = await bot.database.add_suggestion(interaction.guild.id, interaction.user.id, content, time.time())
    embed = hx_embed(f"SUGGESTION #{sid}",
        f"{CYN}[AUTHOR]{RST} {interaction.user.mention}\n"
        f"{CYN}[STATUS]{RST} Pending Review\n\n"
        f"{WHT}{content}{RST}",
        colour=0x5865F2,
        member=interaction.user,
    )
    sug_ch = discord.utils.get(interaction.guild.text_channels, name="💡-suggestions")
    if sug_ch:
        msg = await sug_ch.send(embed=embed, view=SuggestionVoteView(bot.database, sid))
    await interaction.response.send_message(f"💡 Suggestion #{sid} submitted.", ephemeral=True)


# ── ADMIN COMMANDS ──

@bot.tree.command(name="say", description="Make the bot say something")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(channel="Channel to send in", text="Text to send")
async def say(interaction: discord.Interaction, channel: discord.TextChannel, text: str) -> None:
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Manage Messages required.", ephemeral=True)
    await channel.send(text)
    await interaction.response.send_message("Sent.", ephemeral=True)


@bot.tree.command(name="embed", description="Send an embed")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(channel="Channel to send in", title="Embed title", description="Embed description", color="Hex color (e.g. FF0000)")
async def embed_cmd(interaction: discord.Interaction, channel: discord.TextChannel, title: str, description: str, color: str = "5865F2") -> None:
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Manage Messages required.", ephemeral=True)
    try:
        colour = int(color.replace("#", ""), 16)
    except ValueError:
        colour = 0x5865F2
    embed = discord.Embed(title=title, description=description, colour=colour)
    await channel.send(embed=embed)
    await interaction.response.send_message("Embed sent.", ephemeral=True)


# ── FUN COMMANDS ──

@bot.tree.command(name="8ball", description="Ask the magic 8-ball")
@app_commands.guild_only()
@app_commands.describe(question="Your question")
async def eightball(interaction: discord.Interaction, question: str) -> None:
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.", "Yes definitely.",
        "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
        "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
        "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
        "Don't count on it.", "My reply is no.", "My sources say no.",
        "Outlook not so good.", "Very doubtful."
    ]
    embed = discord.Embed(title="🎱 Magic 8-Ball", colour=0x7C3AED)
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="coinflip", description="Flip a coin")
@app_commands.guild_only()
async def coinflip(interaction: discord.Interaction) -> None:
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "💿"
    await interaction.response.send_message(f"{emoji} **{result}**!")


# ── EXISTING + UPDATED COMMANDS ──

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


@bot.tree.command(name="status", description="Show the bot's current operational status.")
async def status(interaction: discord.Interaction) -> None:
    ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    embed = cmd_embed(
        "NEXUS STATUS",
        f"{GRN}[OK]{RST}   Latency: `{round(bot.latency * 1000)} ms`\n"
        f"{GRN}[OK]{RST}   Database: `online`\n"
        f"{GRN}[OK]{RST}   Persistent controls: `armed`\n"
        f"{CYN}[TIME]{RST}  {ts}\n"
        f"{CYN}[INFO]{RST}  Sectors: 9  |  Roles: 10  |  Nodes: 3",
        colour=0x22D3EE,
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="verify", description="Instantly verify a member (Admin/Mod only)")
@app_commands.guild_only()
@app_commands.default_permissions(manage_messages=True)
@app_commands.describe(member="Member to verify instantly")
async def verify_member(interaction: discord.Interaction, member: discord.Member) -> None:
    if not interaction.user.guild_permissions.manage_messages:
        return await interaction.response.send_message("Manage Messages permission required.", ephemeral=True)
    role = discord.utils.get(interaction.guild.roles, name="Verified")
    if not role:
        return await interaction.response.send_message("Verified role not found. Run /setup first.", ephemeral=True)
    if role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
        return await interaction.response.send_message("Move my role above Verified first.", ephemeral=True)
    await member.add_roles(role, reason=f"Instant verify by {interaction.user}")
    await bot.database.set_verification_status(interaction.guild.id, member.id, "approved")
    await bot.database.set_member_stage(interaction.guild.id, member.id, "verified")
    arrival = discord.utils.get(interaction.guild.text_channels, name="⌁-arrival-terminal")
    if arrival:
        ts = datetime.now(UTC).strftime("%H:%M:%S UTC")
        tx_embed = cmd_embed(
            "ACCESS GRANTED // MANUAL OVERRIDE",
            f"{GRN}[SUCCESS]{RST}  Identity verified for {member.mention}\n"
            f"{CYN}[CLEARANCE]{RST} LEVEL 1 — VERIFIED\n"
            f"{CYN}[BY]{RST}      Approved by {interaction.user.mention}\n"
            f"{DIM}[TIME]{RST}    {ts}",
            colour=0x00FF41,
        )
        tx_embed.set_thumbnail(url=member.display_avatar.url)
        await arrival.send(content=member.mention, embed=tx_embed, view=StageTransitionView(bot.database))
    await interaction.response.send_message(f"✅ {member.mention} has been verified instantly.", ephemeral=True)


@bot.tree.command(name="reactionrole", description="Create a reaction role (Admin only)")
@app_commands.guild_only()
@app_commands.default_permissions(manage_roles=True)
async def reactionrole(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_roles:
        return await interaction.response.send_message("Manage Roles required.", ephemeral=True)
    await interaction.response.send_message("Use the panel in 🎭-reaction-roles or use the modal below:", view=discord.ui.View(), ephemeral=True)


@bot.tree.command(name="automod", description="Configure AutoMod settings")
@app_commands.guild_only()
@app_commands.default_permissions(manage_guild=True)
async def automod(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.manage_guild:
        return await interaction.response.send_message("Manage Server required.", ephemeral=True)
    config = await bot.database.get_automod(interaction.guild.id)
    status = lambda x: f"{GRN}ON{RST}" if x else f"{RED}OFF{RST}"
    lines = (
        f"{CYN}[01]{RST} Anti-Spam:    {status(config[1] if config else 0)}\n"
        f"{CYN}[02]{RST} Anti-Link:    {status(config[2] if config else 0)}\n"
        f"{CYN}[03]{RST} Anti-Caps:    {status(config[3] if config else 0)}\n"
        f"{DIM}Use the buttons below to toggle.{RST}"
    )
    embed = cmd_embed("AUTOMOD CONFIG", lines, colour=0xFF4444)
    await interaction.response.send_message(embed=embed, view=AutoModConfigView(bot.database), ephemeral=True)


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


# ── PREFIX COMMANDS ──

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


@bot.command(name="verify")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def prefix_verify(ctx: commands.Context, member: discord.Member) -> None:
    role = discord.utils.get(ctx.guild.roles, name="Verified")
    if not role:
        return await ctx.reply("Run /setup first.", mention_author=False)
    if role >= ctx.guild.me.top_role:
        return await ctx.reply("Move my role above Verified first.", mention_author=False)
    await member.add_roles(role, reason=f"Manual verify by {ctx.author}")
    await bot.database.set_verification_status(ctx.guild.id, member.id, "approved")
    await bot.database.set_member_stage(ctx.guild.id, member.id, "verified")
    arrival = discord.utils.get(ctx.guild.text_channels, name="⌁-arrival-terminal")
    if arrival:
        ts = datetime.now(UTC).strftime("%H:%M:%S UTC")
        tx_embed = cmd_embed(
            "ACCESS GRANTED // MANUAL OVERRIDE",
            f"{GRN}[SUCCESS]{RST}  Identity verified for {member.mention}\n"
            f"{CYN}[CLEARANCE]{RST} LEVEL 1 — VERIFIED\n"
            f"{CYN}[BY]{RST}      Approved by {ctx.author.mention}\n"
            f"{DIM}[TIME]{RST}    {ts}",
            colour=0x00FF41,
        )
        tx_embed.set_thumbnail(url=member.display_avatar.url)
        await arrival.send(content=member.mention, embed=tx_embed, view=StageTransitionView(bot.database))
    await ctx.reply(f"✅ Verified {member.mention}", mention_author=False)


@bot.command(name="warn")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def prefix_warn(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason") -> None:
    case_id = await bot.database.add_warning(ctx.guild.id, member.id, ctx.author.id, reason, time.time())
    await bot._log(ctx.guild.id, "Warn", user_id=ctx.author.id, target_id=member.id, reason=reason, details=f"Case #{case_id}")
    try:
        embed = hx_embed("WARNING ISSUED",
            f"{YLW}[WARN]{RST}  You received a warning in **{ctx.guild.name}**\n"
            f"{CYN}[REASON]{RST} {reason}\n"
            f"{CYN}[CASE]{RST}   #{case_id}",
            colour=0xFF4444)
        await member.send(embed=embed)
    except discord.Forbidden:
        pass
    await ctx.reply(f"⚠️ Warned {member.mention} (Case #{case_id})", mention_author=False)


@bot.command(name="kick")
@commands.guild_only()
@commands.has_permissions(kick_members=True)
async def prefix_kick(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason") -> None:
    await member.kick(reason=f"{ctx.author}: {reason}")
    await bot._log(ctx.guild.id, "Kick", user_id=ctx.author.id, target_id=member.id, reason=reason)
    await ctx.reply(f"👢 Kicked {member.mention}", mention_author=False)


@bot.command(name="ban")
@commands.guild_only()
@commands.has_permissions(ban_members=True)
async def prefix_ban(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason") -> None:
    await member.ban(reason=f"{ctx.author}: {reason}")
    await bot.database.add_ban(ctx.guild.id, member.id, ctx.author.id, reason, time.time())
    await bot._log(ctx.guild.id, "Ban", user_id=ctx.author.id, target_id=member.id, reason=reason)
    await ctx.reply(f"🔨 Banned {member.mention}", mention_author=False)


@bot.command(name="purge")
@commands.guild_only()
@commands.has_permissions(manage_messages=True)
async def prefix_purge(ctx: commands.Context, amount: int = 10) -> None:
    amount = max(1, min(1000, amount))
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🗑️ Purged {len(deleted) - 1} messages.", delete_after=4)


@prefix_setup.error
@prefix_clear.error
@prefix_verify.error
@prefix_warn.error
@prefix_kick.error
@prefix_ban.error
@prefix_purge.error
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
