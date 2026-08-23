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
            await interaction.response.send_message("[SUCCESS] Verification complete. Access granted to system sectors.", ephemeral=True)


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
            await interaction.response.send_message("[SUCCESS] Elite Agent role granted instantly!", ephemeral=True)

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
            await interaction.response.send_message("[SUCCESS] Guest Node role granted instantly!", ephemeral=True)

    @discord.ui.button(label="Security Officer", style=discord.ButtonStyle.danger, custom_id="role_security", emoji="🔒")
    async def security_officer(self, interaction: discord.Interaction, button: discord.ui.Button):
        admin_channel = discord.utils.get(interaction.guild.text_channels, name="admin-console")
        if not admin_channel:
            admin_channel = interaction.channel

        class ApprovalView(discord.ui.View):
            def __init__(self, member: discord.Member):
                super().__init__(timeout=86400)
                self.member = member

            @discord.ui.button(label="Approve", style=discord.ButtonStyle.green, custom_id="approve_sec")
            async def approve(self, inter: discord.Interaction, btn: discord.ui.Button):
                if not inter.user.guild_permissions.administrator:
                    return await inter.response.send_message("Only administrators can approve this.", ephemeral=True)
                role = discord.utils.get(inter.guild.roles, name="Security Officer")
                if not role:
                    role = await inter.guild.create_role(name="Security Officer", color=discord.Color.red())
                await self.member.add_roles(role)
                await inter.response.edit_message(content=f"[APPROVED] Security Officer role granted to {self.member.mention} by {inter.user.mention}.", view=None)

            @discord.ui.button(label="Deny", style=discord.ButtonStyle.red, custom_id="deny_sec")
            async def deny(self, inter: discord.Interaction, btn: discord.ui.Button):
                if not inter.user.guild_permissions.administrator:
                    return await inter.response.send_message("Only administrators can deny this.", ephemeral=True)
                await inter.response.edit_message(content=f"[DENIED] Security Officer request for {self.member.mention} denied by {inter.user.mention}.", view=None)

        embed = discord.Embed(title="[PENDING] Security Clearance Request", color=discord.Color.orange())
        embed.add_field(name="User", value=interaction.user.mention, inline=False)
        embed.add_field(name="Requested Role", value="Security Officer", inline=False)
        
        await admin_channel.send(embed=embed, view=ApprovalView(interaction.user))
        await interaction.response.send_message("[PENDING] Your request for Security Officer requires administrator approval.", ephemeral=True)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Support Ticket", style=discord.ButtonStyle.success, custom_id="open_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="[SECTOR 02] TERMINAL CHAT")
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
                await inter.response.send_message("Closing ticket in 3 seconds...", ephemeral=True)
                await asyncio.sleep(3)
                await inter.channel.delete()

        await channel.send(f"Welcome {interaction.user.mention}! Support staff will assist you shortly.", view=CloseTicketView())
        await interaction.response.send_message(f"[SUCCESS] Ticket created: {channel.mention}", ephemeral=True)


class AdminControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Lockdown", style=discord.ButtonStyle.danger, custom_id="admin_lock", emoji="🔒")
    async def lockdown(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("Administrator permission required.", ephemeral=True)
        for channel in interaction.guild.text_channels:
            await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message("[ALERT] System Lockdown initiated.", ephemeral=True)

    @discord.ui.button(label="Unlock", style=discord.ButtonStyle.green, custom_id="admin_unlock", emoji="🔓")
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
    print('Enterprise Bot fully operational with Capitalized UI components.')

@bot.command(name="setup")
@commands.has_permissions(administrator=True)
async def setup(ctx):
    guild = ctx.guild
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Sector 01
    cat1 = discord.utils.get(guild.categories, name="[SECTOR 01] SYSTEM CORE")
    if not cat1:
        cat1 = await guild.create_category("[SECTOR 01] SYSTEM CORE")
    
    sec_dir = discord.utils.get(cat1.text_channels, name="security-directives")
    if not sec_dir:
        sec_dir = await guild.create_text_channel("security-directives", category=cat1)
        await sec_dir.send("**[VERIFICATION PROTOCOL]**\nClick below to verify your identity and unlock system access:", view=VerificationView())

    role_guide = discord.utils.get(cat1.text_channels, name="role-hierarchy-guide")
    if not role_guide:
        role_guide = await guild.create_text_channel("role-hierarchy-guide", category=cat1)
        await role_guide.send("**[ENTERPRISE SELF-ROLES CLEARANCE SYSTEM]**\nSelect your desired operational clearance role using the interactive buttons below:", view=SelfRolesView())

    # Sector 02
    cat2 = discord.utils.get(guild.categories, name="[SECTOR 02] TERMINAL CHAT")
    if not cat2:
        cat2 = await guild.create_category("[SECTOR 02] TERMINAL CHAT")
    
    conn_term = discord.utils.get(cat2.text_channels, name="connection-terminal")
    if not conn_term:
        conn_term = await guild.create_text_channel("connection-terminal", category=cat2)
        await conn_term.send("**[CONNECTION TERMINAL]**\nWelcome to the network. Use the ticketing system below for support:", view=TicketView())

    # Admin Console
    admin_cat = discord.utils.get(guild.categories, name="[ADMIN CONSOLE]")
    if not admin_cat:
        admin_cat = await guild.create_category("[ADMIN CONSOLE]")
    
    admin_ch = discord.utils.get(admin_cat.text_channels, name="admin-console")
    if not admin_ch:
        admin_ch = await guild.create_text_channel("admin-console", category=admin_cat, overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        })
        await admin_ch.send("**[ADMINISTRATIVE CONTROL PANEL]**\nManage emergency lockdown and system security states:", view=AdminControlView())

    await ctx.send("[SUCCESS] Advanced enterprise server architecture deployed successfully!", delete_after=10)

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 10):
    await ctx.channel.purge(limit=amount + 1)

bot.run(os.getenv("DISCORD_TOKEN"))
