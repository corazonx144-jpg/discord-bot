from __future__ import annotations

import asyncio
import hashlib
import json
import re
from datetime import UTC, datetime

import discord

from database import Database

# ── ANSI colour codes ──
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


def _hash_id(uid: int) -> str:
    return hashlib.sha256(str(uid).encode()).hexdigest()[:16].upper()


def _bar(pct: int, width: int = 20) -> str:
    filled = int(width * pct / 100)
    return f"{GRN}{chr(9608)*filled}{BLK}{chr(9617)*(width-filled)}{RST}"


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
    embed = discord.Embed(description=f"```ansi\n{frame}\n```", colour=colour)
    embed.set_footer(text="root@nexus:~$ ▮", icon_url="https://cdn.discordapp.com/embed/avatars/0.png")
    if member:
        embed.set_thumbnail(url=member.display_avatar.url)
    return embed


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
    async def proceed(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        stage = await self.database.get_member_stage(interaction.guild.id, interaction.user.id)

        if stage == "verified":
            embed = hx_embed(
                "SECTOR 02 // CLEARANCE GATE",
                f"{GRN}[AUTH]{RST}   Identity verified for {interaction.user.mention}\n"
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
                member=interaction.user,
            )
            await interaction.response.send_message(embed=embed, view=RoleView(self.database), ephemeral=True)

        elif stage == "cleared":
            embed = hx_embed(
                "SECTOR 03 // TERMINAL CHAT",
                f"{GRN}[AUTH]{RST}   Clearance level confirmed\n"
                f"{CYN}[NET]{RST}    Operational channels unlocked\n"
                f"{YLW}[NOTE]{RST}   Use /status for system diagnostics\n"
                f"{GRN}[WELCOME]{RST} {interaction.user.mention} — you are cleared for all sectors.",
                colour=0x00FF41,
                member=interaction.user,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await interaction.response.send_message(
                f"{RED}[ERR]{RST}  Protocol mismatch. Current stage: `{stage}`",
                ephemeral=True,
            )


class VerificationView(discord.ui.View):
    def __init__(self, guild_id: int = 0, target_id: int = 0) -> None:
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.target_id = target_id

    @discord.ui.button(label="INITIATE VERIFY.EXE", emoji="🛡️", style=discord.ButtonStyle.success, custom_id="nexus:verify")
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Server only.", ephemeral=True)

        if self.target_id and interaction.user.id != self.target_id:
            return await interaction.response.send_message(
                f"{RED}[ERR]{RST}  This scan session is not assigned to your identity.", ephemeral=True
            )

        db = getattr(interaction.client, "database", None)
        if db is None:
            return await interaction.response.send_message("Database offline.", ephemeral=True)

        queue = discord.utils.get(interaction.guild.text_channels, name="🔐-approval-queue")
        if queue is None:
            return await interaction.response.send_message("Run /setup first.", ephemeral=True)

        status = await db.verification_status(interaction.guild.id, interaction.user.id)
        if status == "approved":
            return await interaction.response.send_message("Already approved.", ephemeral=True)
        if status == "pending":
            return await interaction.response.send_message("Request already queued.", ephemeral=True)

        await db.set_verification_status(interaction.guild.id, interaction.user.id, "pending")
        await db.set_member_stage(interaction.guild.id, interaction.user.id, "pending_verify")

        proc = hx_embed(
            "VERIFY.EXE // EXECUTING",
            f"{CYN}[TX]{RST}     Encrypting payload...\n"
            f"{CYN}[ROUTE]{RST}  Administration Queue\n"
            f"{GRN}[STATUS]{RST} Awaiting manual review...",
            colour=0x7C3AED,
            member=interaction.user,
        )
        await interaction.response.send_message(embed=proc, ephemeral=True)

        req_embed = hx_embed(
            "ACCESS REQUEST // TX",
            f"{CYN}[TX]{RST}     Target: Administration Queue\n"
            f"{YLW}[ID]{RST}     {interaction.user.mention}  `UID:{interaction.user.id}`\n"
            f"{CYN}[HASH]{RST}   {_hash_id(interaction.user.id)}\n"
            f"{GRN}[STATUS]{RST} PENDING REVIEW",
            colour=0x7C3AED,
            member=interaction.user,
        )
        req_embed.set_footer(text=f"member:{interaction.user.id}")
        await queue.send(embed=req_embed, view=ApprovalView(db))

        staff_role = discord.utils.get(interaction.guild.roles, name="Support Team")
        mod_role = discord.utils.get(interaction.guild.roles, name="Moderator")
        mention_parts = []
        if staff_role:
            mention_parts.append(staff_role.mention)
        if mod_role:
            mention_parts.append(mod_role.mention)
        if mention_parts:
            await queue.send(" ".join(mention_parts), delete_after=3600)

        if interaction.guild.owner:
            try:
                await interaction.guild.owner.send(
                    f"{CYN}[ALERT]{RST} New access request in **{interaction.guild.name}** from {interaction.user} (`{interaction.user.id}`)."
                )
            except discord.Forbidden:
                pass


class ApprovalView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    async def decide(self, interaction: discord.Interaction, approved: bool) -> None:
        if not interaction.guild or not interaction.user.guild_permissions.manage_channels or not interaction.message or not interaction.message.embeds:
            return await interaction.response.send_message("Manage Channels permission required.", ephemeral=True)

        footer = interaction.message.embeds[0].footer.text or ""
        arrival = discord.utils.get(interaction.guild.text_channels, name="⌁-arrival-terminal")

        if footer.startswith("clearance:"):
            _, raw_member_id, role_name = footer.split(":", 2)
            member_id = int(raw_member_id)
            member = interaction.guild.get_member(member_id)
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if approved and member and role:
                if role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
                    return await interaction.response.send_message("Move my role above this clearance role before approving.", ephemeral=True)
                await member.add_roles(role, reason=f"Clearance approved by {interaction.user}")
                await self.database.set_member_stage(interaction.guild.id, member_id, "cleared")
                if arrival:
                    tx_embed = hx_embed(
                        "CLEARANCE UPGRADED // SECTOR 03 READY",
                        f"{GRN}[SUCCESS]{RST}  {role_name} granted to {member.mention}\n"
                        f"{CYN}[NEXT]{RST}    Enter Terminal Chat & Secure Nodes\n"
                        f"{DIM}[TIME]{RST}    {datetime.now(UTC).strftime('%H:%M:%S')} UTC",
                        colour=0xFFD700,
                        member=member,
                    )
                    await arrival.send(content=member.mention, embed=tx_embed, view=StageTransitionView(self.database))
            await self.database.set_clearance_status(interaction.guild.id, member_id, role_name, "approved" if approved else "rejected")

        elif footer.startswith("member:"):
            member_id = int(footer.split(":", 1)[1])
            member = interaction.guild.get_member(member_id)
            if approved and member:
                role = discord.utils.get(interaction.guild.roles, name="Verified")
                if role is None or role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
                    return await interaction.response.send_message("Move my role above Verified before approving.", ephemeral=True)
                await member.add_roles(role, reason=f"Access approved by {interaction.user}")
                await self.database.set_member_stage(interaction.guild.id, member_id, "verified")
                if arrival:
                    tx_embed = hx_embed(
                        "ACCESS GRANTED // PROTOCOL COMPLETE",
                        f"{GRN}[SUCCESS]{RST}  Identity verified for {member.mention}\n"
                        f"{CYN}[CLEARANCE]{RST} LEVEL 1 — VERIFIED\n"
                        f"{CYN}[NEXT]{RST}    Proceed to Clearance Gate (Sector 02)\n"
                        f"{DIM}[TIME]{RST}    {datetime.now(UTC).strftime('%H:%M:%S')} UTC",
                        colour=0x00FF41,
                        member=member,
                    )
                    await arrival.send(content=member.mention, embed=tx_embed, view=StageTransitionView(self.database))
            await self.database.set_verification_status(interaction.guild.id, member_id, "approved" if approved else "rejected")

        else:
            return await interaction.response.send_message("Invalid approval record.", ephemeral=True)

        status = "approved" if approved else "rejected"
        embed = interaction.message.embeds[0]
        embed.colour = discord.Colour.green() if approved else discord.Colour.red()
        embed.title = f"ACCESS {status.upper()}"
        embed.add_field(name="Reviewed by", value=interaction.user.mention, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="APPROVE", emoji="✅", style=discord.ButtonStyle.success, custom_id="nexus:verify:approve")
    async def approve(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.decide(interaction, True)

    @discord.ui.button(label="REJECT", emoji="⛔", style=discord.ButtonStyle.danger, custom_id="nexus:verify:reject")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.decide(interaction, False)


class RoleView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    async def _check_and_request(self, interaction: discord.Interaction, role_name: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Server only.", ephemeral=True)
        verified = discord.utils.get(interaction.guild.roles, name="Verified")
        if verified not in interaction.user.roles:
            return await interaction.response.send_message("Verification required first.", ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        queue = discord.utils.get(interaction.guild.text_channels, name="🔐-approval-queue")
        if role is None or queue is None:
            return await interaction.response.send_message("Run /setup first.", ephemeral=True)
        previous = await self.database.clearance_status(interaction.guild.id, interaction.user.id)
        if role in interaction.user.roles or (previous and previous[1] == "approved"):
            return await interaction.response.send_message("You already hold this clearance.", ephemeral=True)
        if previous and previous[1] == "pending":
            return await interaction.response.send_message(f"Your {previous[0]} request is awaiting review.", ephemeral=True)

        await self.database.set_clearance_status(interaction.guild.id, interaction.user.id, role_name, "pending")
        req_embed = hx_embed(
            "CLEARANCE REQUEST // TX",
            f"{CYN}[TX]{RST}     Member: {interaction.user.mention}\n"
            f"{YLW}[REQ]{RST}    Requested clearance: **{role_name}**\n"
            f"{CYN}[HASH]{RST}   {_hash_id(interaction.user.id)}\n"
            f"{GRN}[STATUS]{RST} PENDING REVIEW",
            colour=0x7C3AED,
            member=interaction.user,
        )
        req_embed.set_footer(text=f"clearance:{interaction.user.id}:{role_name}")
        await queue.send(embed=req_embed, view=ApprovalView(self.database))
        await interaction.response.send_message(
            f"{GRN}[OK]{RST}  {role_name} clearance request submitted.", ephemeral=True
        )

    @discord.ui.button(label="Elite Agent", emoji="⚡", style=discord.ButtonStyle.primary, custom_id="nexus:role:elite")
    async def elite(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Elite Agent")

    @discord.ui.button(label="Guest Node", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="nexus:role:guest")
    async def guest(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Guest Node")

    @discord.ui.button(label="Support Team", emoji="🛡️", style=discord.ButtonStyle.success, custom_id="nexus:role:support")
    async def support(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Support Team")

    @discord.ui.button(label="Developer", emoji="💻", style=discord.ButtonStyle.primary, custom_id="nexus:role:dev")
    async def developer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Developer")

    @discord.ui.button(label="Moderator", emoji="🔨", style=discord.ButtonStyle.danger, custom_id="nexus:role:mod")
    async def moderator(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Moderator")

    @discord.ui.button(label="VIP", emoji="👑", style=discord.ButtonStyle.primary, row=1, custom_id="nexus:role:vip")
    async def vip(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "VIP")

    @discord.ui.button(label="Streamer", emoji="📺", style=discord.ButtonStyle.secondary, row=1, custom_id="nexus:role:streamer")
    async def streamer(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Streamer")

    @discord.ui.button(label="Artist", emoji="🎨", style=discord.ButtonStyle.primary, row=1, custom_id="nexus:role:artist")
    async def artist(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Artist")

    @discord.ui.button(label="Musician", emoji="🎵", style=discord.ButtonStyle.secondary, row=1, custom_id="nexus:role:musician")
    async def musician(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self._check_and_request(interaction, "Musician")


class RoomPanelView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Create voice room", emoji="🎛️", style=discord.ButtonStyle.primary, custom_id="nexus:room:begin")
    async def begin(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(RoomModal(self.database))


class RoomModal(discord.ui.Modal, title="Configure your temporary room"):
    room_name = discord.ui.TextInput(label="Room name", placeholder="e.g. Night Ops", max_length=40)
    minutes = discord.ui.TextInput(label="Duration in minutes (5–720)", placeholder="60", default="60", max_length=3)

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            duration = max(5, min(720, int(str(self.minutes))))
        except ValueError:
            return await interaction.response.send_message("Duration must be a number from 5 to 720.", ephemeral=True)
        await interaction.response.send_message(
            "Choose the room privacy:", view=RoomPrivacyView(self.database, str(self.room_name), duration), ephemeral=True
        )


class RoomPrivacyView(discord.ui.View):
    def __init__(self, database: Database, name: str, minutes: int) -> None:
        super().__init__(timeout=120)
        self.database, self.name, self.minutes = database, name, minutes

    async def create(self, interaction: discord.Interaction, private: bool) -> None:
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Server only.", ephemeral=True)
        category = discord.utils.get(guild.categories, name="🎛️ ─ ROOM GENERATOR")
        if not category:
            return await interaction.response.send_message("Run /setup first.", ephemeral=True)
        name = re.sub(r"[^a-z0-9-]", "-", self.name.lower()).strip("-")[:40] or "temporary-room"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=not private, connect=not private),
            interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True),
        }
        channel = await guild.create_voice_channel(
            f"🎙️ {name}", category=category, overwrites=overwrites, reason=f"Temporary room created by {interaction.user}"
        )
        expires = int(datetime.now(UTC).timestamp()) + self.minutes * 60
        await self.database.add_room(channel.id, guild.id, interaction.user.id, expires)
        await interaction.response.edit_message(
            content=f"Room ready: {channel.mention} • {'Private' if private else 'Public'} • expires in {self.minutes} minutes.", view=None
        )

    @discord.ui.button(label="Public", emoji="🌐", style=discord.ButtonStyle.success)
    async def public(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.create(interaction, False)

    @discord.ui.button(label="Private", emoji="🔒", style=discord.ButtonStyle.secondary)
    async def private(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.create(interaction, True)


class TicketView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Open private ticket", emoji="🎫", style=discord.ButtonStyle.success, custom_id="nexus:ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Server only.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        previous = await self.database.open_ticket_for(guild.id, interaction.user.id)
        if previous and guild.get_channel(previous):
            return await interaction.followup.send(f"You already have an open ticket: <#{previous}>.", ephemeral=True)
        category = discord.utils.get(guild.categories, name="🎫 ─ SUPPORT NODE")
        staff = discord.utils.get(guild.roles, name="Support Team")
        if category is None or staff is None:
            return await interaction.followup.send("Ticket system not configured. Run /setup.", ephemeral=True)
        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:30] or "member"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            staff: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        channel = await guild.create_text_channel(
            f"ticket-{safe_name}", category=category, overwrites=overwrites, reason=f"Ticket opened by {interaction.user}"
        )
        await self.database.create_ticket(channel.id, guild.id, interaction.user.id)
        embed = hx_embed(
            "SUPPORT CHANNEL // ESTABLISHED",
            f"{GRN}[OK]{RST}   Secure line open for {interaction.user.mention}\n"
            f"{CYN}[AWAIT]{RST} Support agent will respond shortly",
            colour=0x7C3AED,
            member=interaction.user,
        )
        await channel.send(embed=embed, view=CloseTicketView(self.database))
        await interaction.followup.send(f"Secure channel created: {channel.mention}", ephemeral=True)


class CloseTicketView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Close ticket", emoji="🔒", style=discord.ButtonStyle.danger, custom_id="nexus:ticket:close")
    async def close_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not isinstance(interaction.channel, discord.TextChannel) or not interaction.guild:
            return await interaction.response.send_message("This is not a ticket channel.", ephemeral=True)
        owner = await self.database.ticket_owner(interaction.channel.id)
        is_staff = isinstance(interaction.user, discord.Member) and interaction.user.guild_permissions.manage_channels
        if owner != interaction.user.id and not is_staff:
            return await interaction.response.send_message("Only the ticket owner or staff can close this ticket.", ephemeral=True)
        await interaction.response.send_message("Ticket will close in five seconds.", ephemeral=True)
        await self.database.close_ticket(interaction.channel.id)
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")


# ── NEW: Reaction Roles View ──
class ReactionRoleCreateView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Add Reaction Role", emoji="🎭", style=discord.ButtonStyle.primary, custom_id="nexus:rr:create")
    async def create_rr(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.manage_roles:
            return await interaction.response.send_message("Manage Roles required.", ephemeral=True)
        await interaction.response.send_modal(ReactionRoleModal(self.database))


class ReactionRoleModal(discord.ui.Modal, title="Create Reaction Role"):
    message_id = discord.ui.TextInput(label="Message ID", placeholder="Right-click message → Copy Message ID")
    emoji = discord.ui.TextInput(label="Emoji", placeholder="😀 or :custom_emoji:")
    role_name = discord.ui.TextInput(label="Role Name", placeholder="Verified")

    def __init__(self, database: Database) -> None:
        super().__init__()
        self.database = database

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            msg_id = int(str(self.message_id))
        except ValueError:
            return await interaction.response.send_message("Invalid message ID.", ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name=str(self.role_name))
        if not role:
            return await interaction.response.send_message("Role not found.", ephemeral=True)

        await self.database.add_reaction_role(interaction.guild.id, msg_id, str(self.emoji), role.id)

        # Try to add reaction to the message
        try:
            channel = interaction.channel
            msg = await channel.fetch_message(msg_id)
            await msg.add_reaction(str(self.emoji))
        except Exception:
            pass

        await interaction.response.send_message(
            f"{GRN}[OK]{RST} Reaction role created: {self.emoji} → {role.mention}", ephemeral=True
        )


# ── NEW: Suggestion Vote View ──
class SuggestionVoteView(discord.ui.View):
    def __init__(self, database: Database, suggestion_id: int) -> None:
        super().__init__(timeout=None)
        self.database = database
        self.suggestion_id = suggestion_id

    @discord.ui.button(label="Upvote", emoji="👍", style=discord.ButtonStyle.success, custom_id="nexus:suggest:up")
    async def upvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.database.vote_suggestion(self.suggestion_id, True)
        await interaction.response.send_message("Upvoted.", ephemeral=True)

    @discord.ui.button(label="Downvote", emoji="👎", style=discord.ButtonStyle.danger, custom_id="nexus:suggest:down")
    async def downvote(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.database.vote_suggestion(self.suggestion_id, False)
        await interaction.response.send_message("Downvoted.", ephemeral=True)


# ── NEW: AutoMod Config View ──
class AutoModConfigView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Toggle Anti-Spam", emoji="🛡️", style=discord.ButtonStyle.primary, custom_id="nexus:am:spam")
    async def toggle_spam(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Manage Server required.", ephemeral=True)
        config = await self.database.get_automod(interaction.guild.id)
        new_val = 0 if (config and config[1]) else 1
        await self.database.set_automod(interaction.guild.id, new_val, config[2] if config else 0, config[3] if config else 0, config[4] if config else 5, config[5] if config else 300)
        status = "ENABLED" if new_val else "DISABLED"
        await interaction.response.send_message(f"Anti-Spam {status}", ephemeral=True)

    @discord.ui.button(label="Toggle Anti-Link", emoji="🔗", style=discord.ButtonStyle.primary, custom_id="nexus:am:link")
    async def toggle_link(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Manage Server required.", ephemeral=True)
        config = await self.database.get_automod(interaction.guild.id)
        new_val = 0 if (config and config[2]) else 1
        await self.database.set_automod(interaction.guild.id, config[1] if config else 0, new_val, config[3] if config else 0, config[4] if config else 5, config[5] if config else 300)
        status = "ENABLED" if new_val else "DISABLED"
        await interaction.response.send_message(f"Anti-Link {status}", ephemeral=True)

    @discord.ui.button(label="Toggle Anti-Caps", emoji="🔤", style=discord.ButtonStyle.primary, custom_id="nexus:am:caps")
    async def toggle_caps(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Manage Server required.", ephemeral=True)
        config = await self.database.get_automod(interaction.guild.id)
        new_val = 0 if (config and config[3]) else 1
        await self.database.set_automod(interaction.guild.id, config[1] if config else 0, config[2] if config else 0, new_val, config[4] if config else 5, config[5] if config else 300)
        status = "ENABLED" if new_val else "DISABLED"
        await interaction.response.send_message(f"Anti-Caps {status}", ephemeral=True)
