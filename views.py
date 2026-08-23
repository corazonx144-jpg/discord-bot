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
    def __init__(self) -> None:
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify identity", emoji="🛡️", style=discord.ButtonStyle.success, custom_id="nexus:verify")
    async def verify(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This button only works inside a server.", ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name="Verified")
        if role is None:
            return await interaction.response.send_message("The server has not been configured. Ask an administrator to run /setup.", ephemeral=True)
        if role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
            return await interaction.response.send_message("I cannot assign the Verified role; move my role above it.", ephemeral=True)
        if role in interaction.user.roles:
            return await interaction.response.send_message("You are already verified.", ephemeral=True)
        await interaction.user.add_roles(role, reason="Nexus self-verification")
        await interaction.response.send_message("Identity verified. Welcome to the network.", ephemeral=True)


class RoleView(discord.ui.View):
    def __init__(self) -> None:
        super().__init__(timeout=None)

    async def toggle(self, interaction: discord.Interaction, role_name: str) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("This button only works inside a server.", ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role is None:
            return await interaction.response.send_message("Run /setup first.", ephemeral=True)
        if role >= interaction.guild.me.top_role:  # type: ignore[union-attr]
            return await interaction.response.send_message("Move my role above this self-role first.", ephemeral=True)
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Nexus self-role toggle")
            message = f"{role_name} removed."
        else:
            await interaction.user.add_roles(role, reason="Nexus self-role toggle")
            message = f"{role_name} activated."
        await interaction.response.send_message(message, ephemeral=True)

    @discord.ui.button(label="Elite agent", emoji="⚡", style=discord.ButtonStyle.primary, custom_id="nexus:role:elite")
    async def elite(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.toggle(interaction, "Elite Agent")

    @discord.ui.button(label="Guest node", emoji="👤", style=discord.ButtonStyle.secondary, custom_id="nexus:role:guest")
    async def guest(self, interaction: discord.Interaction, _: discord.ui.Button) -> None:
        await self.toggle(interaction, "Guest Node")


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
