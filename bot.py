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
# INTERACTIVE VIEWS & BUTTONS (Professional Design)
# ---------------------------------------------------------------------------

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity", style=discord.ButtonStyle.green, custom_id="verify_button", emoji="🛡️")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="Verified")
        if not role:
            # إنشاء رتبة Verified ومنحها صلاحية رؤية كل السكتارات
            role = await guild.create_role(name="Verified", color=discord.Color.blue())
            for cat in guild.categories:
                if cat.name != "🔒 -- [ SECTOR 01 ] SYSTEM CORE" and cat.name != "⚙️ -- [ ADMIN CONSOLE ]":
                    await cat.set_permissions(role, read_messages=True, connect=True)
        
        if role in interaction.user.roles:
            await interaction.response.send_message("[INFO] You are already verified!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("[SUCCESS] Verification complete. System access granted!", ephemeral=True)


class SelfRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Elite Agent", style=discord.ButtonStyle.primary, custom_id="role_elite", emoji="⚡")
    async def elite_agent(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Elite Agent")
        if not role:
            role = await interaction.guild.create_role(name="Elite Agent", color=discord.Color.gold())
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("[INFO] Elite Agent role removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("[SUCCESS] Elite Agent role granted!", ephemeral=True)

    @discord.ui.button(label="Guest Node", style=discord.ButtonStyle.secondary, custom_id="role_guest", emoji="👤")
    async def guest_node(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Guest Node")
        if not role:
            role = await interaction.guild.create_role(name="Guest Node", color=discord.Color.light_gray())
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message("[INFO] Guest Node role removed.", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("[SUCCESS] Guest Node role granted!", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.success, custom_id="open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
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
                await inter.response.send_message("Closing ticket...", ephemeral=True)
                await asyncio.sleep(3)
                await inter.channel.delete()

        await channel.send(f"Welcome {interaction.user.mention}! Support staff will assist you shortly.", view=CloseTicketView())
        await interaction.response.send_message(f"[SUCCESS] Ticket created: {channel.mention}", ephemeral=True)


class AdminControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="System Lockdown", style=discord.ButtonStyle.danger, custom_id="admin_lock", emoji="🔒")
    async def lockdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("[ALERT] System Lockdown initiated.", ephemeral=True)

    @discord.ui.button(label="System Unlock", style=discord.ButtonStyle.green, custom_id="admin_unlock", emoji="🔓")
    async def unlock(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message("[SUCCESS] System Unlocked.", ephemeral=True)


# ---------------------------------------------------------------------------
# BOT EVENTS & COMMANDS
# ---------------------------------------------------------------------------

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Secure Enterprise Bot operational.')

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    try:
        await ctx.message.delete()
    except:
        pass
    
    status_msg = await ctx.send("[INFO] Purging and deploying secure architecture...")

    # 1. مسح كامل لتنظيف السيرفر من أي تكرار
    for channel in guild.channels:
        try:
            await channel.delete()
            await asyncio.sleep(0.3)
        except:
            pass

    for category in guild.categories:
        try:
            await category.delete()
            await asyncio.sleep(0.3)
        except:
            pass

    # إعداد أذونات الإخفاء للعامة `@everyone`
    invisible_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False, connect=False)
    }

    visible_overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True, connect=True)
    }

    # 2. بناء الأقسام مع تطبيق الأذونات بدقة (غير المتحقق لا يرى شيئاً سوى السكتور الأول)
    
    # SECTOR 01: SYSTEM CORE (مرئي للجميع للتوثيق)
    cat1 = await guild.create_category("🔒 -- [ SECTOR 01 ] SYSTEM CORE", overwrites=visible_overwrites)
    sec_dir = await guild.create_text_channel("📜-security-directives", category=cat1)
    await sec_dir.send("**[VERIFICATION PROTOCOL]**\nClick below to verify your identity and unlock system access:", view=VerificationView())

    role_guide = await guild.create_text_channel("🛡️-role-hierarchy-guide", category=cat1)
    await role_guide.send("**[ENTERPRISE SELF-ROLES CLEARANCE SYSTEM]**\nSelect your desired operational clearance role using the interactive buttons below:", view=SelfRolesView())

    await guild.create_text_channel("📡-system-broadcast", category=cat1)

    # باقي السكتارات (مخفية تماماً عن غير المتحققين)
    cat2 = await guild.create_category("⚡ -- [ SECTOR 02 ] TERMINAL CHAT", overwrites=invisible_overwrites)
    conn_term = await guild.create_text_channel("🔗-connection-terminal", category=cat2)
    await conn_term.send("**[CONNECTION TERMINAL]**\nWelcome to the network. Use the ticketing system below for support:", view=TicketView())
    for ch_name in ["🌐-global-network", "💻-command-shell", "📦-payload-archive"]:
        await guild.create_text_channel(ch_name, category=cat2)

    cat3 = await guild.create_category("🎧 -- [ SECTOR 03 ] SECURE NODES", overwrites=invisible_overwrites)
    for vc_name in ["🔒 ➔ [Node-01] Safe Zone", "🛡️ ➔ [Node-02] Operations Room", "⚡ ➔ [Node-03] Secure Alpha"]:
        await guild.create_voice_channel(vc_name, category=cat3)

    cat4 = await guild.create_category("🎛️ -- [ SECTOR 04 ] ROOM GENERATOR", overwrites=invisible_overwrites)
    await guild.create_text_channel("🎛️-room-generator", category=cat4)

    await guild.create_category("📁 -- [ SECTOR 05 ] DYNAMIC NOTES", overwrites=invisible_overwrites)

    cat6 = await guild.create_category("👁️ -- [ SECTOR 06 ] CONTROL & LOGS", overwrites=invisible_overwrites)
    for ch_name in ["⚙️-room-control-hub", "📊-surveillance-logs"]:
        await guild.create_text_channel(ch_name, category=cat6)

    # ADMIN CONSOLE (للإدارة فقط)
    admin_cat = await guild.create_category("⚙️ -- [ ADMIN CONSOLE ]", overwrites=invisible_overwrites)
    admin_ch = await guild.create_text_channel("🛠️-admin-console", category=admin_cat, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    })
    await admin_ch.send("**[ADMINISTRATIVE CONTROL PANEL]**\nManage emergency lockdown and system security states:", view=AdminControlView())

    try:
        await status_msg.edit(content="[SUCCESS] Secure architecture deployed! Unverified users can only see Sector 01.")
        await asyncio.sleep(4)
        await status_msg.delete()
    except:
        pass

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

bot.run(os.getenv("DISCORD_TOKEN"))
