import discord

class VerifyModal(discord.ui.Modal, title="🛡️ CLEARANCE REQUEST FORM"):
    codename = discord.ui.TextInput(
        label="Operator Codename / Alias",
        placeholder="Enter your handle or real name...",
        required=True,
        max_length=50
    )
    reason = discord.ui.TextInput(
        label="Reason for Access Request",
        style=discord.TextStyle.paragraph,
        placeholder="Specify your purpose for joining the grid...",
        required=True,
        max_length=300
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        # توجيه الطلب لروم المراقبة والأدمن
        alerts_ch = discord.utils.get(guild.channels, name="🚨-security-alerts")
        
        embed = discord.Embed(
            title="📥 NEW CLEARANCE REQUEST",
            description=(
                f"**User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                f"**Codename:** `{self.codename.value}`\n"
                f"**Reason:**\n```\n{self.reason.value}\n```"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        
        if alerts_ch:
            await alerts_ch.send(embed=embed, view=AdminApprovalView(target_user=interaction.user))
            await interaction.followup.send("```yaml\n[PENDING] Your clearance request has been routed to System Operators for approval.\n```", ephemeral=True)
        else:
            await interaction.followup.send("❌ Error: Verification alert channel not found.", ephemeral=True)

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="AUTHORIZE ACCESS", style=discord.ButtonStyle.green, custom_id="verify_start_btn", emoji="🛡️")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(VerifyModal())

class AdminApprovalView(discord.ui.View):
    def __init__(self, target_user: discord.User):
        super().__init__(timeout=None)
        self.target_user = target_user

    @discord.ui.button(label="APPROVE CLEARANCE", style=discord.ButtonStyle.success, custom_id="approve_user_btn", emoji="✅")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        guild = interaction.guild
        member = guild.get_member(self.target_user.id)
        
        # البحث عن رول Verified أو إنشاؤه
        role = discord.utils.get(guild.roles, name="Verified Operator")
        if not role:
            role = await guild.create_role(name="Verified Operator", color=discord.Color.green())

        if member:
            await member.add_roles(role)
            for item in self.children:
                item.disabled = True
            
            embed = interaction.message.embeds[0]
            embed.color = discord.Color.green()
            embed.title = "✅ CLEARANCE APPROVED"
            embed.add_field(name="Approved By", value=interaction.user.mention)
            
            await interaction.message.edit(embed=embed, view=self)
            try:
                await member.send("```yaml\n[ACCESS GRANTED] Your security clearance request has been APPROVED by system admins.\n```")
            except Exception:
                pass

    @discord.ui.button(label="DENY ACCESS", style=discord.ButtonStyle.danger, custom_id="deny_user_btn", emoji="❌")
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ CLEARANCE DENIED"
        embed.add_field(name="Denied By", value=interaction.user.mention)
        
        await interaction.message.edit(embed=embed, view=self)

class TicketLaunchView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="OPEN SYSTEM TICKET", style=discord.ButtonStyle.primary, custom_id="ticket_open_btn", emoji="🎟️")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket feature initialized.", ephemeral=True)
