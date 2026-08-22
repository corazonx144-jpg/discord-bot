import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# تشغيل سيرفر ويب وهمي لترضية منصة Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SmartHub Bot is active and running!")

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

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] SYSTEM ONLINE: Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("[-] CORE STATUS: SECURE & ENCRYPTED")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM SECURE] | Type !help"))

# أمر التأسيس التلقائي للسيرفر (Server Setup Command)
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    msg = await ctx.send("```[+] INITIALIZING PROTOCOLS: Building cyber mainframe structure... Please wait.```")
    
    try:
        # 1. فئة النظام الأساسي
        cat1 = await guild.create_category("💻 ── [ 01 ] SYSTEM CORE ── 💻")
        await guild.create_text_channel("terminal-rules", category=cat1)
        await guild.create_text_channel("system-broadcast", category=cat1)
        await guild.create_text_channel("secure-ticket", category=cat1)

        # 2. فئة الشات والنقاشات
        cat2 = await guild.create_category("⚡ ── [ 02 ] MAINFRAME CHAT ── ⚡")
        await guild.create_text_channel("global-network", category=cat2)
        await guild.create_text_channel("bot-terminal", category=cat2)
        await guild.create_text_channel("underground-media", category=cat2)

        # 3. فئة الرومات الصوتية
        cat3 = await guild.create_category("🎧 ── [ 03 ] ENCRYPTED NODES ── 🎧")
        await guild.create_voice_channel("[Node-01] Safe Zone", category=cat3)
        await guild.create_voice_channel("[Node-02] Operations Room", category=cat3)
        await guild.create_voice_channel("[Node-03] Secure Alpha", category=cat3)

        # 4. فئة الإدارة
        cat4 = await guild.create_category("🔒 ── [ 04 ] CONTROL ROOM ── 🔒")
        await guild.create_text_channel("surveillance-logs", category=cat4)
        await guild.create_text_channel("admin-console", category=cat4)

        await msg.edit(content="```[✓] SUCCESS: Mainframe structure deployed successfully, Agent.```")
    except Exception as e:
        await ctx.send(f"```[ERROR] Failed to construct matrix: {e}```")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```[ERROR] Access Denied: You need Administrator privileges to execute mainframe builds.```", delete_after=5)

# ترحيب سيبراني
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "terminal" in channel.name or "welcome" in channel.name or "global" in channel.name:
            embed = discord.Embed(
                title="⚡ [SYSTEM ACCESS GRANTED] ⚡",
                description=f"Welcome to the mainframe, <@{member.id}>.\n\n> *\"The matrix has you now... Make sure your firewall is up.\"*",
                color=0x00FF66
            )
            embed.add_field(name="[+] Target ID", value=f"`{member.name}`", inline=True)
            embed.add_field(name="[+] Security Level", value="`Level 0 - Guest`", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="SMARTHUB CORE SYSTEM v4.0.4", icon_url=bot.user.display_avatar.url)
            
            view = View()
            button = Button(label="Acknowledge Protocols", style=discord.ButtonStyle.green, emoji="🛡️")
            
            async def button_callback(interaction):
                await interaction.response.send_message(f"Access acknowledged by <@{interaction.user.id}>. Welcome aboard, agent.", ephemeral=True)
                
            button.callback = button_callback
            view.add_item(button)
            
            await channel.send(embed=embed, view=view)
            break

# أمر مسح الرسائل
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```[SYSTEM] purged {amount} packets from the sector.```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
