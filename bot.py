import discord
from discord.ext import commands
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberKernel Enterprise Core v19.1 Active.")
        
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v19.1] | Interactive UI Active"))

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
        await interaction.response.send_message(f"```prolog\n[SUCCESS] Text Node '{new_chan.name}' successfully provisioned. Clearance: {'HIDDEN' if is_hidden else 'PUBLIC'}\n```", ephemeral=True)

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
        await interaction.response.send_message(f"```prolog\n[SUCCESS] Voice Node '{new_chan.name}' successfully provisioned. Clearance: {'HIDDEN' if is_hidden else 'PUBLIC'}\n```", ephemeral=True)

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
    status_msg = await ctx.send("```prolog\n[INIT] Deploying CyberKernel Enterprise Architecture v19.1...\n[+] Resetting structure & provisioning dynamic interfaces...\n
