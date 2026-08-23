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
        self.wfile.write(b"CyberKernel Enterprise Core v23.0 Active.")
        
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
    bot.add_view(RoleSelectView())
    bot.add_view(RoomConfigSelectView())
    print(f"[-] CYBERKERNEL CORE ONLINE: {bot.user.name}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v23.0] | Dropdown Fresh Cache"))

async def schedule_channel_deletion(channel, hours):
    await asyncio.sleep(hours * 3600)
    try:
        await channel.delete()
    except Exception:
        pass

# --- نافذة إدخال اسم الروم الاحترافية (Modal) ---
class RoomCreationModal(discord.ui.Modal, title="Custom Node Generator"):
    channel_name = discord.ui.TextInput(
        label="Channel Name",
        placeholder="e.g., project-alpha",
        min_length=2,
        max_length=50,
        required=True
    )

    def __init__(self, node_type, visibility, hours):
        super().__init__()
        self.node_type = node_type
        self.visibility = visibility
        self.hours = hours

    async def on_submit(self, interaction: discord.Interaction):
        chan_name = self.channel_name.value.strip().lower().replace(" ", "-")
        guild = interaction.guild
        
        category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
        if not category:
            category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

        is_hidden = (self.visibility == "hidden")

        if self.node_type == "text":
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=not is_hidden, send_messages=not is_hidden),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
            }
            new_chan = await guild.create_text_channel(name=chan_name, category=category, overwrites=overwrites)
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=not is_hidden, connect=not is_hidden),
                interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
            }
            new_chan = await guild.create_voice_channel(name=chan_name, category=category, overwrites=overwrites)

        if self.hours > 0:
            bot.loop.create_task(schedule_channel_deletion(new_chan, self.hours))

        timer_text = f"{self.hours} Hours" if self.hours > 0 else "Permanent"
        await interaction.response.send_message(
            f"[SUCCESS] Node `{new_chan.name}` created successfully!\n• **Type:** {self.node_type.capitalize()}\n• **Visibility:** {self.visibility.capitalize()}\n• **Timer:** {timer_text}",
            ephemeral=True
        )

