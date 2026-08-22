import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# 1. تشغيل سيرفر ويب وهمي لترضية منصة Render
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

# 2. إعدادات البوت والصلاحيات
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] SYSTEM ONLINE: Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("[-] CORE STATUS: SECURE & ENCRYPTED")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM SECURE] | Type !setup"))

# 3. أمر التأسيس الشامل (حذف القديم وبناء النظام السيبراني الإنجليزي بالكامل)
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    msg = await ctx.send("```[!] PURGING SECTORS: Reconstructing the entire mainframe in English...```")
    
    try:
        # مسح جميع القنوات والفئات القديمة نهائياً
        for channel in guild.channels:
            try:
                await channel.delete()
            except Exception:
                pass

        # بناء التصميم السيبراني الإنجليزي بالكامل
        cat1 = await guild.create_category("💻 ── [ 01 ] SYSTEM CORE ── 💻")
        rules_chan = await guild.create_text_channel("terminal-rules", category=cat1)
        await guild.create_text_channel("system-broadcast", category=cat1)
        await guild.create_text_channel("secure-ticket", category=cat1)

        cat2 = await guild.create_category("⚡ ── [ 02 ] MAINFRAME CHAT ── ⚡")
        global_chan = await guild.create_text_channel("global-network", category=cat2)
        await guild.create_text_channel("bot-terminal", category=cat2)
        await guild.create_text_channel("underground-media", category=cat2)

        cat3 = await guild.create_category("🎧 ── [ 03 ] ENCRYPTED NODES ── 🎧")
        await guild.create_voice_channel("[Node-01] Safe Zone", category=cat3)
        await guild.create_voice_channel("[Node-02] Operations Room", category=cat3)
        await guild.create_voice_channel("[Node-03] Secure Alpha", category=cat3)

        cat4 = await guild.create_category("🔒 ── [ 04 ] CONTROL ROOM ── 🔒")
        await guild.create_text_channel("surveillance-logs", category=cat4)
        await guild.create_text_channel("admin-console", category=cat4)

        # إرسال القوانين في الروم المخصص
        rules_embed = discord.Embed(
            title="🛡️ [ SYSTEM SECURITY PROTOCOLS ] 🛡️",
            description="Welcome to the elite mainframe network. Read and acknowledge all directives below to maintain secure access.",
            color=0x00FF66
        )
        rules_embed.add_field(name="[01] Respect & Conduct", value="Maintain professional operational discipline across all channels.", inline=False)
        rules_embed.add_field(name="[02] Security & Privacy", value="Never share confidential tokens, keys, or personal telemetry.", inline=False)
        rules_embed.add_field(name="[03] Channel Utilization", value="Keep discussions strictly bound to designated sector nodes.", inline=False)
        rules_embed.set_footer(text="SMARTHUB DEFENSE SYSTEM v4.0.4")
        await rules_chan.send(embed=rules_embed)

    except Exception as e:
        print(f"Error during setup: {e}")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```[ERROR] Access Denied: Administrator privileges required.```", delete_after=5)

# 4. نظام الترحيب السيبراني التلقائي بالأعضاء الجدد
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "global" in channel.name or "terminal" in channel.name:
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

# 5. نظام الحماية ومراقبة الروابط (Anti-Link)
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if "http://" in message.content or "https://www.discord.gg" in message.content or "discord.com/invite" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                warning = await message.channel.send(f"```[SECURITY WARNING] Unauthorized link transmission detected from <@{message.author.id}>. Packet blocked.```")
                await warning.delete(delay=5)
            except Exception:
                pass
            return

    await bot.process_commands(message)

# 6. أمر مسح الرسائل
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```[SYSTEM] purged {amount} packets from the sector.```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
