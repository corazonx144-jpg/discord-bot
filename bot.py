from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress

import discord
from aiohttp import web
from discord import app_commands
from dotenv import load_dotenv

from database import Database
from views import CloseTicketView, RoleView, TicketView, VerificationView, panel_embed

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
log = logging.getLogger("nexus")

INTENTS = discord.Intents.default()
INTENTS.guilds = True
INTENTS.members = True


class NexusBot(discord.Client):
    def __init__(self) -> None:
        super().__init__(intents=INTENTS)
        self.tree = app_commands.CommandTree(self)
        self.database = Database()
        self.web_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        await self.database.initialize()
        # Register persistent controls exactly once, before Discord starts dispatching interactions.
        self.add_view(VerificationView())
        self.add_view(RoleView())
        self.add_view(TicketView(self.database))
        self.add_view(CloseTicketView(self.database))
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
        if self.web_runner:
            await self.web_runner.cleanup()
        await super().close()


bot = NexusBot()


def everyone_overwrites(guild: discord.Guild, verified: discord.Role, bot_member: discord.Member) -> dict:
    return {
        guild.default_role: discord.PermissionOverwrite(view_channel=False, connect=False),
        verified: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, connect=True, speak=True),
        bot_member: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, read_message_history=True),
    }


async def ensure_role(guild: discord.Guild, name: str, colour: discord.Colour) -> discord.Role:
    return discord.utils.get(guild.roles, name=name) or await guild.create_role(name=name, colour=colour, reason="Nexus setup")


async def ensure_category(guild: discord.Guild, name: str, overwrites: dict, *legacy_names: str) -> discord.CategoryChannel:
    category = discord.utils.get(guild.categories, name=name)
    if category is None:
        category = next((item for item in guild.categories if item.name in legacy_names), None)
    if category is None:
        category = await guild.create_category(name, overwrites=overwrites, reason="Nexus setup")
    elif category.name != name:
        await category.edit(name=name, reason="Nexus layout naming migration")
    return category


async def ensure_text(category: discord.CategoryChannel, name: str) -> discord.TextChannel:
    channel = discord.utils.get(category.text_channels, name=name)
    if channel is None:
        # A channel created inside a category inherits that category's permissions.
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


@bot.event
async def on_ready() -> None:
    log.info("Online as %s (%s)", bot.user, bot.user.id if bot.user else "unknown")


@bot.tree.command(name="setup", description="Create or repair the Nexus server layout without deleting existing channels.")
@app_commands.guild_only()
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction) -> None:
    if not interaction.user.guild_permissions.administrator or not interaction.guild:
        return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
    guild = interaction.guild
    me = guild.me
    if not me or not me.guild_permissions.manage_channels or not me.guild_permissions.manage_roles:
        return await interaction.response.send_message("I need Manage Channels and Manage Roles before setup can run.", ephemeral=True)
    await interaction.response.defer(ephemeral=True, thinking=True)
    verified = await ensure_role(guild, "Verified", discord.Colour.blurple())
    await ensure_role(guild, "Elite Agent", discord.Colour.gold())
    await ensure_role(guild, "Guest Node", discord.Colour.light_grey())
    await ensure_role(guild, "Support Team", discord.Colour.green())
    protected = everyone_overwrites(guild, verified, me)
    public = {guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=False, read_message_history=True), me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)}

    core = await ensure_category(guild, "🔒 ─ SECTOR 01 │ SYSTEM CORE", public, "🔒 -- [ SECTOR 01 ] SYSTEM CORE")
    verify = await ensure_text(core, "🛡️-verify-access")
    roles = await ensure_text(core, "⚡-select-clearance")
    await ensure_text(core, "📡-broadcasts")

    terminal = await ensure_category(guild, "⚡ ─ SECTOR 02 │ TERMINAL CHAT", protected, "⚡ -- [ SECTOR 02 ] TERMINAL CHAT")
    tickets = await ensure_text(terminal, "🎫-open-a-ticket")
    for name in ("🌐-global-network", "💻-command-shell", "📦-payload-archive"):
        await ensure_text(terminal, name)

    secure = await ensure_category(guild, "🎧 ─ SECTOR 03 │ SECURE NODES", protected)
    for name in ("🔒 Node 01 • Safe Zone", "🛡️ Node 02 • Operations", "⚡ Node 03 • Alpha"):
        await ensure_voice(secure, name)
    await ensure_category(guild, "📁 ─ SECTOR 04 │ INTELLIGENCE ARCHIVE", protected)
    support = await ensure_category(guild, "🎫 ─ SUPPORT NODE", protected)
    await ensure_text(support, "📋-support-protocol")
    control = await ensure_category(guild, "👁️ ─ SECTOR 05 │ CONTROL & LOGS", protected)
    await ensure_text(control, "📊-surveillance-logs")

    await ensure_panel(verify, "verification", panel_embed("Identity gateway", "Verify once to unlock the protected network."), VerificationView())
    await ensure_panel(roles, "roles", panel_embed("Clearance selector", "Choose optional roles. Press again to remove a role."), RoleView())
    await ensure_panel(tickets, "tickets", panel_embed("Support terminal", "Open one private, persistent support ticket."), TicketView(bot.database))
    await interaction.followup.send("Nexus layout is ready. Existing channels were preserved; missing pieces were created.", ephemeral=True)


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
    await interaction.response.send_message(embed=panel_embed("Nexus status", f"Latency: `{round(bot.latency * 1000)} ms`\nDatabase: `online`\nPersistent controls: `armed`"), ephemeral=True)


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


if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN is missing. Add it as a Render environment variable.")
    bot.run(token, log_handler=None)
