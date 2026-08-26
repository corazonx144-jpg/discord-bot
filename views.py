import discord
from discord.ui import View, Button, Select
import database

# 1. واجهة التوثيق والتحقق (Verification System)
class VerifyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="AUTHORIZE ACCESS", 
        style=discord.ButtonStyle.green, 
        custom_id="nexus_verify_button",
        emoji="🛡️"
    )
    async def verify_button(self, interaction: discord.Interaction, button: Button):
        # البحث عن رول Verified أو إنشائه إن لم يكن موجوداً
        guild = interaction.guild
        role = discord.utils.get(guild.roles, name="[User] Verified")
        
        if not role:
            role = await guild.create_role(name="[User] Verified", color=discord.Color.blue())

        if role in interaction.user.roles:
            await interaction.response.send_message(
                "```yaml\n[SYSTEM] Access already granted. Clearance verified.\n```", 
                ephemeral=True
            )
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(
                "```yaml\n[SUCCESS] Credentials Accepted. Access granted to internal nodes.\n```", 
                ephemeral=True
            )

# 2. واجهة فتح التكت والدعم الفني (Ticket System)
class TicketLaunchView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="OPEN SYSTEM TICKET", 
        style=discord.ButtonStyle.blurple, 
        custom_id="nexus_open_ticket",
        emoji="🎟️"
    )
    async def open_ticket(self, interaction: discord.Interaction, button: Button):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="🎛️ SECTOR 02 // SERVICES")
        
        # إنشاء روم التكت الخاص للمستخدم
        ticket_channel_name = f"ticket-{interaction.user.name}"
        existing_ticket = discord.utils.get(guild.channels, name=ticket_channel_name)
        
        if existing_ticket:
            await interaction.response.send_message(
                f"```yaml\n[WARNING] Active session already exists: #{ticket_channel_name}\n```", 
                ephemeral=True
            )
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        channel = await guild.create_text_channel(
            name=ticket_channel_name, 
            category=category, 
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎟️ SYSTEM TICKET INITIALIZED",
            description=(
                f"Greetings {interaction.user.mention},\n"
                f"State your query or issue below. A staff member will respond shortly.\n\n"
                f"```yaml\nStatus: WAITING FOR OPERATOR\n```"
            ),
            color=discord.Color.dark_teal()
        )
        
        await channel.send(embed=embed, view=TicketControlView())
        await interaction.response.send_message(
            f"```yaml\n[SUCCESS] Ticket terminal created: #{ticket_channel_name}\n```", 
            ephemeral=True
        )

# 3. واجهة التحكم داخل التكت (إغلاق التكت)
class TicketControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="CLOSE TERMINAL", 
        style=discord.ButtonStyle.red, 
        custom_id="nexus_close_ticket",
        emoji="🔒"
    )
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("```yaml\n[TERMINATING] Terminating session in 5 seconds...\n```")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.utils.timedelta(seconds=5))
        await interaction.channel.delete(reason="Ticket closed by user/staff")