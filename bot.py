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
# INTERACTIVE VIEWS & BUTTONS (Capitalized & Professional)
# ---------------------------------------------------------------------------

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify Identity", style=discord.ButtonStyle.green, custom_id="verify_button", emoji="🛡️")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name="Verified")
        if not role:
            role = await interaction.guild.create_role(name="Verified", color=discord.Color.blue())
        
        if role in interaction.user.roles:
            await interaction.response.send_message("[INFO] You are already verified!", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("[SUCCESS] Verification complete. Access granted.", ephemeral=True)


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
        category = discord.utils.get(guild.categories, name="⚡ -- [ Sector 02 ] Terminal Chat")
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
    print('Smart Enterprise Bot fully operational.')

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    try:
        await ctx.message.delete()
    except:
        pass
    
    status_msg = await ctx.send("[INFO] Purging server and rebuilding clean professional layout...")

    # 1. مسح وتنظيف السيرفر بالكامل من أي قنوات وأقسام قديمة لمنع أي تكرار
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

    # 2. بناء الهيكلة الجديدة بالكامل مع الحروف الكبيرة (Capitalized) والتنسيق الاحترافي
    
    # Sector 01: System Core
    cat1 = await guild.create_category("🔒 -- [ Sector 01 ] System Core")
    sec_dir = await guild.create_text_channel("Security-Directives", category=cat1)
    await sec_dir.send("**[Verification Protocol]**\nClick below to verify your identity and unlock system access:", view=VerificationView())

    role_guide = await guild.create_text_channel("Role-Hierarchy-Guide", category=cat1)
    await role_guide.send("**[Enterprise Self-Roles Clearance System]**\nSelect your desired operational clearance role using the interactive buttons below:", view=SelfRolesView())

    await guild.create_text_channel("System-Broadcast", category=cat1)

    # Sector 02: Terminal Chat
    cat2 = await guild.create_category("⚡ -- [ Sector 02 ] Terminal Chat")
    conn_term = await guild.create_text_channel("Connection-Terminal", category=cat2)
    await conn_term.send("**[Connection Terminal]**\nWelcome to the network. Use the ticketing system below for support:", view=TicketView())

    for ch_name in ["Global-Network", "Command-Shell", "Payload-Archive"]:
        await guild.create_text_channel(ch_name, category=cat2)

    # Sector 03: Secure Nodes
    cat3 = await guild.create_category("🎧 -- [ Sector 03 ] Secure Nodes")
    for vc_name in ["[Node-01] Safe Zone", "[Node-02] Operations Room", "[Node-03] Secure Alpha"]:
        await guild.create_voice_channel(vc_name, category=cat3)

    # Sector 04: Room Generator
    cat4 = await guild.create_category("🎛️ -- [ Sector 04 ] Room Generator")
    await guild.create_text_channel("Room-Generator", category=cat4)

    # Sector 05: Dynamic Notes
    await guild.create_category("📁 -- [ Sector 05 ] Dynamic Notes")

    # Sector 06: Control & Logs
    cat6 = await guild.create_category("👁️ -- [ Sector 06 ] Control & Logs")
    for ch_name in ["Room-Control-Hub", "Surveillance-Logs"]:
        await guild.create_text_channel(ch_name, category=cat6)

    # Admin Console
    admin_cat = await guild.create_category("⚙️ -- [ Admin Console ]")
    admin_ch = await guild.create_text_channel("Admin-Console", category=admin_cat, overwrites={
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    })
    await admin_ch.send("**[Administrative Control Panel]**\nManage emergency lockdown and system security states:", view=AdminControlView())

    print("[SUCCESS] Server architecture successfully rebuilt.")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

bot.run(os.getenv("DISCORD_TOKEN"))
