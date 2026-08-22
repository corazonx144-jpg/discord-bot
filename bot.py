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
        self.wfile.write(b"CyberKernel Enterprise Core v14.0 Active.")

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
    print(f"[-] CYBERKERNEL CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v14.0] | Type !setup"))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    status_msg = await ctx.send("```prolog\n[INIT] Deploying CyberKernel Enterprise Architecture v14.0...\n[+] Purging old channels, categories, and roles...\n```")
    
    try:
        # 1. حذف شامل لجميع القنوات والفئات القديمة
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        # 2. حذف جميع الرتب القديمة (باستثناء الرتبة الافتراضية @everyone، رتب البوتات، ورتبة صاحب السيرفر)
        for role in list(guild.roles):
            if role != guild.default_role and not role.managed and role < guild.me.top_role:
                try:
                    await role.delete()
                except Exception:
                    pass

        # 3. إنشاء الرتب السيبرانية الجديدة والاحترافية من الصفر
        admin_role = await guild.create_role(name="👑 ── [ ROOT_ADMIN ] ── 👑", color=discord.Color.from_rgb(235, 50, 50), permissions=discord.Permissions(administrator=True))
        mod_role = await guild.create_role(name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️", color=discord.Color.from_rgb(255, 140, 0), permissions=discord.Permissions(manage_messages=True, kick_members=True, ban_members=True))
        agent_role = await guild.create_role(name="⚡ ── [ ELITE_AGENT ] ── ⚡", color=discord.Color.from_rgb(0, 230, 118))
        guest_role = await guild.create_role(name="👤 ── [ GUEST_NODE ] ── 👤", color=discord.Color.from_rgb(140, 140, 140))

        # 4. إعداد صلاحيات الرومات
        everyone = guild.default_role

        public_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        readonly_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        admin_only_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # 5. بناء الهيكل بفئات UPPERCASE وأسماء قنوات lowercase تقنية ونظيفة
        cat1 = await guild.create_category("🔒 ── [ SECTOR 01 ] SYSTEM CORE ── 🔒")
        rules_chan = await guild.create_text_channel("📜・security-directives", category=cat1, overwrites=readonly_overwrites)
        roles_chan = await guild.create_text_channel("🛡️・role-hierarchy-guide", category=cat1, overwrites=readonly_overwrites)
        await guild.create_text_channel("📡・system-broadcast", category=cat1, overwrites=readonly_overwrites)

        cat2 = await guild.create_category("⚡ ── [ SECTOR 02 ] TERMINAL CHAT ── ⚡")
        welcome_chan = await guild.create_text_channel("🔗・connection-terminal", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("🌐・global-network", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("💻・command-shell", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("📂・payload-archive", category=cat2, overwrites=public_overwrites)

        cat3 = await guild.create_category("🎧 ── [ SECTOR 03 ] SECURE NODES ── 🎧")
        await guild.create_voice_channel("🔒 ➔ [Node-01] Safe Zone", category=cat3)
        await guild.create_voice_channel("🔒 ➔ [Node-02] Operations Room", category=cat3)
        await guild.create_voice_channel("🔒 ➔ [Node-03] Secure Alpha", category=cat3)

        cat4 = await guild.create_category("👁️ ── [ SECTOR 04 ] CONTROL & LOGS ── 👁️")
        await guild.create_text_channel("⚠️・surveillance-logs", category=cat4, overwrites=admin_only_overwrites)
        await guild.create_text_channel("⚙️・admin-console", category=cat4, overwrites=admin_only_overwrites)

        # 6. رسالة القوانين الرسمية
        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to the following security directives is mandatory for all active nodes.",
            color=0x00E676
        )
        rules_embed.add_field(name="01. Professional Discipline", value="Maintain absolute tactical discipline and professional conduct across all terminal channels.", inline=False)
        rules_embed.add_field(name="02. Zero-Leak Policy", value="Exposing authentication tokens, keys, or internal telemetry results in immediate node termination.", inline=False)
        rules_embed.add_field(name="03. Sector Routing", value="Keep all communications strictly bound to their designated operational channels.", inline=False)
        rules_embed.set_footer(text="CYBERKERNEL DEFENSE SYSTEM v14.0")
        await rules_chan.send(embed=rules_embed)

        # 7. رسالة شرح الرتب الرسمية
        roles_embed = discord.Embed(
            title="ENTERPRISE ROLE HIERARCHY & CLEARANCE",
            description="Detailed breakdown of security clearances and operational roles established within the system network:",
            color=0x00E676
        )
        roles_embed.add_field(name="👑 ── [ ROOT_ADMIN ]", value="Supreme Control: Possesses full administrative clearance over infrastructure, role provisioning, and core system configurations.", inline=False)
        roles_embed.add_field(name="🛡️ ── [ SECURITY_OFFICER ]", value="Operations & Moderation: Authorized to monitor network traffic, enforce disciplinary protocols, and manage channel integrity.", inline=False)
        roles_embed.add_field(name="⚡ ── [ ELITE_AGENT ]", value="Verified Operative: Granted to trusted active members with full access to global chat channels, command shell, and encrypted nodes.", inline=False)
        roles_embed.add_field(name="👤 ── [ GUEST_NODE ]", value="Unverified Guest: Default clearance assigned upon initial connection. Limited to public communication channels.", inline=False)
        roles_embed.set_footer(text="SYSTEM SECURITY ARCHITECTURE // CLEARANCE GUIDE")
        await roles_chan.send(embed=roles_embed)

        await status_msg.edit(content="```prolog\n[SUCCESS] CyberKernel Enterprise Architecture v14.0 deployed successfully. Old roles & channels purged.\n```")

    except Exception as e:
        print(f"Setup Error: {e}")
        await ctx.send(f"```css\n[CRITICAL ERROR] Setup failed: {e}\n```")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```css\n[ERROR] Access Denied: Administrator clearance required to initialize setup.\n```", delete_after=5)

# 8. نظام الترحيب بستايل الـ Terminal و ASCII Art الاحترافي
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "connection" in channel.name or "welcome" in channel.name:
            
            terminal_banner = (
                "```ini\n"
                "  _       __     __                           \n"
                " | |     / /__  / /________  _      ME  ___     \n"
                " | | /| / / _ \\/ / ___/ __ \\| | /| / / _ \\    \n"
                " | |/ |/ /  __/ / /__/ /_/ /| |/ |/ /  __/    \n"
                " |__/|__/\\___/_/\\___/\\____/ |__/|__/\\___/     \n"
                "                 control panel                \n"
                "==================================================\n"
                "STATUS\n"
                "==================================================\n"
                f"[ OK ] Target Agent  : {member.name}\n"
                f"       UID Assigned  : {member.id}\n"
                f"[ OK ] Gateway Proxy : TLS-1.3 Encrypted\n"
                f"       Assigned Role : 👤 GUEST_NODE\n"
                "\n"
                "==================================================\n"
                "WHAT DO YOU WANT TO DO?\n"
                "==================================================\n"
                "[1] Initialize protocol & sync channels\n"
                "[2] View #security-directives\n"
                "[3] View #role-hierarchy-guide\n"
                "[4] Acknowledge connection handshake\n"
                "```"
            )
            
            await channel.send(f"Welcome agent <@{member.id}> to the mainframe network!\n{terminal_banner}")
            break

# 9. حماية ضد الروابط الخارجية
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if "http://" in message.content or "https://" in message.content or "discord.gg" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                warning = await message.channel.send(f"```css\n[SECURITY BREACH BLOCKED] Unauthorized external transmission detected from <@{message.author.id}>. Packet dropped.\n```")
                await warning.delete(delay=5)
            except Exception:
                pass
            return

    await bot.process_commands(message)

# 10. أمر التنظيف السريع
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```prolog\n[SYSTEM] Purged {amount} packets from sector buffer.\n```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
