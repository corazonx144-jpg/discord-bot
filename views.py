from __future__ import annotations

import asyncio
import hashlib
import re
from contextlib import suppress
from datetime import UTC, datetime

import discord

from database import Database
from layout import SERVICES_CATEGORY, is_self_assignable


# ============================================================
# ANSI colour codes
# ============================================================

BLK = "\u001b[0;30m"
RED = "\u001b[1;31m"
GRN = "\u001b[1;32m"
YLW = "\u001b[1;33m"
BLU = "\u001b[1;34m"
MAG = "\u001b[1;35m"
CYN = "\u001b[1;36m"
WHT = "\u001b[1;37m"
RST = "\u001b[0m"
DIM = "\u001b[2m"

ACCENT = 0x00FF41


# ============================================================
# HELPERS
# ============================================================

def _hash_id(uid: int) -> str:
    return hashlib.sha256(str(uid).encode()).hexdigest()[:16].upper()


def _bar(pct: int, width: int = 20) -> str:
    pct = max(0, min(100, pct))
    filled = int(width * pct / 100)
    return f"{GRN}{chr(9608) * filled}{BLK}{chr(9617) * (width - filled)}{RST}"


def hx_embed(
    header: str,
    lines: str,
    colour: int = 0x00FF41,
    member: discord.Member | None = None,
) -> discord.Embed:
    frame = (
        f"{CYN}╔══════════════════════════════════════════════════════════════╗{RST}\n"
        f"{CYN}║{RST}  {WHT}{header:^56}{RST}  {CYN}║{RST}\n"
        f"{CYN}╠══════════════════════════════════════════════════════════════╣{RST}\n"
        f"{lines}\n"
        f"{CYN}╚══════════════════════════════════════════════════════════════╝{RST}"
    )

    embed = discord.Embed(
        description=f"```ansi\n{frame}\n```",
        colour=colour,
    )

    embed.set_footer(text="root@nexus:~$ ▮")

    if member:
        embed.set_thumbnail(url=member.display_avatar.url)

    return embed


REVIEWER_ROLES = {"Admin", "Moderator"}
SUPPORT_ROLES = {"Admin", "Moderator", "Support Team"}


def _has_role(member: discord.Member, names: set[str]) -> bool:
    return any(role.name in names for role in member.roles)


def can_review(member: discord.Member) -> bool:
    perms = member.guild_permissions
    return (
        perms.administrator
        or perms.manage_roles
        or _has_role(member, REVIEWER_ROLES)
    )


def _arrival(guild: discord.Guild) -> discord.TextChannel | None:
    return discord.utils.get(guild.text_channels, name="⌁-arrival-terminal")


# ============================================================
# STAGE TRANSITION
# ============================================================

class StageTransitionView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label=">> PROCEED TO NEXT SECTOR",
        emoji="🚀",
        style=discord.ButtonStyle.success,
        custom_id="nexus:stage:proceed",
    )
    async def proceed(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        if not guild or not isinstance(user, discord.Member):
            return

        stage = await self.database.get_member_stage(guild.id, user.id)
        verified = discord.utils.get(guild.roles, name="Verified")

        # manual role grants never set a stage, so trust the role too
        if verified in user.roles and stage in (None, "arrival", "pending_verify"):
            stage = "verified"

        if stage == "verified":
            embed = hx_embed(
                "SECTOR 01 // CLEARANCE GATE",
                f"{GRN}[AUTH]{RST}   Identity verified for {user.mention}\n"
                f"{CYN}[CMD]{RST}    Select operational clearance below\n\n"
                f"{WHT}  [1] {YLW}⚡ Elite Agent{WHT}  — Full system access{RST}\n"
                f"{WHT}  [2] {DIM}👤 Guest Node{WHT}   — Limited read-only{RST}\n"
                f"{WHT}  [3] {GRN}🛡️ Support Team{WHT} — Ticket management{RST}\n"
                f"{WHT}  [4] {BLU}💻 Developer{WHT}    — Code & bot dev{RST}\n"
                f"{WHT}  [5] {YLW}🔨 Moderator{WHT}    — Kick, mute, warn{RST}\n"
                f"{WHT}  [6] {MAG}👑 VIP{WHT}          — Premium lounge{RST}\n"
                f"{WHT}  [7] {RED}📺 Streamer{WHT}     — Content creator{RST}\n"
                f"{WHT}  [8] {CYN}🎨 Artist{WHT}       — Visual gallery{RST}\n"
                f"{WHT}  [9] {MAG}🎵 Musician{WHT}     — Music lab{RST}",
                colour=0x7C3AED,
                member=user,
            )

            return await interaction.response.send_message(
                embed=embed,
                view=RoleView(self.database),
                ephemeral=True,
            )

        if stage == "cleared":
            embed = hx_embed(
                "SECTOR 02 // TERMINAL CHAT",
                f"{GRN}[AUTH]{RST}   Clearance level confirmed\n"
                f"{CYN}[NET]{RST}    Operational channels unlocked\n"
                f"{YLW}[NOTE]{RST}   Use /status for system diagnostics\n"
                f"{GRN}[WELCOME]{RST} {user.mention} — you are cleared for all sectors.",
                colour=0x00FF41,
                member=user,
            )

            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True,
            )

        await interaction.response.send_message(
            f"{RED}[ERR]{RST}  Verification is not complete yet. "
            f"Current stage: `{stage or 'unknown'}`",
            ephemeral=True,
        )


