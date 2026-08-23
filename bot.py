import discord
from discord.ext import commands
import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberKernel Enterprise Core v19.6 Active.")
        
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

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
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] CYBERKERNEL CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v19.6] | Unified Modals & Self-Roles Active"))

# --- دالة حذف الرومات تلقائياً بعد انتهاء المؤقت ---
async def schedule_channel_deletion(channel, hours):
    await asyncio.sleep(hours * 3600)
    try:
        await channel.delete()
    except Exception:
        pass

# --- نافذة موحدة سريعة لإنشاء الرومات (تمنع حدوث الـ Timeout) ---
class UnifiedCreateNodeModal(discord.ui.Modal):
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        title = "Initialize Text Node" if channel_type == "text" else "Initialize Voice Node"
        super().__init__(title=title)

        self.channel_name = discord.ui.TextInput(
            label="Node Designation (Name)",
            placeholder="e.g., operations-alpha",
            required=True,
            max_length=50
        )
        self.visibility = discord.ui.TextInput(
            label="Visibility (public / hidden)",
            placeholder="Type 'public' or 'hidden'",
            default="public",
            required=True,
            max_length=10
        )
        self.timer_hours = discord.ui.TextInput(
            label="Auto-Destruct Timer (Hours / 0 for None)",
            placeholder="Type hours e.g. 1, 6, 24 or 0",
            default="0",
            required=True,
            max_length=3
        )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
        if not category:
            category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        is_hidden = self.visibility.value.strip().lower() == "hidden"
        try:
            hours = int(self.timer_hours.value.strip())
        except ValueError:
            hours = 0

        if self.channel_type == "text":
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=not is_hidden, send_messages=not is_hidden),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

            new_chan = await guild.create_text_channel(name=self.channel_name.value, category=category, overwrites=overwrites)
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=not is_hidden, connect=not is_hidden),
                interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
            }
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)

            new_chan = await guild.create_voice_channel(name=self.channel_name.value, category=category, overwrites=overwrites)

        if hours > 0:
            bot.loop.create_task(schedule_channel_deletion(new_chan, hours))

        timer_str = f"{hours} Hours" if hours > 0 else "Permanent"
        await interaction.response.send_message(f"[SUCCESS] {self.channel_type.capitalize()} Node '{new_chan.name}' provisioned! (Visibility: {'HIDDEN' if is_hidden else 'PUBLIC'} | Timer: {timer_str})", ephemeral=True)

# --- أزرار إنشاء الرومات ---
class RoomGeneratorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Text Node", style=discord.ButtonStyle.green, emoji="💬", custom_id="create_text_btn")
    async def create_text_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnifiedCreateNodeModal("text"))

    @discord.ui.button(label="Create Voice Node", style=discord.ButtonStyle.blurple, emoji="🔊", custom_id="create_voice_btn")
    async def create_voice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UnifiedCreateNodeModal("voice"))

# --- نظام Self-Roles الاحترافي (اختيار الرتب عبر قائمة منسدلة) ---
class SelfRoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Elite Agent", description="Receive the Elite Agent clearance role", emoji="⚡", value="agent"),
            discord.SelectOption(label="Security Officer", description="Receive the Security Officer clearance role", emoji="🛡️", value="mod"),
            discord.SelectOption(label="Guest Node", description="Receive the Guest Node clearance role", emoji="👤", value="guest")
        ]
        super().__init__(placeholder="Select your operational clearance role...", min_values=1, max_values=1, options=options, custom_id="self_role_select")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        member = interaction.user
        selected_val = self.values[0]

        role_name_map = {
            "agent": "⚡ ── [ ELITE_AGENT ] ── ⚡",
            "mod": "🛡️ ── [ SECURITY_OFFICER ] ── 🛡️",
            "guest": "👤 ── [ GUEST_NODE ] ── 👤"
        }

        target_role_name = role_name_map.get(selected_val)
        role = discord.utils.get(guild.roles, name=target_role_name)

        if not role:
            await interaction.response.send_message("[ERROR] Specified role not found in system database.", ephemeral=True)
            return

        # تبديل الرتبة (إذا كانت عنده تزال، وإذا لم تكن عنده تضاف)
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"[SECURITY] Role '{role.name}' has been revoked.", ephemeral=True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"[SUCCESS] Role '{role.name}' has been granted to your profile.", ephemeral=True)

class SelfRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect())

# --- الحذف الفوري للرومات الصوتية الفارغة ---
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel and before.channel != after.channel:
        category = before.channel.category
        if category and "SECTOR 05" in category.name:
            if len(before.channel.members) == 0:
                try:
                    await before.channel.delete()
                except Exception:
                    pass

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    status_msg = await ctx.send("[INIT] Deploying CyberKernel Architecture v19.6...")
    
    try:
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        for role in list(guild.roles):
            if role != guild.default_role and not role.managed and role != guild.me.top_role and role.position < guild.me.top_role.position:
                try:
                    await role.delete()
                except Exception:
                    pass

        admin_role = await guild.create_role(name="👑 ── [ ROOT_ADMIN ] ── 👑", color=discord.Color.from_rgb(235, 50, 50), permissions=discord.Permissions(administrator=True))
        mod_role = await guild.create_role(name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️", color=discord.Color.from_rgb(255, 140, 0), permissions=discord.Permissions(manage_messages=True, kick_members=True, ban_members=True))
        agent_role = await guild.create_role(name="⚡ ── [ ELITE_AGENT ] ── ⚡", color=discord.Color.from_rgb(0, 230, 118))
        guest_role = await guild.create_role(name="👤 ── [ GUEST_NODE ] ── 👤", color=discord.Color.from_rgb(140, 140, 140))

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

        generator_cat = await guild.create_category("🎛️ ── [ SECTOR 04 ] ROOM GENERATOR ── 🎛️")
        generator_chan = await guild.create_text_channel("🎛️・room-generator", category=generator_cat, overwrites=public_overwrites)

        await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        cat_admin = await guild.create_category("👁️ ── [ SECTOR 06 ] CONTROL & LOGS ── 👁️", overwrites=admin_only_overwrites)
        await guild.create_text_channel("⚙️・room-control-hub", category=cat_admin, overwrites=admin_only_overwrites)
        await guild.create_text_channel("⚠️・surveillance-logs", category=cat_admin, overwrites=admin_only_overwrites)
        await guild.create_text_channel("🛠️・admin-console", category=cat_admin, overwrites=admin_only_overwrites)

        # رسالة إنشاء الرومات
        embed = discord.Embed(
            title="SYSTEM DYNAMIC NODE GENERATOR v19.6",
            description="Use the control buttons below to provision custom channels instantly with integrated visibility and auto-destruct timers.\n\n• **Green Button**: Create Text Node\n• **Blue Button**: Create Voice Node",
            color=0x00E676
        )
        embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v19.6")
        await generator_chan.send(embed=embed, view=RoomGeneratorView())

        # رسالة قواعد السيرفر
        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        # رسالة Self-Roles في قناة الأرصاد أو الرتب
        roles_embed = discord.Embed(
            title="ENTERPRISE SELF-ROLES CLEARANCE SYSTEM",
            description="Select your desired operational clearance role from the interactive dropdown menu below to instantly assign or revoke permissions:",
            color=0x00E676
        )
        roles_embed.set_footer(text="CYBERKERNEL ROLE MANAGEMENT SYSTEM")
        await roles_chan.send(embed=roles_embed, view=SelfRoleView())

        await status_msg.edit(content="[SUCCESS] CyberKernel Architecture v19.6 deployed successfully.")

    except Exception as e:
        print(f"Setup Error: {e}")
        await ctx.send(f"[CRITICAL ERROR] Setup failed: {e}")

@setup.error
async def setup_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("[ERROR] Access Denied: Administrator clearance required.", delete_after=5)

@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "connection" in channel.name or "welcome" in channel.name:
            await channel.send(f"Welcome agent <@{member.id}> to the mainframe network!")
            break

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if "http://" in message.content or "https://" in message.content or "discord.gg" in message.content:
        if not message.author.guild_permissions.administrator:
            try:
                await message.delete()
                warning = await message.channel.send(f"[SECURITY BREACH] Unauthorized external transmission dropped for <@{message.author.id}>.")
                await warning.delete(delay=5)
            except Exception:
                pass
            return
    await bot.process_commands(message)

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"[SYSTEM] Purged {amount} packets.")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
