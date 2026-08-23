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
        self.wfile.write(b"CyberKernel Enterprise Core v20.0 Active.")
        
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v20.0] | Direct Chat Setup & Secure Roles Active"))

async def schedule_channel_deletion(channel, hours):
    await asyncio.sleep(hours * 3600)
    try:
        await channel.delete()
    except Exception:
        pass

# --- نظام تفاعلي مباشر في الشات لإنشاء الرومات بالاسم والوقت بحرية تامة ---
class RoomConfigView(discord.ui.View):
    def __init__(self, author_id):
        super().__init__(timeout=60)
        self.author_id = author_id
        self.channel_type = "text"
        self.is_hidden = False
        self.hours = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("[ERROR] This configuration session is not for you.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Type: Text", style=discord.ButtonStyle.blurple, emoji="💬")
    async def toggle_type(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.channel_type = "voice" if self.channel_type == "text" else "text"
        button.label = f"Type: {self.channel_type.capitalize()}"
        button.emoji = "🔊" if self.channel_type == "voice" else "💬"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Visibility: Public", style=discord.ButtonStyle.green, emoji="🔓")
    async def toggle_visibility(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.is_hidden = not self.is_hidden
        button.label = "Visibility: Hidden" if self.is_hidden else "Visibility: Public"
        button.style = discord.ButtonStyle.red if self.is_hidden else discord.ButtonStyle.green
        button.emoji = "🔒" if self.is_hidden else "🔓"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Timer: Permanent", style=discord.ButtonStyle.grey, emoji="⏳")
    async def toggle_timer(self, interaction: discord.Interaction, button: discord.ui.Button):
        # تدوير الساعات: 0 -> 1 -> 6 -> 12 -> 24 -> 0
        if self.hours == 0: self.hours = 1
        elif self.hours == 1: self.hours = 6
        elif self.hours == 6: self.hours = 12
        elif self.hours == 12: self.hours = 24
        else: self.hours = 0

        button.label = f"Timer: {self.hours} Hours" if self.hours > 0 else "Timer: Permanent"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Confirm & Create", style=discord.ButtonStyle.success, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("[INPUT] Please type the **name of the channel** in this chat within 30 seconds:", ephemeral=True)
        
        def check(m):
            return m.author.id == self.author_id and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            chan_name = msg.content.strip().lower().replace(" ", "-")
            try:
                await msg.delete()
            except:
                pass

            guild = interaction.guild
            category = discord.utils.get(guild.categories, name="📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")
            if not category:
                category = await guild.create_category("📂 ── [ SECTOR 05 ] DYNAMIC NODES ── 📂")

            if self.channel_type == "text":
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=not self.is_hidden, send_messages=not self.is_hidden),
                    interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
                }
                new_chan = await guild.create_text_channel(name=chan_name, category=category, overwrites=overwrites)
            else:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=not self.is_hidden, connect=not self.is_hidden),
                    interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
                }
                new_chan = await guild.create_voice_channel(name=chan_name, category=category, overwrites=overwrites)

            if self.hours > 0:
                bot.loop.create_task(schedule_channel_deletion(new_chan, self.hours))

            timer_text = f"{self.hours} Hours" if self.hours > 0 else "Permanent"
            await interaction.followup.send(f"[SUCCESS] Node `{new_chan.name}` created successfully! (Type: {self.channel_type.capitalize()} | Visibility: {'Hidden' if self.is_hidden else 'Public'} | Timer: {timer_text})", ephemeral=True)
            try:
                await interaction.message.delete()
            except:
                pass
        except asyncio.TimeoutError:
            await interaction.followup.send("[TIMEOUT] Channel creation cancelled due to inactivity.", ephemeral=True)

class RoomGeneratorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Initialize Custom Node", style=discord.ButtonStyle.green, emoji="⚙️", custom_id="init_custom_node_btn_v20")
    async def init_node(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoomConfigView(interaction.user.id)
        embed = discord.Embed(
            title="⚙️ DYNAMIC NODE CONFIGURATOR",
            description="Configure your node settings using the buttons below, then click **Confirm & Create**:",
            color=0x00E676
        )
        embed.add_field(name="Settings", value="• **Type**: Text / Voice\n• **Visibility**: Public / Hidden\n• **Timer**: Permanent or Hours", inline=False)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# --- نظام Self-Roles الذكي والمضمون ---
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

class SelfRoleButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Get Elite Agent", style=discord.ButtonStyle.green, emoji="⚡", custom_id="role_agent_btn")
    async def get_agent(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="⚡ ── [ ELITE_AGENT ] ── ⚡")
        if not role:
            await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"[SECURITY] Role '{role.name}' revoked.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"[SUCCESS] Role '{role.name}' instantly granted!", ephemeral=True)

    @discord.ui.button(label="Request Security Officer", style=discord.ButtonStyle.blurple, emoji="🛡️", custom_id="role_mod_btn")
    async def request_mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="🛡️ ── [ SECURITY_OFFICER ] ── 🛡️")
        if not role:
            await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.response.send_message("[INFO] You already have this role.", ephemeral=True)
            return

        control_channel = discord.utils.get(interaction.guild.text_channels, name="⚙️・room-control-hub")
        if not control_channel:
            control_channel = discord.utils.get(interaction.guild.text_channels, name="🛠️・admin-console")

        if not control_channel:
            await interaction.response.send_message("[ERROR] Control hub channel missing.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛡️ PENDING ROLE APPROVAL REQUEST",
            description=f"User <@{interaction.user.id}> requested high-clearance role **{role.name}**.\n\nChoose an action:",
            color=0xFF8C00
        )
        await control_channel.send(embed=embed, view=RoleApprovalView(interaction.user, role))
        await interaction.response.send_message("[PENDING] Your request has been sent to the server owner/administrators for approval.", ephemeral=True)

    @discord.ui.button(label="Get Guest Node", style=discord.ButtonStyle.grey, emoji="👤", custom_id="role_guest_btn")
    async def get_guest(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="👤 ── [ GUEST_NODE ] ── 👤")
        if not role:
            await interaction.response.send_message("[ERROR] Role not found. Re-run !setup.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"[SECURITY] Role '{role.name}' revoked.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"[SUCCESS] Role '{role.name}' instantly granted!", ephemeral=True)

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
    status_msg = await ctx.send("[INIT] Deploying CyberKernel Architecture v20.0...")
    
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

        embed = discord.Embed(
            title="SYSTEM DYNAMIC NODE GENERATOR v20.0",
            description="Click below to open the interactive room configurator. You will choose the name, type, visibility, and auto-destruct timer safely without timeouts.",
            color=0x00E676
        )
        embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v20.0")
        await generator_chan.send(embed=embed, view=RoomGeneratorView())

        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        roles_embed = discord.Embed(
            title="ENTERPRISE SELF-ROLES CLEARANCE SYSTEM",
            description="Click the buttons below to manage your clearance roles.\n*Note: High-clearance roles (Security Officer) require administrator approval.*",
            color=0x00E676
        )
        roles_embed.set_footer(text="CYBERKERNEL ROLE MANAGEMENT SYSTEM")
        await roles_chan.send(embed=roles_embed, view=SelfRoleButtonsView())

        await status_msg.edit(content="[SUCCESS] CyberKernel Architecture v20.0 deployed successfully.")

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
