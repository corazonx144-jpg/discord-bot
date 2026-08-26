import os
import asyncio
import discord
from discord.ext import commands, tasks
from aiohttp import web

import database
import views

# Initialize SQLite Schema
database.init_db()

# Intents Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Buffer for voice XP updates (Prevents Database Rate Limiting)
voice_xp_buffer = {}

# 1. Background Voice XP Loop
@tasks.loop(minutes=2)
async def update_voice_xp():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if not member.bot:
                    voice_xp_buffer[member.id] = voice_xp_buffer.get(member.id, 0) + 10
    
    if voice_xp_buffer:
        database.batch_add_xp(voice_xp_buffer)
        voice_xp_buffer.clear()

# 2. Event: Bot Ready & Persistent Views Synchronization
@bot.event
async def on_ready():
    print("=========================================")
    print(f"[NEXUS OS] Logged in as: {bot.user.name}")
    print(f"[NEXUS OS] System Status: ONLINE")
    print("=========================================")
    
    # Register Persistent Views so buttons remain functional after restart
    bot.add_view(views.VerifyView())
    bot.add_view(views.TicketLaunchView())
    bot.add_view(views.TicketControlView())

    try:
        synced = await bot.tree.sync()
        print(f"[NEXUS OS] Synced {len(synced)} Slash Commands.")
    except Exception as e:
        print(f"[ERROR] Failed to sync commands: {e}")

    if not update_voice_xp.is_running():
        update_voice_xp.start()

# 3. Event: Cyberpunk Welcome Log & Anti-Raid Protocol
@bot.event
async def on_member_join(member):
    # Check Anti-Raid Status
    if database.get_raid_mode(member.guild.id):
        try:
            await member.send("```yaml\n[REJECTED] Server is currently under LOCKDOWN protocol. Access denied.\n```")
            await member.kick(reason="Anti-Raid Lockdown Active")
            return
        except Exception:
            pass

    # Terminal Style Welcome Log
    arrival_channel = discord.utils.get(member.guild.text_channels, name="⚡-arrival-terminal")
    if arrival_channel:
        embed = discord.Embed(
            title="[!] UNKNOWN ENTITY DETECTED",
            description=(
                f"```yaml\n"
                f"Trace IP: 192.168.0.{member.id % 255}\n"
                f"Identity: {member.name}\n"
                f"Status: INTRUSION SUCCESSFUL\n"
                f"```\n"
                f"Welcome {member.mention} to the grid. Head over to `#verify-access` to authorize clearance."
            ),
            color=discord.Color.green()
        )
        await arrival_channel.send(embed=embed)

# 4. Event: Auto-Create and Dynamic Clean Voice Channels
@bot.event
async def on_voice_state_update(member, before, after):
    # Auto-Create Temporary Voice Channel
    if after.channel and "create-node" in after.channel.name.lower():
        category = after.channel.category
        new_channel = await member.guild.create_voice_channel(
            name=f"🔒-{member.name}'s-node",
            category=category
        )
        await member.move_to(new_channel)

    # Clean Up Empty Temporary Voice Channels
    if before.channel and "node" in before.channel.name.lower() and len(before.channel.members) == 0:
        if before.channel.name not in ["net_00_safe_zone", "net_01_black_ops"]:
            try:
                await before.channel.delete(reason="Empty temporary node auto-purged")
            except Exception:
                pass

# 5. Webhook Health Server (Render 24/7 Deployment Keep-Alive)
async def handle_ping(request):
    return web.Response(text="NEXUS CORE: OPERATIONAL", status=200)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# Main Async Entrypoint
async def main():
    async with bot:
        await bot.load_extension("admin_cog")
        await asyncio.gather(
            start_web_server(),
            bot.start(os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE"))
        )

if __name__ == "__main__":
    asyncio.run(main())