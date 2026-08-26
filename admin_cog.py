import discord
from discord.ext import commands
from discord import app_commands
import database
import views

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_system", description="[ROOT] Align server grid and initialize all interface terminals.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_system(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. الهيكلية المطابقة مع الفئات والقنوات
        TARGET_LAYOUT = {
            "SECTOR 00": {
                "fullname": "🔒 – SECTOR 00 | GATEWAY",
                "channels": ["⚡-arrival-terminal", "🛡️-verify-access", "📜-protocol-rules"]
            },
            "SECTOR 01": {
                "fullname": "🧬 – SECTOR 01 | CLEARANCE",
                "channels": ["🔑-announcements", "📡-system-status"]
            },
            "SECTOR 02": {
                "fullname": "⚡ – SECTOR 02 | TERMINAL",
                "channels": ["🌐-global-network", "💻-command-shell"]
            },
            "SECTOR 03": {
                "fullname": "🎧 – SECTOR 03 | NODES",
                "channels": [
                    ("net_00_safe_zone", discord.ChannelType.voice),
                    ("net_01_black_ops", discord.ChannelType.voice)
                ]
            },
            "SECTOR 04": {
                "fullname": "🎛️ – SECTOR 04 | SERVICES",
                "channels": ["🎮-create-node", "🎟️-open-ticket"]
            },
            "SECTOR 05": {
                "fullname": "📁 – SECTOR 05 | ARCHIVE",
                "channels": ["📦-data-vault", "📜-patch-notes"]
            },
            "SECTOR 06": {
                "fullname": "👁️ – SECTOR 06 | CONTROL",
                "channels": ["📊-surveillance-logs", "🚨-security-alerts"]
            },
            "SECTOR 07": {
                "fullname": "💻 – SECTOR 07 | DEV OPS",
                "channels": ["🛠️-bot-console"]
            },
            "SECTOR 08": {
                "fullname": "💎 – SECTOR 08 | VAULT",
                "channels": ["🏆-top-users", "⭐-vip-lounge"]
            }
        }

        allowed_channels = []
        for key, data in TARGET_LAYOUT.items():
            for item in data["channels"]:
                allowed_channels.append(item[0] if isinstance(item, tuple) else item)

        created_channels = {}

        # 2. مطابقة القطاعات وتوزيع الرومات
        for sec_code, sec_data in TARGET_LAYOUT.items():
            category = discord.utils.find(lambda c: sec_code in c.name, guild.categories)
            if not category:
                category = await guild.create_category(sec_data["fullname"])
            else:
                if category.name != sec_data["fullname"]:
                    try:
                        await category.edit(name=sec_data["fullname"])
                    except Exception:
                        pass

            for item in sec_data["channels"]:
                ch_name = item[0] if isinstance(item, tuple) else item
                ch_type = item[1] if isinstance(item, tuple) else discord.ChannelType.text

                existing = discord.utils.get(guild.channels, name=ch_name)
                if not existing:
                    if ch_type == discord.ChannelType.text:
                        ch_obj = await guild.create_text_channel(ch_name, category=category)
                    elif ch_type == discord.ChannelType.voice:
                        ch_obj = await guild.create_voice_channel(ch_name, category=category)
                    created_channels[ch_name] = ch_obj
                else:
                    if existing.category != category:
                        await existing.edit(category=category)
                    created_channels[ch_name] = existing

        # 3. تنظيف الرومات الغريبة مع استثناء Community
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                is_rules = (guild.rules_channel and channel.id == guild.rules_channel.id)
                is_updates = (guild.public_updates_channel and channel.id == guild.public_updates_channel.id)
                
                if not (is_rules or is_updates):
                    if channel.name not in allowed_channels and channel.name != "general":
                        try:
                            await channel.delete()
                        except Exception:
                            pass

        # 4. نشر الواجهات التفاعلية المصممة بشكـل عالي الجودة

        # (أ) Arrival Terminal Banner
        arrival_ch = created_channels.get("⚡-arrival-terminal")
        if arrival_ch:
            await arrival_ch.purge(limit=10)
            embed_arrival = discord.Embed(
                title="⚡ NEXUS // ENTRY TERMINAL INITIALIZED",
                description=(
                    "```yaml\n"
                    "SYSTEM STATUS: ONLINE\n"
                    "FIREWALL MODE: ACTIVE [ENCRYPTED]\n"
                    "PROTOCOL: CYBERPUNK NETWORK GRID v4.0.8\n"
                    "```\n"
                    "Welcome strictly authorized entities. Proceed to `#verify-access` to unlock full clearance."
                ),
                color=discord.Color.green()
            )
            embed_arrival.set_footer(text="NEXUS GRID AUTOMATION SYSTEMS")
            await arrival_ch.send(embed=embed_arrival)

        # (ب) Clearance Verification Embed (مع الزر)
        verify_ch = created_channels.get("🛡️-verify-access")
        if verify_ch:
            await verify_ch.purge(limit=10)
            embed_verify = discord.Embed(
                title="🛡️ IDENTITY VERIFICATION TERMINAL",
                description=(
                    "To access internal channels and features within the grid, you must authorize your user profile.\n\n"
                    "```yaml\n"
                    "Requirement: Click the authorization button below.\n"
                    "Clearance Level: [User] Verified Role\n"
                    "```"
                ),
                color=discord.Color.blue()
            )
            embed_verify.set_footer(text="Nexus Security System • Authorization Terminal")
            await verify_ch.send(embed=embed_verify, view=views.VerifyView())

        # (ج) Ticket System Embed (مع الزر)
        ticket_ch = created_channels.get("🎟️-open-ticket")
        if ticket_ch:
            await ticket_ch.purge(limit=10)
            embed_ticket = discord.Embed(
                title="🎟️ OPERATOR SUPPORT TERMINAL",
                description=(
                    "Need assistance, project support, or custom clearance permissions?\n\n"
                    "```yaml\n"
                    "Action: Click to launch a secure ticket channel.\n"
                    "Visibility: Only visible to assigned System Operators.\n"
                    "```"
                ),
                color=discord.Color.dark_purple()
            )
            embed_ticket.set_footer(text="Nexus Support Matrix • System Helpdesk")
            await ticket_ch.send(embed=embed_ticket, view=views.TicketLaunchView())

        await interaction.followup.send("```yaml\n[SUCCESS] Grid fully formatted! All terminal embeds & views successfully published.\n```")

    @app_commands.command(name="clear_roles", description="[ROOT] Purge non-essential custom roles.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        purged = 0
        for role in interaction.guild.roles:
            if role.name != "@everyone" and not role.managed and role < interaction.guild.me.top_role:
                try:
                    await role.delete()
                    purged += 1
                except Exception:
                    pass
        await interaction.followup.send(f"```yaml\n[ROOT] Purged {purged} custom roles.\n```")

async def setup(bot):
    await bot.add_cog(SystemAdmin(bot))
