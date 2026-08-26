import discord
from discord.ext import commands
from discord import app_commands
import database
import views

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_system", description="[ROOT] Auto-align all Cyberpunk sectors and populate missing channels.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_system(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. الهيكلية الكاملة لجميع القطاعات لمنع وجود أي Category فارغ
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
                "channels": ["🛠️-bot-console", "⚙️-system-tests"]
            },
            "SECTOR 08": {
                "fullname": "💎 – SECTOR 08 | VAULT",
                "channels": ["🏆-top-users", "⭐-vip-lounge"]
            }
        }

        # جمع أسماء الرومات المعتمدة لمنع حذفها
        allowed_channels = []
        for key, data in TARGET_LAYOUT.items():
            for item in data["channels"]:
                allowed_channels.append(item[0] if isinstance(item, tuple) else item)

        created_channels = {}

        # 2. ربط القنوات بالقطاعات عبر المطابقة الجزئية برقم القطاع
        for sec_code, sec_data in TARGET_LAYOUT.items():
            # البحث عن القطاع في السيرفر عبر الرقم
            category = discord.utils.find(lambda c: sec_code in c.name, guild.categories)
            
            if not category:
                category = await guild.create_category(sec_data["fullname"])
            else:
                # إعادة تسميته بالشكل المطلوب إن لزم
                if category.name != sec_data["fullname"]:
                    try:
                        await category.edit(name=sec_data["fullname"])
                    except Exception:
                        pass

            # إضافة الرومات داخل القطاع
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

        # 3. تنظيف القنوات المكررة أو الزائدة (مع استثناء رومات Community)
        for channel in guild.channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                is_rules = (guild.rules_channel and channel.id == guild.rules_channel.id)
                is_updates = (guild.public_updates_channel and channel.id == guild.public_updates_channel.id)
                
                if not (is_rules or is_updates):
                    if channel.name not in allowed_channels and channel.name != "general":
                        try:
                            await channel.delete(reason="Clean non-layout channel")
                        except Exception:
                            pass

        # 4. نشر الواجهات التفاعلية (Verify & Tickets)
        verify_ch = created_channels.get("🛡️-verify-access")
        if verify_ch:
            embed_verify = discord.Embed(
                title="🛡️ CLEARANCE VERIFICATION REQUIRED",
                description="Click below to verify access credentials and gain access to grid nodes.",
                color=discord.Color.blue()
            )
            await verify_ch.purge(limit=5)
            await verify_ch.send(embed=embed_verify, view=views.VerifyView())

        ticket_ch = created_channels.get("🎟️-open-ticket")
        if ticket_ch:
            embed_ticket = discord.Embed(
                title="🎟️ SYSTEM TERMINAL SUPPORT",
                description="Click below to open a direct support request channel.",
                color=discord.Color.dark_purple()
            )
            await ticket_ch.purge(limit=5)
            await ticket_ch.send(embed=embed_ticket, view=views.TicketLaunchView())

        await interaction.followup.send("```yaml\n[SUCCESS] Grid fully aligned! All sectors populated and interfaces active.\n```")

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
