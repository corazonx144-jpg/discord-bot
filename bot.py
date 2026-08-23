import discord
from discord.ext import commands
import asyncio
import os
from flask import Flask
import threading

# ---------------------------------------------------------------------------
# 1. FLASK WEB SERVER (لإرضاء منصة Render ومنع إغلاق البورت)
# ---------------------------------------------------------------------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running and active!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ---------------------------------------------------------------------------
# 2. DISCORD BOT SETUP
# ---------------------------------------------------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------------------------
# INTERACTIVE VIEWS & BUTTONS
# ---------------------------------------------------------------------------

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity", style=discord.ButtonStyle.green, custom_id="verify_button", emoji="🛡️")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="Verified")
        
        if not role:
            role = await guild.create_role(name="Verified", color=discord.Color.blue())

        if role in interaction.user.roles:
            await interaction.followup.send("[INFO] You are already verified!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.followup.send("[SUCCESS] Verification complete. System access granted!", ephemeral=True)


class SelfRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Elite Agent", style=discord.ButtonStyle.primary, custom_id="role_elite", emoji="⚡")
    async def elite_agent(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name="Elite Agent")
        if not role:
            role = await interaction.guild.create_role(name="Elite Agent", color=discord.Color.gold())
            
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.followup.send("[INFO] Elite Agent role removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.followup.send("[SUCCESS] Elite Agent role granted!", ephemeral=True)

    @discord.ui.button(label="Guest Node", style=discord.ButtonStyle.secondary, custom_id="role_guest", emoji="👤")
    async def guest_node(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        role = discord.utils.get(interaction.guild.roles, name="Guest Node")
        if not role:
            role = await interaction.guild.create_role(name="Guest Node", color=discord.Color.light_gray())
            
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.followup.send("[INFO] Guest Node role removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.followup.send("[SUCCESS] Guest Node role granted!", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.success, custom_id="open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="⚡ -- [ SECTOR 02 ] TERMINAL CHAT")
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        
        class CloseTicketView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=None)
            @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
            async def close(self, inter: discord.Interaction, btn: discord.ui.Button):
                await inter.response.defer(ephemeral=True)
                await inter.followup.send("Closing ticket in 3 seconds...", ephemeral=True)
                await asyncio.sleep(3)
                await inter.channel.delete()

        await channel.send(f"Welcome {interaction.user.mention}! Support staff will assist you shortly.", view=CloseTicketView())
        await interaction.followup.send(f"[SUCCESS] Ticket created: {channel.mention}", ephemeral=True)


class AdminControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="System Lockdown", style=discord.ButtonStyle.danger, custom_id="admin_lock", emoji="🔒")
    async def lockdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("Administrator permission required.", ephemeral=True)
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.followup.send("[ALERT] System Lockdown initiated.", ephemeral=True)

    @discord.ui.button(label="System Unlock", style=discord.ButtonStyle.green, custom_id="admin_unlock", emoji="🔓")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("Administrator permission required.", ephemeral=True)
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.followup.send("[SUCCESS] System Unlocked.", ephemeral=True)


# ---------------------------------------------------------------------------
# BOT EVENTS & COMMANDS
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    bot.add_view(VerificationView())
    bot.add_view(SelfRolesView())
    bot.add_view(TicketView())
    bot.add_view(AdminControlView())
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Anti-Rate-Limit Security Bot operational.')

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    try:
        await ctx.message.delete()
    except:
        pass
    
    status_msg = await ctx.send("[INFO] Safe purging and rebuilding architecture (Anti-Rate-Limit active)...")

    # 1. مسح القنوات والأقسام ببطء آمن لمنع الحظر المؤقت من ديسكورد
    for channel in guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.5)
        except:
            pass

    for category in guild.categories:
        try:
            await category.delete()
            await asyncio.sleep(0.5)
        except:
            pass

    # 2. إنشاء رتبة Verified مسبقاً
    verified_role = discord.utils.get(guild.roles, name="Verified")
    if not verified_role:
        verified_role = await guild.create_role(name="Verified", color=discord.Color.blue())

    public_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }

    protected_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False, view_channel=False),
        verified_role: discord.PermissionOverwrite(read_messages=True, connect=True, send_messages=True, view_channel=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, view_channel=True)
    }

    await asyncio.sleep(1)

    # 3. بناء الأقسام خطوة بخطوة مع فترات راحة آمنة لمنع التوقف
    
    # SECTOR 01
    cat1 = await guild.create_category("🔒 -- [ SECTOR 01 ] SYSTEM CORE", overwrites=public_overwrites)
    await asyncio.sleep(0.3)
    sec_dir = await guild.create_text_channel("📜-security-directives", category=cat1, sync_permissions=True)
    await sec_dir.send("**[VERIFICATION PROTOCOL]**\nClick below to verify your identity and unlock system access:", view=VerificationView())
    await asyncio.sleep(0.3)

    role_guide = await guild.create_text_channel("🛡️-role-hierarchy-guide", category=cat1, sync_permissions=True)
    await role_guide.send("**[ENTERPRISE SELF-ROLES CLEARANCE SYSTEM]**\nSelect your desired operational clearance role using the interactive buttons below:", view=SelfRolesView())
    await asyncio.sleep(0.3)

    await guild.create_text_channel("📡-system-broadcast", category=cat1, sync_permissions=True)
    await asyncio.sleep(0.5)

    # SECTOR 02
    cat2 = await guild.create_category("⚡ -- [ SECTOR 02 ] TERMINAL CHAT", overwrites=protected_overwrites)
    await asyncio.sleep(0.3)
    conn_term = await guild.create_text_channel("🔗-connection-terminal", category=cat2, sync_permissions=True)
    await conn_term.send("**[CONNECTION TERMINAL]**\nWelcome to the network. Use the ticketing system below for support:", view=TicketView())
    await asyncio.sleep(0.3)
    for ch_name in ["🌐-global-network", "💻-command-shell", "📦-payload-archive"]:
        await guild.create_text_channel(ch_name, category=cat2, sync_permissions=True)
        await asyncio.sleep(0.3)

    # SECTOR 03
    cat3 = await guild.create_category("🎧 -- [ SECTOR 03 ] SECURE NODES", overwrites=protected_overwrites)
    await asyncio.sleep(0.3)
    for vc_name in ["🔒 ➔ [Node-01] Safe Zone", "🛡️ ➔ [Node-02] Operations Room", "⚡ ➔ [Node-03] Secure Alpha"]:
        await guild.create_voice_channel(vc_name, category=cat3, sync_permissions=True)
        await asyncio.sleep(0.3)

    # SECTOR 04
    cat4 = await guild.create_category("🎛️ -- [ SECTOR 04 ] ROOM GENERATOR", overwrites=protected_overwrites)
    await asyncio.sleep(0.3)
    await guild.create_text_channel("🎛️-room-generator", category=cat4, sync_permissions=True)
    await asyncio.sleep(0.3)

    # SECTOR 05
    await guild.create_category("📁 -- [ SECTOR 05 ] DYNAMIC NOTES", overwrites=protected_overwrites)
    await asyncio.sleep(0.3)

    # SECTOR 06
    cat6 = await guild.create_category("👁️ -- [ SECTOR 06 ] CONTROL & LOGS", overwrites=protected_overwrites)
    await asyncio.sleep(0.3)
    for ch_name in ["⚙️-room-control-hub", "📊-surveillance-logs"]:
        await guild.create_text_channel(ch_name, category=cat6, sync_permissions=True)
        await asyncio.sleep(0.3)

    # ADMIN CONSOLE
    admin_cat = await guild.create_category("⚙️ -- [ ADMIN CONSOLE ]", overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, view_channel=True)
    })
    await asyncio.sleep(0.3)
    admin_ch = await guild.create_text_channel("🛠️-admin-console", category=admin_cat, sync_permissions=True)
    await admin_ch.send("**[ADMINISTRATIVE CONTROL PANEL]**\nManage emergency lockdown and system security states:", view=AdminControlView())

    try:
        await status_msg.edit(content="[SUCCESS] All sectors and security boundaries successfully deployed!")
        await asyncio.sleep(4)
        await status_msg.delete()
    except:
        pass

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

bot.run(os.getenv("DISCORD_TOKEN"))