# --- نظام إعداد الرومات عبر القوائم المنسدلة ---
class RoomConfigSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.node_type = "text"
        self.visibility = "public"
        self.hours = 0

    @discord.ui.select(
        placeholder="💬 Select Channel Type...",
        custom_id="select_node_type_v23",
        options=[
            discord.SelectOption(label="Text Channel", value="text", description="Create a secure text node", emoji="💬"),
            discord.SelectOption(label="Voice Channel", value="voice", description="Create a secure voice node", emoji="🔊")
        ]
    )
    async def select_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.node_type = select.values[0]
        await interaction.response.send_message(f"[CONFIG] Type set to: **{self.node_type.capitalize()}**", ephemeral=True)

    @discord.ui.select(
        placeholder="🔓 Select Visibility...",
        custom_id="select_node_visibility_v23",
        options=[
            discord.SelectOption(label="Public", value="public", description="Visible to everyone", emoji="🔓"),
            discord.SelectOption(label="Hidden", value="hidden", description="Private / Restricted access", emoji="🔒")
        ]
    )
    async def select_visibility(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.visibility = select.values[0]
        await interaction.response.send_message(f"[CONFIG] Visibility set to: **{self.visibility.capitalize()}**", ephemeral=True)

    @discord.ui.select(
        placeholder="⏳ Select Auto-Destruct Timer...",
        custom_id="select_node_timer_v23",
        options=[
            discord.SelectOption(label="Permanent", value="0", description="No auto-deletion", emoji="⏳"),
            discord.SelectOption(label="1 Hour", value="1", description="Deletes after 1 hour", emoji="⏱️"),
            discord.SelectOption(label="6 Hours", value="6", description="Deletes after 6 hours", emoji="⏱️"),
            discord.SelectOption(label="24 Hours", value="24", description="Deletes after 24 hours", emoji="⏱️")
        ]
    )
    async def select_timer(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.hours = int(select.values[0])
        await interaction.response.send_message(f"[CONFIG] Timer set to: **{self.hours} Hours** (0 = Permanent)", ephemeral=True)

    @discord.ui.button(label="🚀 Create Custom Node", style=discord.ButtonStyle.success, emoji="⚙️", custom_id="trigger_node_modal_v23", row=3)
    async def create_node_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoomCreationModal(self.node_type, self.visibility, self.hours)
        await interaction.response.send_modal(modal)

# --- نظام موافقة الأدمين ---
class RoleApprovalView(discord.ui.View):
    def __init__(self, member: discord.Member, role: discord.Role):
        super().__init__(timeout=86400)
        self.member = member
        self.role = role

    @discord.ui.button(label="Approve & Grant", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("[ERROR] Only administrators can approve role requests.", ephemeral=True)
            return
        try:
            await self.member.add_roles(self.role)
            await interaction.response.edit_message(content=f"[APPROVED] Role `{self.role.name}` granted to <@{self.member.id}> by <@{interaction.user.id}>.", view=None)
            try:
                await self.member.send(f"Your request for role `{self.role.name}` in **{interaction.guild.name}** was **Approved**!")
            except:
                pass
        except Exception as e:
            await interaction.response.send_message(f"[ERROR] {e}", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("[ERROR] Only administrators can deny role requests.", ephemeral=True)
            return
        await interaction.response.edit_message(content=f"[DENIED] Role request for `{self.role.name}` denied by <@{interaction.user.id}>.", view=None)
        try:
            await self.member.send(f"Your request for role `{self.role.name}` in **{interaction.guild.name}** was **Denied**.")
        except:
            pass

# --- قائمة اختيار الرتب الاحترافية (Dropdown) مع معرف جديد كلياً ---
class RoleSelectDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Elite Agent", value="agent", description="Instant clearance for active agents", emoji="⚡"),
            discord.SelectOption(label="Guest Node", value="guest", description="Standard guest visitor role", emoji="👤"),
            discord.SelectOption(label="Security Officer", value="mod", description="Request high-clearance moderator role", emoji="🛡️")
        ]
        super().__init__(placeholder="🛡️ Click here to select your clearance role...", min_values=1, max_values=1, options=options, custom_id="role_select_dropdown_v23_fresh")

    async def callback(self, interaction: discord.Interaction):
        val = self.values[0]
        guild = interaction.guild
        
        if val == "agent":
            role = discord.utils.get(guild.roles, name="⚡ ── [ ELITE_AGENT ] ── ⚡")
            if not role:
                await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
                return
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"[SECURITY] Role `{role.name}` revoked.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"[SUCCESS] Role `{role.name}` instantly granted!", ephemeral=True)

        elif val == "guest":
            role = discord.utils.get(guild.roles, name="👤 ── [ GUEST_NODE ] ── 👤")
            if not role:
                await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
                return
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"[SECURITY] Role `{role.name}` revoked.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"[SUCCESS] Role `{role.name}` instantly granted!", ephemeral=True)

        elif val == "mod":
            role = discord.utils.get(guild.roles, name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️")
            if not role:
                await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
                return
            if role in interaction.user.roles:
                await interaction.response.send_message("[INFO] You already have this role.", ephemeral=True)
                return

            control_channel = discord.utils.get(guild.text_channels, name="⚙️・room-control-hub") or discord.utils.get(guild.text_channels, name="🛠️・admin-console")
            if not control_channel:
                await interaction.response.send_message("[ERROR] Control hub channel missing.", ephemeral=True)
                return

            embed = discord.Embed(
                title="🛡️ PENDING ROLE APPROVAL REQUEST",
                description=f"User <@{interaction.user.id}> requested high-clearance role **{role.name}** via Select Menu.\n\nChoose an action:",
                color=0xFF8C00
            )
            await control_channel.send(embed=embed, view=RoleApprovalView(interaction.user, role))
            await interaction.response.send_message("[PENDING] Your request has been sent to the administrators for approval.", ephemeral=True)

class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelectDropdown())

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
    status_msg = await ctx.send("[INIT] Deploying CyberKernel Architecture v23.0...")
    
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
        mod_role = await guild.create_role(name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️", color=discord.Color.from_rgb(255, 140, 0), permissions=discord.Permissions(manage_messages=True, kick_members=True))
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

        generator_embed = discord.Embed(
            title="SYSTEM DYNAMIC NODE GENERATOR v23.0",
            description="Use the interactive dropdown menus below to configure your node properties (Type, Visibility, Timer), then click **🚀 Create Custom Node** to open the naming modal.",
            color=0x00E676
        )
        generator_embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v23.0")
        await generator_chan.send(embed=generator_embed, view=RoomConfigSelectView())

        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        roles_embed = discord.Embed(
            title="ENTERPRISE SELF-ROLES CLEARANCE SYSTEM",
            description="Select your desired operational clearance role from the dropdown menu below.\n*Note: High-clearance roles (Security Officer) require administrator approval.*",
            color=0x00E676
        )
        roles_embed.set_footer(text="CYBERKERNEL ROLE MANAGEMENT SYSTEM")
        await roles_chan.send(embed=roles_embed, view=RoleSelectView())

        await status_msg.edit(content="[SUCCESS] CyberKernel Architecture v23.0 deployed successfully.")

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
async def clear(ctx, amount: int=5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"[SYSTEM] Purged {amount} packets.")
    await msg.delete(delay=3)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
