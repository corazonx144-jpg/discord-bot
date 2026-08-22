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
        self.wfile.write(b"CyberMainframe Core v5.0 Active.")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# 2. إعدادات البوت
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] CYBER CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SECURE TERMINAL] | Type !setup"))

# 3. أمر التأسيس الاحترافي (حذف كامل وبناء الهيكل السيبراني الخالص)
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    await ctx.send("```prolog\n[!] INITIATING SYSTEM PURGE: Erasing legacy sectors and deploying Cyber-Mainframe v5.0...\n```")
    
    try:
        # حذف جميع الرومات والفئات القديمة دون استثناء
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        # بناء الهيكل الاحترافي الجديد بالكامل (إنجليزي سيبراني بحت)
        cat1 = await guild.create_category("🛡️ ── [ SECTOR 01 ] SYSTEM ROOT ── 🛡️")
        rules_chan = await guild.create_text_channel("🔒--security-directives", category=cat1)
        await guild.create_text_channel("📡--mainframe-broadcast", category=cat1)
        await guild.create_text_channel("🎫--secure-ticket-desk", category=cat1)

        cat2 = await guild.create_category("⚡ ── [ SECTOR 02 ] MAINFRAME CHAT ── ⚡")
        welcome_chan = await guild.create_text_channel(" [+]--welcome-terminal", category=cat2)
        await guild.create_text_channel("🌐--global-network", category=cat2)
        await guild.create_text_channel("💻--bot-console", category=cat2)
        await guild.create_text_channel("📂--underground-media", category=cat2)

        cat3 = await guild.create_category("🎧 ── [ SECTOR 03 ] ENCRYPTED NODES ── 🎧")
        await guild.create_voice_channel("🔒 [Node-01] Secure Alpha", category=cat3)
        await guild.create_voice_channel("🔒 [Node-02] Operations Room", category=cat3)
        await guild.create_voice_channel("🔒 [Node-03] Ghost Protocol", category=cat3)

        cat4 = await guild.create_category("👁️ ── [ SECTOR 04 ] CONTROL & LOGS ── 👁️")
        await guild.create_text_channel("⚠️--surveillance-logs", category=cat4)
        await guild.create_text_channel("⚙️--admin-terminal", category=cat4)

        # رسالة القوانين السيبرانية الاحترافية
        rules_embed = discord.Embed(
            title="⚡ [ SYSTEM SECURITY DIRECTIVES v5.0 ] ⚡",
            description="```ini\n[ ACCESS LEVEL: RESTRICTED ]\nWelcome to the elite mainframe network. Comply with all directives below to prevent system isolation.\n```",
            color=0x00FF66
        )
        rules_embed.add_field(name="[01] Operational Discipline", value="> Maintain strict professional conduct across all terminal sectors.", inline=False)
        rules_embed.add_field(name="[02] Data Privacy & Encryption", value="> Never leak authentication tokens, private keys, or personal telemetry.", inline=False)
        rules_embed.add_field(name="[03] Sector Routing", value="> Keep all transmissions bound to their respective designated channels.", inline=False)
        rules_embed.set_footer(text="MAINFRAME SECURITY DEFENSE | SECURE ENCLAVE")
        await rules_chan.send(embed=rules_embed)

    except Exception as e:
        print(f"Setup Error: {e}")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```css\n[ERROR] Access Denied: Administrator clearance required.\n```", delete_after=5)

# 4. نظام الترحيب السيبراني الهكرز الاحترافي (Matrix Style)
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "welcome" in channel.name:
            embed = discord.Embed(
                title="🔓 [ NEW AGENT CONNECTION DETECTED ] 🔓",
                description=f"```css\nTarget Connected: {member.name}\nIP Routing: Secure Proxy\nStatus: Unverified Node\n```\n> *\"The matrix has absorbed another signal... Ensure your firewall is active, agent <@{member.id}>.\"*",
                color=0x00FF66
            )
            embed.add_field(name="[+] Target UID", value=f"`{member.id}`", inline=True)
            embed.add_field(name="[+] Security Clearance", value="`Level 0 - Guest`", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="CYBERMAINFRAME CORE V5.0 // AUTHENTICATED", icon_url=bot.user.display_avatar.url)
            
            view = View()
            button = Button(label="Acknowledge Protocols & Sync", style=discord.ButtonStyle.green, emoji="🛡️")
            
            async def button_callback(interaction):
                await interaction.response.send_message(f"```prolog\n[SUCCESS] Agent <@{interaction.user.id}> has successfully synchronized with the network mainframe.\n```", ephemeral=True)
                
            button.callback = button_callback
            view.add_item(button)
            
            await channel.send(embed=embed, view=view)
            break

# 5. نظام الحماية ضد الروابط والسبام
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if "http://" in message.content or "https://" in message.content or "discord.gg" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                warning = await message.channel.send(f"```css\n[SECURITY BREACH BLOCKED] Unauthorized transmission link intercepted from <@{message.author.id}>. Packet dropped.\n```")
                await warning.delete(delay=5)
            except Exception:
                pass
            return

    await bot.process_commands(message)

# 6. أمر التنظيف السريع
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```prolog\n[SYSTEM] Purged {amount} encrypted packets from sector buffer.\n```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
