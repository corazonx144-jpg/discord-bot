import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberMainframe Core v8.0 Active.")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] CYBER CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[CYBERMAINFRAME v8.0] | Type !setup"))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    await ctx.send("```prolog\n[!] OVERRIDE: Executing absolute server wipe and deploying Hacker Terminal v8.0...\n```")
    
    try:
        # حذف إجباري شامل لكل قنوات وفئات السيرفر
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        # بناء الهيكل السيبراني بستايل الهكرز (أسماء رومات وتصاميم مرعبة)
        cat1 = await guild.create_category("🛡️ ── [ ROOT_ACCESS ] ── 🛡️")
        rules_chan = await guild.create_text_channel("🔒-terminal-directives", category=cat1)
        await guild.create_text_channel("📡-encrypted-broadcast", category=cat1)
        await guild.create_text_channel("🎫-violation-tickets", category=cat1)

        cat2 = await guild.create_category("⚡ ── [ MAINFRAME_HUB ] ── ⚡")
        welcome_chan = await guild.create_text_channel("💀-welcome-matrix", category=cat2)
        await guild.create_text_channel("🌐-global-net-chat", category=cat2)
        await guild.create_text_channel("💻-command-shell", category=cat2)
        await guild.create_text_channel("📂-underground-payloads", category=cat2)

        cat3 = await guild.create_category("🎧 ── [ SECURE_NODES ] ── 🎧")
        await guild.create_voice_channel("🔒 [Node-01] Dark Room", category=cat3)
        await guild.create_voice_channel("🔒 [Node-02] Ghost Protocol", category=cat3)
        await guild.create_voice_channel("🔒 [Node-03] Shadow Alpha", category=cat3)

        cat4 = await guild.create_category("👁️ ── [ SYSTEM_LOGS ] ── 👁️")
        await guild.create_text_channel("⚠️-surveillance-logs", category=cat4)
        await guild.create_text_channel("⚙️-admin-console", category=cat4)

        # رسالة القوانين بستايل الهكرز الحقيقي
        rules_embed = discord.Embed(
            title="⚡ [ SYSTEM SECURITY PROTOCOLS // ROOT ACCESS ] ⚡",
            description="```ini\n[ WARNING: UNAUTHORIZED ACCESS IS PUNISHABLE BY PERMANENT BAN ]\nYou have breached the perimeter of the elite mainframe. Comply with all system directives below.\n```",
            color=0x00FF66
        )
        rules_embed.add_field(name="[01] Tactical Discipline", value="> Maintain absolute operational silence and professional conduct.", inline=False)
        rules_embed.add_field(name="[02] Zero Leak Policy", value="> Leaking private tokens, keys, or node telemetry results in instant node termination.", inline=False)
        rules_embed.add_field(name="[03] Packet Routing", value="> Keep all communications strictly bound to their designated sector terminals.", inline=False)
        rules_embed.set_footer(text="CYBERMAINFRAME DEFENSE SYSTEM v8.0")
        await rules_chan.send(embed=rules_embed)

    except Exception as e:
        print(f"Setup Error: {e}")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```css\n[ERROR] Access Denied: Administrator clearance required.\n```", delete_after=5)

# ترحيب هكرز مرترف واحترافي في روم welcome-matrix
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "welcome" in channel.name or "matrix" in channel.name:
            embed = discord.Embed(
                title="💀 [ NEW INTRUDER SIGNAL INTERCEPTED ] 💀",
                description=f"```css\nTarget Node: {member.name}\nProxy IP: Encrypted Gateway\nStatus: Unverified Connection\n```\n> *\"The matrix has absorbed another soul... Establish your firewall immediately, agent <@{member.id}>.\"*",
                color=0x00FF66
            )
            embed.add_field(name="[+] Target UID", value=f"`{member.id}`", inline=True)
            embed.add_field(name="[+] Threat Level", value="`Level 0 - Guest`", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="MAINFRAME SURVEILLANCE // ACCESS GRANTED", icon_url=bot.user.display_avatar.url)
            
            view = View()
            button = Button(label="Acknowledge Handshake", style=discord.ButtonStyle.green, emoji="🛡️")
            
            async def button_callback(interaction):
                await interaction.response.send_message(f"```prolog\n[SUCCESS] Agent <@{interaction.user.id}> handshake verified. Welcome to the grid.\n```", ephemeral=True)
                
            button.callback = button_callback
            view.add_item(button)
            
            await channel.send(embed=embed, view=view)
            break

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if "http://" in message.content or "https://" in message.content or "discord.gg" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                warning = await message.channel.send(f"```css\n[SECURITY BREACH] External link transmission blocked from <@{message.author.id}>. Packet dropped.\n```")
                await warning.delete(delay=5)
            except Exception:
                pass
            return

    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```prolog\n[SYSTEM] Purged {amount} packets from mainframe memory.\n```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
