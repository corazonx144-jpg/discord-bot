from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime

import discord

from database import Database

ACCENT = 0x7C3AED


def panel_embed(title: str, body: str) -> discord.Embed:
    return discord.Embed(title=title, description=body, colour=ACCENT, timestamp=datetime.now(UTC))


class VerificationView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Verify identity", emoji="🛡️", style=discord.ButtonStyle.success, custom_id="nexus:verify")
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This button only works inside a server.", ephemeral=True)
        queue = discord.utils.get(interaction.guild.text_channels, name="🔐-approval-queue")
        if queue is None:
            return await interaction.response.send_message("The server has not been configured. Ask an administrator to run /setup.", ephemeral=True)
        status = await self.database.verification_status(interaction.guild.id, interaction.user.id)
        if status == "approved": return await interaction.response.send_message("Your access is already approved.", ephemeral=True)
        if status == "pending": return await interaction.response.send_message("Your verification request is already waiting for review.", ephemeral=True)
        await self.database.set_verification_status(interaction.guild.id, interaction.user.id, "pending")
        embed = panel_embed("ACCESS REQUEST", f"Member: {interaction.user.mention}\nUser ID: `{interaction.user.id}`\n\nApprove only members you recognize.")
        embed.set_footer(text=f"member:{interaction.user.id}")
        await queue.send(embed=embed, view=ApprovalView(self.database))
        # The private queue is the authoritative record; a DM is a useful owner alert when available.
        if interaction.guild.owner:
            try:
                await interaction.guild.owner.send(f"New access request in **{interaction.guild.name}** from {interaction.user} (`{interaction.user.id}`). Review it in 🔐-approval-queue.")
            except discord.Forbidden:
                pass
        await interaction.response.send_message("Request transmitted to the administration queue. Wait for approval.", ephemeral=True)


class ApprovalView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None); self.database = database

    async def decide(self, interaction: discord.Interaction, approved: bool) -> None:
        if not interaction.guild or not interaction.user.guild_permissions.administrator or not interaction.message or not interaction.message.embeds:
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        footer = interaction.message.embeds[0].footer.text or ""
        if footer.startswith("clearance:"):
            _, raw_member_id, role_name = footer.split(":", 2)
            member_id = int(raw_member_id); member = interaction.guild.get_member(member_id)
            role = discord.utils.get(interaction.guild.roles, name=role_name)
            if approved and member and role:
                if role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
                    return await interaction.response.send_message("Move my role above this clearance role before approving.", ephemeral=True)
                await member.add_roles(role, reason=f"Clearance approved by {interaction.user}")
            await self.database.set_clearance_status(interaction.guild.id, member_id, role_name, "approved" if approved else "rejected")
        elif footer.startswith("member:"):
            member_id = int(footer.split(":", 1)[1]); member = interaction.guild.get_member(member_id)
            if approved and member:
                role = discord.utils.get(interaction.guild.roles, name="Verified")
                if role is None or role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
                    return await interaction.response.send_message("Move my role above Verified before approving.", ephemeral=True)
                await member.add_roles(role, reason=f"Access approved by {interaction.user}")
            await self.database.set_verification_status(interaction.guild.id, member_id, "approved" if approved else "rejected")
        else:
            return await interaction.response.send_message("Invalid approval record.", ephemeral=True)
        status = "approved" if approved else "rejected"
        embed = interaction.message.embeds[0]; embed.colour = discord.Colour.green() if approved else discord.Colour.red(); embed.title = f"ACCESS {status.upper()}"; embed.add_field(name="Reviewed by", value=interaction.user.mention, inline=False)
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="Approve", emoji="✅", style=discord.ButtonStyle.success, custom_id="nexus:verify:approve")
    async def approve(self, interaction: discord.Interaction, _: discord.ui.Button) -> None: await self.decide(interaction, True)
    @discord.ui.button(label="Reject", emoji="⛔", style=discord.ButtonStyle.danger, custom_id="nexus:verify:reject")
    async def reject(self, interaction: discord.Interaction, _: discord.ui.Button) -> None: await self.decide(interaction, False)


