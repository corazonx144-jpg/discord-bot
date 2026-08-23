import discord
from discord.ext import commands
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberKernel Enterprise Core v19.2 Active.")
        
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

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] CYBERKERNEL CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v19.2] | Interactive UI Active"))

# --- نافذة منبثقة (Modal) لإنشاء الروم الكتابي ---
class CreateTextModal(discord.ui.Modal, title="Initialize Text Node"):
    channel_name = discord.ui.TextInput(
        label="Node Designation (Name)",
        placeholder="e.g., tactical-ops",
        required=True,
        max_length=50
    )
    visibility = discord.ui.TextInput(
        label="Visibility (public / hidden)",
        placeholder="Type 'hidden' or 'public'",
        default="public",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
        if not category:
            category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        is_hidden = self.visibility.value.strip().lower() == "hidden"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=not is_hidden, send_messages=not is_hidden),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)

        new_chan = await guild.create_text_channel(name=self.channel_name.value, category=category, overwrites=overwrites)
        await interaction.response.send_message(f"```prolog\n[SUCCESS] Text Node '{new_chan.name}' successfully provisioned.\n```", ephemeral=True)

# --- نافذة منبثقة (Modal) لإنشاء الروم الصوتي ---
class CreateVoiceModal(discord.ui.Modal, title="Initialize Voice Node"):
    channel_name = discord.ui.TextInput(
        label="Voice Node Designation (Name)",
        placeholder="e.g., Squad Alpha",
        required=True,
        max_length=50
    )
    visibility = discord.ui.TextInput(
        label="Visibility (public / hidden)",
        placeholder="Type 'hidden' or 'public'",
        default="public",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
        if not category:
            category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        is_hidden = self.visibility.value.strip().lower() == "hidden"
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=not is_hidden, connect=not is_hidden),
            interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)

        new_chan = await guild.create_voice_channel(name=self.channel_name.value, category=category, overwrites=overwrites)
        await interaction.response.send_message(f"```prolog\n[SUCCESS] Voice Node '{new_chan.name}' successfully provisioned.\n```", ephemeral=True)

# --- الأزرار التفاعلية للتحكم ---
class RoomGeneratorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Text Node", style=discord.ButtonStyle.green, emoji="💬", custom_id="create_text_btn")
    async def create_text_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateTextModal())

    @discord.ui.button(label="Create Voice Node", style=discord.ButtonStyle.blurple, emoji="🔊", custom_id="create_voice_btn")
    async def create_voice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(CreateVoiceModal())

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    status_msg = await ctx.send("```prolog\n[INIT] Deploying CyberKernel Enterprise Architecture v19.2...\n```")
    
    try:
        # 1. حذف القنوات القديمة
        for channel in list(guild.channels):
            try:
                await channel.delete()
            except Exception:
                pass

        # 2. حذف الرتب القديمة
        for role in list(guild.roles):
            if role != guild.default_role and not role.managed and role != guild.me.top_role and role.position < guild.me.top_role.position:
                try:
                    await role.delete()
                except Exception:
                    pass

        # 3. إنشاء الرتب
        admin_role = await guild.create_role(name="👑 ── [ ROOT_ADMIN ] ── 👑", color=discord.Color.from_rgb(235, 50, 50), permissions=discord.Permissions(administrator=True))
        mod_role = await guild.create_role(name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️", color=discord.Color.from_rgb(255, 140, 0), permissions=discord.Permissions(manage_messages=True, kick_members=True, ban_members=True))
        agent_role = await guild.create_role(name="⚡ ── [ ELITE_AGENT ] ── ⚡", color=discord.Color.from_rgb(0, 230, 118))
        guest_role = await guild.create_role(name="👤 ── [ GUEST_NODE ] ── 👤", color=discord.Color.from_rgb(140, 140, 140))

        # 4. إعداد الصلاحيات
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

        # 5. بناء الأقسام والشانلز
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

        embed = discord.Embed(
            title="SYSTEM DYNAMIC NODE GENERATOR",
            description="Use the control interface below to provision a custom text or voice channel instantly.\n\n• **Green Button**: Create Text Channel\n• **Blue Button**: Create Voice Channel",
            color=0x00E676
        )
        embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v19.2")
        await generator_chan.send(embed=embed, view=RoomGeneratorView())

        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        roles_embed = discord.Embed(
            title="ENTERPRISE ROLE HIERARCHY & CLEARANCE",
            description="Detailed breakdown of security clearances and operational roles established within the system network:",
            color=0x00E676
        )
        await roles_chan.send(embed=roles_embed)

        await status_msg.edit(content="```prolog\n