# ============================================================
# VERIFICATION
# ============================================================

class VerificationView(discord.ui.View):
    def __init__(self, guild_id: int = 0, target_id: int = 0) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.target_id = target_id

    @discord.ui.button(
        label="INITIATE VERIFY.EXE",
        emoji="🛡️",
        style=discord.ButtonStyle.success,
        custom_id="nexus:verify",
    )
    async def verify(
        self,
        interaction: discord.Interaction,
        _: discord.ui.Button,
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        if not guild or not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Server only.", ephemeral=True
            )

        # A welcome message mentions its member. Checking the mention
        # keeps working after a restart (target_id would be lost).
        message = interaction.message

        if message and message.mentions and user not in message.mentions:
            return await interaction.response.send_message(
                f"{RED}[ERR]{RST}  This scan session is not assigned to your identity.",
                ephemeral=True,
            )

        db = getattr(interaction.client, "database", None)

        if db is None:
            return await interaction.response.send_message(
                "Database offline.", ephemeral=True
            )

        queue = discord.utils.get(
            guild.text_channels, name="🔐-approval-queue"
        )

        if queue is None:
            return await interaction.response.send_message(
                "Run /setup first.", ephemeral=True
            )

        verified = discord.utils.get(guild.roles, name="Verified")

        if verified in user.roles:
            return await interaction.response.send_message(
                "Already verified.", ephemeral=True
            )

        status = await db.verification_status(guild.id, user.id)

        if status == "pending":
            return await interaction.response.send_message(
                "Request already queued.", ephemeral=True
            )

        await db.set_verification_status(guild.id, user.id, "pending")
        await db.set_member_stage(guild.id, user.id, "pending_verify")

        proc = hx_embed(
            "VERIFY.EXE // EXECUTING",
            f"{CYN}[TX]{RST}     Encrypting payload...\n"
            f"{CYN}[ROUTE]{RST}  Administration Queue\n"
            f"{GRN}[STATUS]{RST} Awaiting manual review...",
            colour=0x7C3AED,
            member=user,
        )

        await interaction.response.send_message(embed=proc, ephemeral=True)

        req_embed = hx_embed(
            "ACCESS REQUEST // TX",
            f"{CYN}[MEMBER]{RST} {user.mention}\n"
            f"{CYN}[NAME]{RST}   {user.display_name}\n"
            f"{CYN}[UID]{RST}    `{user.id}`\n"
            f"{CYN}[HASH]{RST}   {_hash_id(user.id)}\n"
            f"{GRN}[STATUS]{RST} PENDING REVIEW",
            colour=0x7C3AED,
            member=user,
        )

        req_embed.set_footer(text=f"member:{user.id}")

        await queue.send(embed=req_embed, view=ApprovalView(db))

        pings = [
            role.mention
            for role in (
                discord.utils.get(guild.roles, name="Admin"),
                discord.utils.get(guild.roles, name="Moderator"),
            )
            if role
        ]

        if pings:
            await queue.send(" ".join(pings), delete_after=3600)

        if guild.owner:
            with suppress(discord.Forbidden, discord.HTTPException):
                await guild.owner.send(
                    f"New access request in **{guild.name}** from "
                    f"{user} (`{user.id}`)."
                )


