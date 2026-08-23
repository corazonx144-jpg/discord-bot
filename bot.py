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
        self.wfile.write(b"CyberKernel Enterprise Core v19.7 Active.")
        
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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM KERNEL v19.7] | Smart Approval & Fast Nodes Active"))

async def schedule_channel_deletion(channel, hours):
    await asyncio.sleep(hours * 3600)
    try:
        await channel.delete()
    except Exception:
        pass

# --- نافذة سريعة جداً لإنشاء الرومات (تمنع الـ Timeout) ---
class FastCreateNodeModal(discord.ui.Modal):
    def __init__(self, channel_type: str):
        self.channel_type = channel_type
        super().__init__(title=f"Create {channel_type.capitalize()} Node")

        self.channel_name = discord.ui.TextInput(
            label="Node Name",
            placeholder="e.g. operations-room",
            required=True,
            max_length=50
        )
        self.visibility = discord.ui.TextInput(
            label="Visibility (public / hidden)",
            placeholder="public or hidden",
            default="public",
            required=True,
            max_length=10
        )
        self.timer_hours = discord.ui.TextInput(
            label="Auto-Destruct Hours (0 for Permanent)",
            placeholder="0, 1, 6, 24",
            default="0",
            required=True,
            max_length=3
        )

    async def on_submit(self, interaction: discord.Interaction):
        # الاستجابة الفورية لمنع الـ Timeout
        await interaction.response.defer(ephemeral=True)
        
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
            new_chan = await guild.create_text_channel(name=self.channel_name.value, category=category, overwrites=overwrites)
        else:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=not is_hidden, connect=not is_hidden),
                interaction.user: discord.PermissionOverwrite(view_channel=True, connect=True, manage_channels=True)
            }
            new_chan = await guild.create_voice_channel(name=self.channel_name.value, category=category, overwrites=overwrites)

        if hours > 0:
            bot.loop.create_task(schedule_channel_deletion(new_chan, hours))

        timer_str = f"{hours} Hours" if hours > 0 else "Permanent"
        await interaction.followup.send(f"[SUCCESS] {self.channel_type.capitalize()} Node '{new_chan.name}' provisioned! (Visibility: {'HIDDEN' if is_hidden else 'PUBLIC'} | Timer: {timer_str})", ephemeral=True)

class RoomGeneratorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Text Node", style=discord.ButtonStyle.green, emoji="💬", custom_id="create_text_btn_v2")
    async def create_text_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FastCreateNodeModal("text"))

    @discord.ui.button(label="Create Voice Node", style=discord.ButtonStyle.blurple, emoji="🔊", custom_id="create_voice_btn_v2")
    async def create_voice_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(FastCreateNodeModal("voice"))

# --- نظام Self-Roles الذكي مع طلب الموافقة (Approval) للرتب الخطيرة ---
class RoleApprovalView(discord.ui.View):
    def __init__(self, member: discord.Member, role: discord.Role):
        super().__init__(timeout=86400) # صالح لمدة 24 ساعة
        self.member = member
        self.role = role

    @discord.ui.button(label="Approve & Grant", style=discord.ButtonStyle.green, emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("[ERROR] Only administrators can approve role requests.", ephemeral=True)
            return
        
        try:
            await self.member.add_roles(self.role)
            await interaction.response.edit_message(content=f"[APPROVED] Role `{self.role.name}` has been successfully granted to <@{self.member.id}> by <@{interaction.user.id}>.", view=None)
            try:
                await self.member.send(f"Your request for role `{self.role.name}` in **{interaction.guild.name}** has been **Approved**!")
            except:
                pass
        except Exception as e:
            await interaction.response.send_message(f"[ERROR] Failed to grant role: {e}", ephemeral=True)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, emoji="❌")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("[ERROR] Only administrators can deny role requests.", ephemeral=True)
            return

        await interaction.response.edit_message(content=f"[DENIED] Role request for `{self.role.name}` for <@{self.member.id}> was denied by <@{interaction.user.id}>.", view=None)
        try:
            await self.member.send(f"Your request for role `{self.role.name}` in **{interaction.guild.name}** was **Denied**.")
        except:
            pass

class SelfRoleSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Elite Agent", description="Instant grant: Standard active member role", emoji="⚡", value="agent"),
            discord.SelectOption(label="Security Officer", description="Requires Owner/Admin approval (High clearance)", emoji="🛡️", value="mod"),
            discord.SelectOption(label="Guest Node", description="Instant grant: Basic visitor role", emoji="👤", value="guest")
        ]
        super().__init__(placeholder="Select your operational clearance role...", min_values=1, max_values=1, options=options, custom_id="self_role_select_v2")

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
            await interaction.response.send_message("[ERROR] Role not found in system database.", ephemeral=True)
            return

        # الرتب الضعيفة / العادية تُمنح فوراً
        if selected_val in ["agent", "guest"]:
            if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(f"[SECURITY] Role '{role.name}' has been revoked from your profile.", ephemeral=True)
            else:
                await member.add_roles(role)
                await interaction.response.send_message(f"[SUCCESS] Role '{role.name}' has been instantly granted.", ephemeral=True)
        
        # الرتب الحساسة (مثل Security Officer / Admin) تتطلب موافقة الإدارة
        elif selected_val == "mod":
            if role in member.roles:
                await interaction.response.send_message("[INFO] You already possess this clearance role.", ephemeral=True)
                return

            # البحث عن قناة التحكم والإدارة لإرسال طلب الموافقة إليها
            control_channel = discord.utils.get(guild.text_channels, name="⚙️・room-control-hub")
            if not control_channel:
                # إذا لم تكن موجودة، ابحث عن أي قناة إدارية
                control_channel = discord.utils.get(guild.text_channels, name="🛠️・admin-console")

            if not control_channel:
                await interaction.response.send_message("[ERROR] Control channel for approvals is missing. Please re-run setup.", ephemeral=True)
                return

            embed = discord.Embed(
                title="🛡️ PENDING ROLE APPROVAL REQUEST",
                description=f"User <@{member.id}> has requested the high-clearance role **{role.name}**.\n\nChoose an action below:",
                color=0xFF8C00
            )
            embed.set_footer(text="CYBERKERNEL SECURITY GATEWAY")

            await control_channel.send(embed=embed, view=RoleApprovalView(member, role))
            await interaction.response.send_message(f"[PENDING] Your request for `{role.name}` has been sent to the administrators for security review.", ephemeral=True)

class SelfRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRoleSelect())

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
    status_msg = await ctx.send("[INIT] Deploying CyberKernel Architecture v19.7...")
    
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
            title="SYSTEM DYNAMIC NODE GENERATOR v19.7",
            description="Use the control buttons below to provision custom channels instantly with integrated visibility and auto-destruct timers.\n\n• **Green Button**: Create Text Node\n• **Blue Button**: Create Voice Node",
            color=0x00E676
        )
        embed.set_footer(text="CYBERKERNEL ENTERPRISE INTERFACE v19.7")
        await generator_chan.send(embed=embed, view=RoomGeneratorView())

        rules_embed = discord.Embed(
            title="SYSTEM SECURITY PROTOCOLS // CORE DIRECTIVES",
            description="Welcome to the enterprise core network. Strict adherence to security directives is mandatory.",
            color=0x00E676
        )
        await rules_chan.send(embed=rules_embed)

        roles_embed = discord.Embed(
            title="ENTERPRISE SELF-ROLES CLEARANCE SYSTEM",
            description="Select your desired operational clearance role from the interactive dropdown menu below.\n*Note: High-clearance roles require administrative approval.*",
            color=0x00E676
        )
        roles_embed.set_footer(text="CYBERKERNEL ROLE MANAGEMENT SYSTEM")
        await roles_chan.send(embed=roles_embed, view=SelfRoleView())

        await status_msg.edit(content="[SUCCESS] CyberKernel Architecture v19.7 deployed successfully.")

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