class RoleView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None); self.database = database

    async def request(self, interaction: discord.Interaction, role_name: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This button only works inside a server.", ephemeral=True)
        verified = discord.utils.get(interaction.guild.roles, name="Verified")
        if verified not in interaction.user.roles:
            return await interaction.response.send_message("Access approval is required before selecting clearance roles.", ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        queue = discord.utils.get(interaction.guild.text_channels, name="🔐-approval-queue")
        if role is None or queue is None:
            return await interaction.response.send_message("Run /setup first.", ephemeral=True)
        previous = await self.database.clearance_status(interaction.guild.id, interaction.user.id)
        if role in interaction.user.roles or (previous and previous[1] == "approved"):
            return await interaction.response.send_message("You already hold this clearance.", ephemeral=True)
        if previous and previous[1] == "pending":
            return await interaction.response.send_message(f"Your {previous[0]} clearance request is awaiting review.", ephemeral=True)
        await self.database.set_clearance_status(interaction.guild.id, interaction.user.id, role_name, "pending")
        embed = panel_embed("CLEARANCE REQUEST", f"Member: {interaction.user.mention}\nRequested clearance: **{role_name}**\n\nGrant only after review.")
        embed.set_footer(text=f"clearance:{interaction.user.id}:{role_name}")
        await queue.send(embed=embed, view=ApprovalView(self.database))
        await interaction.response.send_message(f"{role_name} clearance request submitted for owner approval.", ephemeral=True)

    @discord.ui.button(label="Elite agent", emoji="⚡", style=discord.ButtonStyle.primary, custom_id="nexus:role:elite")
    async def elite(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.request(interaction, "Elite Agent")

    @discord.ui.button(label="Guest node", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="nexus:role:guest")
    async def guest(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.request(interaction, "Guest Node")


class RoomPanelView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None); self.database = database
    @discord.ui.button(label="Create voice room", emoji="🎛️", style=discord.ButtonStyle.primary, custom_id="nexus:room:begin")
    async def begin(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await interaction.response.send_modal(RoomModal(self.database))


class RoomModal(discord.ui.Modal, title="Configure your temporary room"):
    room_name = discord.ui.TextInput(label="Room name", placeholder="e.g. Night Ops", max_length=40)
    minutes = discord.ui.TextInput(label="Duration in minutes (5–720)", placeholder="60", default="60", max_length=3)
    def __init__(self, database: Database) -> None: super().__init__(); self.database = database
    async def on_submit(self, interaction: discord.Interaction) -> None:
        try: duration = max(5, min(720, int(str(self.minutes))))
        except ValueError: return await interaction.response.send_message("Duration must be a number from 5 to 720.", ephemeral=True)
        await interaction.response.send_message("Choose the room privacy:", view=RoomPrivacyView(self.database, str(self.room_name), duration), ephemeral=True)


class RoomPrivacyView(discord.ui.View):
    def __init__(self, database: Database, name: str, minutes: int) -> None:
        super().__init__(timeout=120); self.database, self.name, self.minutes = database, name, minutes
    async def create(self, interaction: discord.Interaction, private: bool) -> None:
        guild = interaction.guild
        if not guild or not isinstance(interaction.user, discord.Member): return await interaction.response.send_message("Server only.", ephemeral=True)
        category = discord.utils.get(guild.categories, name="🎛️ ─ ROOM GENERATOR")
        if not category: return await interaction.response.send_message("Run /setup first.", ephemeral=True)
        name = re.sub(r"[^a-z0-9-]", "-", self.name.lower()).strip("-")[:40] or "temporary-room"
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=not private, connect=not private), interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, speak=True), guild.me: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)}
        channel = await guild.create_voice_channel(f"🎙️ {name}", category=category, overwrites=overwrites, reason=f"Temporary room created by {interaction.user}")
        expires = int(datetime.now(UTC).timestamp()) + self.minutes * 60
        await self.database.add_room(channel.id, guild.id, interaction.user.id, expires)
        await interaction.response.edit_message(content=f"Room ready: {channel.mention} • {'Private' if private else 'Public'} • expires in {self.minutes} minutes.", view=None)
    @discord.ui.button(label="Public", emoji="🌐", style=discord.ButtonStyle.success)
    async def public(self, interaction: discord.Interaction, _: discord.ui.Button) -> None: await self.create(interaction, False)
    @discord.ui.button(label="Private", emoji="🔒", style=discord.ButtonStyle.secondary)
    async def private(self, interaction: discord.Interaction, _: discord.ui.Button) -> None: await self.create(interaction, True)


class TicketView(discord.ui.View):
    def __init__(self, database: Database) -> None:
        super().__init__(timeout=None)
        self.database = database

    @discord.ui.button(label="Open private ticket", emoji="🎫", style=discord.ButtonStyle.success, custom_id="nexus:ticket:open")
    async def open_ticket(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        guild = interaction.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This button only works inside a server.", ephemeral=True)
        await interaction.response.defer(ephemeral=True, thinking=True)
        previous = await self.database.open_ticket_for(guild.id, interaction.user.id)
        if previous and guild.get_channel(previous):
            return await interaction.followup.send(f"You already have an open ticket: <#{previous}>.", ephemeral=True)
        category = discord.utils.get(guild.categories, name="🎫 ─ SUPPORT NODE")
        staff = discord.utils.get(guild.roles, name="Support Team")
        if category is None or staff is None:
            return await interaction.followup.send("Ticket system is not configured. Ask an administrator to run /setup.", ephemeral=True)
        safe_name = re.sub(r"[^a-z0-9-]", "", interaction.user.name.lower().replace(" ", "-"))[:30] or "member"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            staff: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True),
        }
        channel = await guild.create_text_channel(f"ticket-{safe_name}", category=category, overwrites=overwrites, reason=f"Ticket opened by {interaction.user}")
        await self.database.create_ticket(channel.id, guild.id, interaction.user.id)
        embed = panel_embed("Support channel established", f"{interaction.user.mention}, describe your request clearly. A support agent will be with you soon.")
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