# ============================================================
# APPROVAL QUEUE
# ============================================================

class ApprovalView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    async def decide(
        self,
        interaction: discord.Interaction,
        approved: bool,
    ) -> None:
        guild = interaction.guild
        user = interaction.user
        message = interaction.message

        if (
            not guild
            or not isinstance(user, discord.Member)
            or not message
            or not message.embeds
            or not can_review(user)
        ):
            return await interaction.response.send_message(
                "Staff permission required.", ephemeral=True
            )

        footer = message.embeds[0].footer.text or ""
        arrival = _arrival(guild)
        now = datetime.now(UTC).strftime("%H:%M:%S")

        # ---- validate before touching anything ----------------------

        if footer.startswith("clearance:"):
            _, raw_id, role_name = footer.split(":", 2)
            kind = "clearance"
        elif footer.startswith("member:"):
            raw_id = footer.split(":", 1)[1]
            role_name = "Verified"
            kind = "verify"
        else:
            return await interaction.response.send_message(
                "Invalid approval record.", ephemeral=True
            )

        member_id = int(raw_id)
        member = guild.get_member(member_id)
        role = discord.utils.get(guild.roles, name=role_name)

        if approved:
            if kind == "clearance" and role_name == "Moderator":
                if not user.guild_permissions.administrator:
                    return await interaction.response.send_message(
                        "Only an Administrator can approve a Moderator.",
                        ephemeral=True,
                    )

            if member is None or role is None:
                return await interaction.response.send_message(
                    "The member or the role no longer exists. "
                    "Reject this request instead.",
                    ephemeral=True,
                )

            if role >= guild.me.top_role:
                return await interaction.response.send_message(
                    f"Move my role above **{role_name}** first.",
                    ephemeral=True,
                )

        await interaction.response.defer()

        # ---- apply ---------------------------------------------------

        if approved:
            try:
                await member.add_roles(
                    role, reason=f"{kind} approved by {user}"
                )
            except (discord.Forbidden, discord.HTTPException):
                return await interaction.followup.send(
                    "I could not assign that role (check my permissions).",
                    ephemeral=True,
                )

            if kind == "verify":
                await self.database.set_member_stage(guild.id, member_id, "verified")
                header = "ACCESS GRANTED // PROTOCOL COMPLETE"
                body = (
                    f"{GRN}[SUCCESS]{RST}  Identity verified for {member.mention}\n"
                    f"{CYN}[CLEARANCE]{RST} LEVEL 1 — VERIFIED\n"
                    f"{CYN}[NEXT]{RST}    Proceed to Clearance Gate (Sector 01)\n"
                    f"{DIM}[TIME]{RST}    {now} UTC"
                )
                colour = 0x00FF41
            else:
                await self.database.set_member_stage(guild.id, member_id, "cleared")
                header = "CLEARANCE UPGRADED // SECTOR 02 READY"
                body = (
                    f"{GRN}[SUCCESS]{RST}  {role_name} granted to {member.mention}\n"
                    f"{CYN}[NEXT]{RST}    Enter Terminal Chat & Secure Nodes\n"
                    f"{DIM}[TIME]{RST}    {now} UTC"
                )
                colour = 0xFFD700

            if arrival:
                await arrival.send(
                    content=member.mention,
                    embed=hx_embed(header, body, colour=colour, member=member),
                    view=StageTransitionView(self.database),
                )

        status = "approved" if approved else "rejected"

        if kind == "verify":
            await self.database.set_verification_status(guild.id, member_id, status)
            if not approved:
                await self.database.set_member_stage(guild.id, member_id, "arrival")
        else:
            await self.database.set_clearance_status(
                guild.id, member_id, role_name, status
            )

        embed = message.embeds[0]
        embed.colour = (
            discord.Colour.green() if approved else discord.Colour.red()
        )
        embed.title = f"ACCESS {status.upper()}"
        embed.add_field(name="Reviewed by", value=user.mention, inline=False)

        await interaction.edit_original_response(embed=embed, view=None)

    @discord.ui.button(
        label="APPROVE",
        emoji="✅",
        style=discord.ButtonStyle.success,
        custom_id="nexus:verify:approve",
    )
    async def approve(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await self.decide(interaction, True)

    @discord.ui.button(
        label="REJECT",
        emoji="⛔",
        style=discord.ButtonStyle.danger,
        custom_id="nexus:verify:reject",
    )
    async def reject(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await self.decide(interaction, False)


# ============================================================
# CLEARANCE ROLE REQUESTS
# ============================================================

class RoleView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    async def _request(
        self,
        interaction: discord.Interaction,
        role_name: str,
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        if not guild or not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Server only.", ephemeral=True
            )

        verified = discord.utils.get(guild.roles, name="Verified")

        if verified is None or verified not in user.roles:
            return await interaction.response.send_message(
                "Verification required first.", ephemeral=True
            )

        role = discord.utils.get(guild.roles, name=role_name)
        queue = discord.utils.get(guild.text_channels, name="🔐-approval-queue")

        if role is None or queue is None:
            return await interaction.response.send_message(
                "Run /setup first.", ephemeral=True
            )

        if role in user.roles:
            return await interaction.response.send_message(
                "You already hold this clearance.", ephemeral=True
            )

        previous = await self.database.clearance_status(guild.id, user.id)

        if previous and previous[1] == "pending":
            return await interaction.response.send_message(
                f"Your {previous[0]} request is awaiting review.",
                ephemeral=True,
            )

        await self.database.set_clearance_status(
            guild.id, user.id, role_name, "pending"
        )

        req_embed = hx_embed(
            "CLEARANCE REQUEST // TX",
            f"{CYN}[MEMBER]{RST} {user.mention}\n"
            f"{CYN}[NAME]{RST}   {user.display_name}\n"
            f"{YLW}[REQ]{RST}    {role_name}\n"
            f"{CYN}[UID]{RST}    `{user.id}`\n"
            f"{CYN}[HASH]{RST}   {_hash_id(user.id)}\n"
            f"{GRN}[STATUS]{RST} PENDING REVIEW",
            colour=0x7C3AED,
            member=user,
        )

        req_embed.set_footer(text=f"clearance:{user.id}:{role_name}")

        await queue.send(embed=req_embed, view=ApprovalView(self.database))

        await interaction.response.send_message(
            f"{GRN}[OK]{RST}  {role_name} clearance request submitted.",
            ephemeral=True,
        )

    @discord.ui.button(label="Elite Agent", emoji="⚡", style=discord.ButtonStyle.primary, custom_id="nexus:role:elite")
    async def elite(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Elite Agent")

    @discord.ui.button(label="Guest Node", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="nexus:role:guest")
    async def guest(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Guest Node")

    @discord.ui.button(label="Support Team", emoji="🛡️", style=discord.ButtonStyle.success, custom_id="nexus:role:support")
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Support Team")

    @discord.ui.button(label="Developer", emoji="💻", style=discord.ButtonStyle.primary, custom_id="nexus:role:dev")
    async def developer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Developer")

    @discord.ui.button(label="Moderator", emoji="🔨", style=discord.ButtonStyle.danger, custom_id="nexus:role:mod")
    async def moderator(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Moderator")

    @discord.ui.button(label="VIP", emoji="👑", style=discord.ButtonStyle.primary, row=1, custom_id="nexus:role:vip")
    async def vip(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "VIP")

    @discord.ui.button(label="Streamer", emoji="📺", style=discord.ButtonStyle.secondary, row=1, custom_id="nexus:role:streamer")
    async def streamer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Streamer")

    @discord.ui.button(label="Artist", emoji="🎨", style=discord.ButtonStyle.primary, row=1, custom_id="nexus:role:artist")
    async def artist(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Artist")

    @discord.ui.button(label="Musician", emoji="🎵", style=discord.ButtonStyle.secondary, row=1, custom_id="nexus:role:musician")
    async def musician(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._request(interaction, "Musician")


# ============================================================
# TEMPORARY VOICE ROOMS
# ============================================================

class RoomPanelView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="Create voice room",
        emoji="🎛️",
        style=discord.ButtonStyle.primary,
        custom_id="nexus:room:begin",
    )
    async def begin(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        await interaction.response.send_modal(RoomModal(self.database))


class RoomModal(discord.ui.Modal, title="Configure your temporary room"):
    room_name = discord.ui.TextInput(
        label="Room name",
        placeholder="e.g. Night Ops",
        max_length=40,
    )

    minutes = discord.ui.TextInput(
        label="Duration in minutes (5–720)",
        placeholder="60",
        default="60",
        max_length=3,
    )

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            duration = max(5, min(720, int(str(self.minutes))))
        except ValueError:
            return await interaction.response.send_message(
                "Duration must be a number from 5 to 720.", ephemeral=True
            )

        await interaction.response.send_message(
            "Choose the room privacy:",
            view=RoomPrivacyView(self.database, str(self.room_name), duration),
            ephemeral=True,
        )


class RoomPrivacyView(discord.ui.View):
    def __init__(self, database: Database, name: str, minutes: int) -> None:
        super().__init__(timeout=120)
        self.database = database
        self.name = name
        self.minutes = minutes

    async def create(
        self, interaction: discord.Interaction, private: bool
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        if not guild or not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Server only.", ephemeral=True
            )

        category = discord.utils.get(guild.categories, name=SERVICES_CATEGORY)
        verified = discord.utils.get(guild.roles, name="Verified")

        if category is None or verified is None:
            return await interaction.response.send_message(
                "Run /setup first.", ephemeral=True
            )

        # one live room per member
        for channel_id in await self.database.owner_rooms(guild.id, user.id):
            if guild.get_channel(channel_id):
                return await interaction.response.send_message(
                    f"You already own a room: <#{channel_id}>.",
                    ephemeral=True,
                )

            await self.database.remove_room(channel_id)

        name = re.sub(r"\s+", " ", self.name).strip()[:40] or "Temporary Room"

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                view_channel=False, connect=False
            ),
            user: discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True,
                move_members=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, connect=True, manage_channels=True
            ),
        }

        if not private:
            # public = every verified member, never the unverified
            overwrites[verified] = discord.PermissionOverwrite(
                view_channel=True, connect=True, speak=True
            )

        moderator = discord.utils.get(guild.roles, name="Moderator")

        if moderator:
            overwrites[moderator] = discord.PermissionOverwrite(
                view_channel=True, connect=True, move_members=True
            )

        channel = await guild.create_voice_channel(
            f"🎙️ {name}",
            category=category,
            overwrites=overwrites,
            reason=f"Temporary room created by {user}",
        )

        expires = int(datetime.now(UTC).timestamp()) + self.minutes * 60

        await self.database.add_room(channel.id, guild.id, user.id, expires)

        await interaction.response.edit_message(
            content=(
                f"Room ready: {channel.mention} • "
                f"{'Private' if private else 'Public'} • "
                f"expires in {self.minutes} minutes."
            ),
            view=None,
        )

    @discord.ui.button(label="Public", emoji="🌐", style=discord.ButtonStyle.success)
    async def public(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.create(interaction, False)

    @discord.ui.button(label="Private", emoji="🔒", style=discord.ButtonStyle.secondary)
    async def private(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.create(interaction, True)


# ============================================================
# TICKETS
# ============================================================

class TicketView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="Open private ticket",
        emoji="🎫",
        style=discord.ButtonStyle.success,
        custom_id="nexus:ticket:open",
    )
    async def open_ticket(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        guild = interaction.guild
        user = interaction.user

        if guild is None or not isinstance(user, discord.Member):
            return await interaction.response.send_message(
                "Server only.", ephemeral=True
            )

        await interaction.response.defer(ephemeral=True, thinking=True)

        previous = await self.database.open_ticket_for(guild.id, user.id)

        if previous:
            if guild.get_channel(previous):
                return await interaction.followup.send(
                    f"You already have an open ticket: <#{previous}>.",
                    ephemeral=True,
                )

            await self.database.close_ticket(previous)  # channel was deleted

        category = discord.utils.get(guild.categories, name=SERVICES_CATEGORY)
        support = discord.utils.get(guild.roles, name="Support Team")
        moderator = discord.utils.get(guild.roles, name="Moderator")

        if category is None or support is None:
            return await interaction.followup.send(
                "Ticket system not configured. Run /setup.", ephemeral=True
            )

        safe_name = (
            re.sub(r"[^a-z0-9-]", "", user.name.lower().replace(" ", "-"))[:30]
            or "member"
        )

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, read_message_history=True
            ),
            support: discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True,
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_channels=True
            ),
        }

        if moderator:
            overwrites[moderator] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True,
                read_message_history=True, manage_messages=True,
            )

        channel = await guild.create_text_channel(
            f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            reason=f"Ticket opened by {user}",
        )

        await self.database.create_ticket(channel.id, guild.id, user.id)

        embed = hx_embed(
            "SUPPORT CHANNEL // ESTABLISHED",
            f"{GRN}[OK]{RST}   Secure line open for {user.mention}\n"
            f"{CYN}[AWAIT]{RST} Support agent will respond shortly",
            colour=0x7C3AED,
            member=user,
        )

        await channel.send(
            content=f"{user.mention} {support.mention}",
            embed=embed,
            view=CloseTicketView(self.database),
        )

        await interaction.followup.send(
            f"Secure channel created: {channel.mention}", ephemeral=True
        )


class CloseTicketView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="Close ticket",
        emoji="🔒",
        style=discord.ButtonStyle.danger,
        custom_id="nexus:ticket:close",
    )
    async def close_ticket(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        channel = interaction.channel
        user = interaction.user

        if not isinstance(channel, discord.TextChannel) or not interaction.guild:
            return await interaction.response.send_message(
                "This is not a ticket channel.", ephemeral=True
            )

        owner = await self.database.ticket_owner(channel.id)

        if owner is None:
            return await interaction.response.send_message(
                "This is not a ticket channel.", ephemeral=True
            )

        is_staff = isinstance(user, discord.Member) and (
            _has_role(user, SUPPORT_ROLES)
            or user.guild_permissions.manage_channels
        )

        if owner != user.id and not is_staff:
            return await interaction.response.send_message(
                "Only the ticket owner or staff can close this ticket.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            "Ticket will close in five seconds.", ephemeral=True
        )

        await self.database.close_ticket(channel.id)
        await asyncio.sleep(5)

        with suppress(discord.NotFound, discord.Forbidden):
            await channel.delete(reason=f"Ticket closed by {user}")


# ============================================================
# REACTION ROLES
# ============================================================

class ReactionRoleCreateView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(
        label="Add Reaction Role",
        emoji="🎭",
        style=discord.ButtonStyle.primary,
        custom_id="nexus:rr:create",
    )
    async def create_rr(
        self, interaction: discord.Interaction, _: discord.ui.Button
    ) -> None:
        user = interaction.user

        if not isinstance(user, discord.Member) or not user.guild_permissions.manage_roles:
            return await interaction.response.send_message(
                "Manage Roles required.", ephemeral=True
            )

        await interaction.response.send_modal(ReactionRoleModal(self.database))


class ReactionRoleModal(discord.ui.Modal, title="Create Reaction Role"):
    message_id = discord.ui.TextInput(
        label="Message ID",
        placeholder="Right-click message → Copy Message ID",
    )

    emoji = discord.ui.TextInput(
        label="Emoji",
        placeholder="😀",
    )

    role_name = discord.ui.TextInput(
        label="Role Name",
        placeholder="e.g. Gamer",
    )

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database

    async def on_submit(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "Server only.", ephemeral=True
            )

        try:
            msg_id = int(str(self.message_id).strip())
        except ValueError:
            return await interaction.response.send_message(
                "Invalid message ID.", ephemeral=True
            )

        role = discord.utils.get(guild.roles, name=str(self.role_name).strip())

        if not role:
            return await interaction.response.send_message(
                "Role not found.", ephemeral=True
            )

        if not is_self_assignable(role) or role >= guild.me.top_role:
            return await interaction.response.send_message(
                "That role cannot be used as a reaction role "
                "(Nexus roles, staff roles and roles with moderation "
                "permissions are blocked).",
                ephemeral=True,
            )

        emoji = str(self.emoji).strip()

        await self.database.add_reaction_role(guild.id, msg_id, emoji, role.id)

        with suppress(Exception):
            message = await interaction.channel.fetch_message(msg_id)
            await message.add_reaction(emoji)

        await interaction.response.send_message(
            f"{GRN}[OK]{RST} Reaction role created: {emoji} → {role.mention}",
            ephemeral=True,
        )


# ============================================================
# SUGGESTIONS
# ============================================================

class SuggestionVoteView(discord.ui.View):
    def __init__(self, database: Database, suggestion_id: int) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.suggestion_id = suggestion_id

        # every suggestion gets its own button ids
        self.upvote.custom_id = f"nexus:suggest:{suggestion_id}:up"
        self.downvote.custom_id = f"nexus:suggest:{suggestion_id}:down"

    async def _refresh_message(self, interaction: discord.Interaction) -> None:
        suggestion = await self.database.get_suggestion(self.suggestion_id)

        if suggestion is None or not interaction.message:
            return

        upvotes, downvotes = suggestion[5], suggestion[6]

        embed = (
            interaction.message.embeds[0]
            if interaction.message.embeds
            else discord.Embed(title="💡 Suggestion")
        )

        found_up = found_down = False

        for index, field in enumerate(embed.fields):
            name = field.name.lower()

            if "upvote" in name:
                embed.set_field_at(index, name="👍 Upvotes", value=str(upvotes), inline=True)
                found_up = True
            elif "downvote" in name:
                embed.set_field_at(index, name="👎 Downvotes", value=str(downvotes), inline=True)
                found_down = True

        if not found_up:
            embed.add_field(name="👍 Upvotes", value=str(upvotes), inline=True)

        if not found_down:
            embed.add_field(name="👎 Downvotes", value=str(downvotes), inline=True)

        self.upvote.label = f"Upvote • {upvotes}"
        self.downvote.label = f"Downvote • {downvotes}"

        await interaction.message.edit(embed=embed, view=self)

    async def _vote(self, interaction: discord.Interaction, up: bool) -> None:
        user_id = interaction.user.id

        current = await self.database.get_suggestion_vote(
            self.suggestion_id, user_id
        )

        if current == (1 if up else -1):
            return await interaction.response.send_message(
                f"You have already {'upvoted' if up else 'downvoted'} "
                f"this suggestion.",
                ephemeral=True,
            )

        if not await self.database.vote_suggestion(
            self.suggestion_id, user_id, up
        ):
            return await interaction.response.send_message(
                "Suggestion not found.", ephemeral=True
            )

        if current is None:
            message = (
                "👍 Your upvote has been recorded."
                if up
                else "👎 Your downvote has been recorded."
            )
        elif up:
            message = "Your vote has been changed from Downvote to Upvote."
        else:
            message = "Your vote has been changed from Upvote to Downvote."

        await interaction.response.send_message(message, ephemeral=True)

        with suppress(discord.NotFound, discord.HTTPException):
            await self._refresh_message(interaction)

    @discord.ui.button(label="Upvote", emoji="👍", style=discord.ButtonStyle.success)
    async def upvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._vote(interaction, True)

    @discord.ui.button(label="Downvote", emoji="👎", style=discord.ButtonStyle.danger)
    async def downvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._vote(interaction, False)


# ============================================================
# AUTOMOD PANEL
# ============================================================

class AutoModConfigView(discord.ui.View):
    NAMES = {1: "Anti-Spam", 2: "Anti-Link", 3: "Anti-Caps"}

    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    async def _toggle(self, interaction: discord.Interaction, field: int) -> None:
        user = interaction.user
        guild = interaction.guild

        if (
            guild is None
            or not isinstance(user, discord.Member)
            or not user.guild_permissions.manage_guild
        ):
            return await interaction.response.send_message(
                "Manage Server required.", ephemeral=True
            )

        config = await self.database.get_automod(guild.id)
        values = list(config) if config else [guild.id, 0, 0, 0, 5, 300]

        values[field] = 0 if values[field] else 1

        await self.database.set_automod(guild.id, *values[1:])

        # apply immediately instead of waiting for the cache refresh
        cache = getattr(interaction.client, "automod_cache", None)

        if cache is not None:
            cache.pop(guild.id, None)

        await interaction.response.send_message(
            f"{self.NAMES[field]} {'ENABLED' if values[field] else 'DISABLED'}",
            ephemeral=True,
        )

    @discord.ui.button(label="Toggle Anti-Spam", emoji="🛡️", style=discord.ButtonStyle.primary, custom_id="nexus:am:spam")
    async def toggle_spam(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._toggle(interaction, 1)

    @discord.ui.button(label="Toggle Anti-Link", emoji="🔗", style=discord.ButtonStyle.primary, custom_id="nexus:am:link")
    async def toggle_link(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._toggle(interaction, 2)

    @discord.ui.button(label="Toggle Anti-Caps", emoji="🔤", style=discord.ButtonStyle.primary, custom_id="nexus:am:caps")
    async def toggle_caps(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._toggle(interaction, 3)
