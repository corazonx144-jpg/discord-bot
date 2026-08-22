import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# سيرفر ويب وهمي لترضية منصة Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberMainframe Enterprise Core v9.0 Active.")

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
    print(f"[-] ENTERPRISE CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[ENTERPRISE MATRIX v9.0] | Type !setup"))

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    status_msg = await ctx.send("```prolog\n[INIT] Deploying Enterprise Cyber-Architecture v9.0...\n[+] Purging old sectors & establishing role hierarchy...\n```")
    
    try:
        # 1. حذف شامل لجميع القنوات والفئات القديمة
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        # 2. إنشاء الرتب السيبرانية تلقائياً (إذا لم تكن موجودة)
        admin_role = discord.utils.get(guild.roles, name="👑 | Root Administrator")
        if not admin_role:
            admin_role = await guild.create_role(name="👑 | Root Administrator", color=discord.Color.from_rgb(255, 50, 50), permissions=discord.Permissions(administrator=True))

        mod_role = discord.utils.get(guild.roles, name="🛡️ | Security Officer")
        if not mod_role:
            mod_role = await guild.create_role(name="🛡️ | Security Officer", color=discord.Color.from_rgb(255, 165, 0), permissions=discord.Permissions(manage_messages=True, kick_members=True, ban_members=True))

        agent_role = discord.utils.get(guild.roles, name="⚡ | Elite Agent")
        if not agent_role:
            agent_role = await guild.create_role(name="⚡ | Elite Agent", color=discord.Color.from_rgb(0, 255, 102))

        guest_role = discord.utils.get(guild.roles, name="👤 | Guest Node")
        if not guest_role:
            guest_role = await guild.create_role(name="👤 | Guest Node", color=discord.Color.from_rgb(150, 150, 150))

        # 3. إعداد صلاحيات الرومات (Permissions Overwrites)
        everyone = guild.default_role

        # صلاحيات للرومات العامة (مرئية للجميع)
        public_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=True, connect=True),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        # صلاحيات لقنوات القراءة فقط (مثل القوانين وشرح الرتب)
        readonly_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_messages=True)
        }

        # صلاحيات لقنوات الإدارة الحصينة (مخفية تماماً عن الأعضاء العاديين)
        admin_only_overwrites = {
            everyone: discord.PermissionOverwrite(read_messages=False),
            admin_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # 4. بناء الهيكل التنظيمي السيبراني الفخم
        # القطاع الأول: التوجيهات
        cat1 = await guild.create_category("🛡️ ── [ SECTOR 01 ] SYSTEM CORE ── 🛡️")
        rules_chan = await guild.create_text_channel("security-directives", category=cat1, overwrites=readonly_overwrites)
        roles_chan = await guild.create_text_channel("role-hierarchy-guide", category=cat1, overwrites=readonly_overwrites)
        await guild.create_text_channel("mainframe-broadcast", category=cat1, overwrites=readonly_overwrites)

        # القطاع الثاني: الشات العام والترحيب
        cat2 = await guild.create_category("⚡ ── [ SECTOR 02 ] MAINFRAME CHAT ── ⚡")
        welcome_chan = await guild.create_text_channel("welcome-terminal", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("global-network", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("command-shell", category=cat2, overwrites=public_overwrites)
        await guild.create_text_channel("underground-media", category=cat2, overwrites=public_overwrites)

        # القطاع الثالث: الغرف الصوتية المشفرة
        cat3 = await guild.create_category("🎧 ── [ SECTOR 03 ] ENCRYPTED NODES ── 🎧")
        await guild.create_voice_channel("🔒 [Node-01] Safe Zone", category=cat3)
        await guild.create_voice_channel("🔒 [Node-02] Operations Room", category=cat3)
        await guild.create_voice_channel("🔒 [Node-03] Secure Alpha", category=cat3)

        # القطاع الرابع: غرفة التحكم والسجلات (خاصة بالإدارة فقط)
        cat4 = await guild.create_category("👁️ ── [ SECTOR 04 ] CONTROL & LOGS ── 👁️")
        await guild.create_text_channel("surveillance-logs", category=cat4, overwrites=admin_only_overwrites)
        await guild.create_text_channel("admin-terminal", category=cat4, overwrites=admin_only_overwrites)

        # 5. إرسال محتوى روم القوانين (Security Directives)
        rules_embed = discord.Embed(
            title="⚡ [ SYSTEM SECURITY PROTOCOLS ] ⚡",
            description="```ini\n[ ACCESS LEVEL: RESTRICTED // ENTERPRISE SECURE ]\nWelcome to the official mainframe enclave. Adherence to core directives is mandatory for all active nodes.\n```",
            color=0x00FF66
        )
        rules_embed.add_field(name="[01] Professional Discipline", value="> Maintain absolute operational discipline and respect across all terminal channels.", inline=False)
        rules_embed.add_field(name="[02] Zero-Leak Policy", value="> Exposing authentication tokens, private keys, or internal telemetry results in immediate isolation.", inline=False)
        rules_embed.add_field(name="[03] Sector Routing", value="> Keep all transmissions strictly bound to their designated operational channels.", inline=False)
        rules_embed.set_footer(text="ENTERPRISE CYBER DEFENSE SYSTEM v9.0")
        await rules_chan.send(embed=rules_embed)

        # 6. إرسال محتوى روم شرح الرتب (Role Hierarchy Guide)
        roles_embed = discord.Embed(
            title="🛡️ [ ENTERPRISE ROLE HIERARCHY & CLEARANCE ] 🛡️",
            description="```yaml\nDetailed breakdown of security clearances and operational roles established within the mainframe network:\n```",
            color=0x00FF66
        )
        roles_embed.add_field(name="👑 | Root Administrator", value="> **Full System Control:** Possesses supreme clearance over infrastructure, role provisioning, security policies, and core mainframe configurations.", inline=False)
        roles_embed.add_field(name="🛡️ | Security Officer", value="> **Operations & Moderation:** Authorized to monitor network traffic, enforce disciplinary actions, handle tickets, and manage channel integrity.", inline=False)
        roles_embed.add_field(name="⚡ | Elite Agent", value="> **Verified Operative:** Granted to active, trusted members with full access to global chat channels, command shell, and encrypted voice nodes.", inline=False)
        roles_embed.add_field(name="👤 | Guest Node", value="> **Unverified Guest:** Default clearance assigned upon initial connection. Limited to public communication channels.", inline=False)
        roles_embed.set_footer(text="MAINFRAME SECURITY ARCHITECTURE // CLEARANCE GUIDE")
        await roles_chan.send(embed=roles_embed)

        await status_msg.edit(content="```prolog\n[SUCCESS] Enterprise Cyber-Architecture v9.0 deployed successfully. All roles, permissions, and channels configured.\n```")

    except Exception as e:
        print(f"Setup Error: {e}")
        await ctx.send(f"```css\n[CRITICAL ERROR] Setup failed: {e}\n```")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```css\n[ERROR] Access Denied: Administrator clearance required to initialize setup.\n```", delete_after=5)

# 7. نظام الترحيب البروفيشنال (Terminal / Code-Block Style فائق النظافة)
@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "welcome" in channel.name:
            # رسالة ترحيبية بتصميم Code-Block تقني بحت وعالي الاحترافية
            welcome_text = (
                f"```ini\n"
                f"[CONNECTION ESTABLISHED]\n"
                f"--------------------------------------------------\n"
                f"Target Agent     : {member.name}\n"
                f"Target UID       : {member.id}\n"
                f"Gateway Proxy    : Secure TLS-1.3 Encrypted\n"
                f"Assigned Role    : 👤 | Guest Node\n"
                f"System Status    : Standby for Handshake\n"
                f"--------------------------------------------------\n"
                f"```\n"
                f"> *\"The grid has registered a new signal. Welcome aboard, agent <@{member.id}>. Review `#role-hierarchy-guide` and `#security-directives` to synchronize with protocol.\"*"
            )
            
            embed = discord.Embed(
                title="⚡ [ SECURE HANDSHAKE // ACCESS GRANTED ] ⚡",
                description=welcome_text,
                color=0x00FF66
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="ENTERPRISE MAINFRAME // SECURE KERNEL v9.0", icon_url=bot.user.display_avatar.url)
            
            view = View()
            button = Button(label="Acknowledge Protocol", style=discord.ButtonStyle.green, emoji="🛡️")
            
            async def button_callback(interaction):
                await interaction.response.send_message(f"```prolog\n[VERIFIED] Agent <@{interaction.user.id}> handshake acknowledged. Welcome to the enterprise network.\n```", ephemeral=True)
                
            button.callback = button_callback
            view.add_item(button)
            
            await channel.send(embed=embed, view=view)
            break

# 8. حماية خرافية ضد الروابط الخارجية
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

# 9. أمر التنظيف السريع
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```prolog\n[SYSTEM] Purged {amount} packets from sector buffer.\n```")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
