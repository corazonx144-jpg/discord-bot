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
        self.wfile.write(b"CyberKernel Enterprise Core v19.5 Active.")
        
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v19.5] | Smart Dropdowns Active"))

# --- دالة مؤقت الحذف التلقائي للرومات بناءً على الوقت المحدد ---
async def schedule_channel_deletion(channel, hours):
    await asyncio.sleep(hours * 3600)
    try:
        await channel.delete()
    except Exception:
        pass

# --- قوائم اختيار تفاعلية (Select Menus) لخصائص الروم ---
class RoomConfigSelect(discord.ui.Select):
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        options = [
            discord.SelectOption(label="Public (Visible to All)", description="Standard public node accessible by everyone", emoji="🌐", value="public"),
            discord.SelectOption(label="Hidden (Private / Locked)", description="Encrypted private node restricted access", emoji="🔒", value="hidden")
        ]
        super().__init__(placeholder="Select Node Security Visibility...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        visibility = self.values[0]
        # الانتقال للخطوة التالية وهي اختيار المؤقت الزمني
        view = TimerConfigView(self.channel_type, visibility)
        await interaction.response.edit_message(content=f"```prolog\n[CONFIG] Visibility set to: {visibility.upper()}\n[+] Now select the auto-destruct timer duration:\n```", view=view)

class RoomConfigView(discord.ui.View):
    def __init__(self, channel_type: str, visibility: str):
        super().__init__(timeout=180)
        self.add_item(RoomConfigSelect(channel_type))

class TimerSelect(discord.ui.Select):
    def __init__(self, channel_type: str, visibility: str):
        self.channel_type = channel_type
        self.visibility = visibility
        options = [
            discord.SelectOption(label="1 Hour", description="Auto-destruct after 1 hour", emoji="⏳", value="1"),
            discord.SelectOption(label="6 Hours", description="Auto-destruct after 6 hours", emoji="⏳", value="6"),
            discord.SelectOption(label="24 Hours (1 Day)", description="Auto-destruct after 24 hours", emoji="⏳", value="24"),
            discord.SelectOption(label="Permanent (No Timer)", description="Stays until manually or empty-purged", emoji="♾️", value="0")
        ]
        super().__init__(placeholder="Select Auto-Destruct Timer...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        hours = int(self.values[0])
        modal = CreateNodeModal(self.channel_type, self.visibility, hours)
        await interaction.response.send_modal(modal)

class TimerConfigView(discord.ui.View):
    def __init__(self, channel_type: str, visibility: str):
        super().__init__(timeout=180)
        self.add_item(TimerSelect(channel_type, visibility))

# --- نافذة كتابة اسم الروم النهائية ---
class CreateNodeModal(discord.ui.Modal):
    def __init__(self, channel_type: str, visibility: str, hours: int):
        self.channel_type = channel_type
        self.visibility = visibility
        self.hours = hours
        title = "Initialize Text Node" if channel_type == "text" else "Initialize Voice Node"
        super().__init__(title=title)

        self.channel_name = discord.ui.TextInput(
            label="Node Designation (Name)",
            placeholder="e.g., tactical-ops",
            required=True,
            max_length=50
        )

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
        if not category:
            category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        is_hidden = self.visibility == "hidden"
        
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

        # تفعيل المؤقت الزمني إذا لم يكن 0
        if self.hours > 0:
            bot.loop.create_task(schedule_channel_deletion(new_chan, self.hours))

        timer_text = f"{self.hours} Hours" if self.hours > 0 else "Permanent"
        await interaction.response.send_message(f"[SUCCESS] {self.channel_type.capitalize()} Node '{new_chan.name}' provisioned successfully! (Visibility: {self.visibility.upper()} | Timer: {timer_text})", ephemeral=True)

# --- لوحة التحكم والأزرار الرئيسية ---
class RoomGeneratorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Text Node", style=discord.ButtonStyle.green, emoji="💬", custom_id="create_text_btn")
    async def create_text_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoomConfigView("text", "public")
        await interaction.response.send_message("```prolog\n[PANEL] Configure Text Node parameters below:\n```", view=view, ephemeral=True)

    @discord.ui.button(label="Create Voice Node", style=discord.ButtonStyle.blurple, emoji="🔊", custom_id="create_voice_btn")
    async def create_voice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoomConfigView("voice", "public")
        await interaction.response.send_message("```prolog\n[PANEL] Configure Voice Node parameters below:\n```", view=view, ephemeral=True)

# --- الحذف الفوري للرومات الصوتية عند خروج آخر مستخدم ---
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
    status_msg = await ctx.send("[INIT] Deploying CyberKernel Architecture v19.5...")
    
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

        embed = discord.Embed(
            title="SYSTEM DYNAMIC NODE GENERATOR v19.5",
            description="Use the interactive menus below to provision custom channels with advanced security visibility and custom auto-destruct timers.\n\n• **Green Button**: Create Text Node\n• **Blue Button**: Create Voice Node",
            color=0x00E676
        )
        embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v19.5")
        await generator_chan.send(embed=embed, view=RoomGeneratorView())

        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        roles_embed = discord.Embed(
            title="ENTERPRISE ROLE HIERARCHY & CLEARANCE",
            description="Detailed breakdown of security clearances and operational roles established within the system network.",
            color=0x00E676
        )
        await roles_chan.send(embed=roles_embed)

        await status_msg.edit(content="[SUCCESS] CyberKernel Architecture v19.5 deployed successfully.")

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
