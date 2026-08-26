import discord
from discord.ext import commands
from discord import app_commands
import database

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. أمر التنظيف وإعادة البناء الذكي (Minimalist Cyber Architecture)
    @app_commands.command(name="setup_system", description="[ROOT] Purge non-standard channels and deploy optimized Cyberpunk structure.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_system(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # التصميم الأدق والأنظف بدون تكرار أو زحمة
        TARGET_LAYOUT = {
            "🔒 SECTOR 00 // GATEWAY": [
                "⚡-arrival-terminal",
                "🛡️-verify-access",
                "📜-protocol-rules"
            ],
            "⚡ SECTOR 01 // TERMINAL": [
                "🌐-global-network",
                "💻-command-shell",
                "📊-surveillance-logs"
            ],
            "🎛️ SECTOR 02 // SERVICES": [
                "🎮-create-node",
                "🎟️-open-ticket"
            ],
            "🔊 SECTOR 03 // NODES": [
                ("net_00_safe_zone", discord.ChannelType.voice),
                ("net_01_black_ops", discord.ChannelType.voice)
            ]
        }

        # تجميع الرومات المسموحة
        allowed_channels = []
        for cat, chans in TARGET_LAYOUT.items():
            for ch in chans:
                allowed_channels.append(ch[0] if isinstance(ch, tuple) else ch)

        # مسح الزيادات والطفح داخل السيرفر
        for channel in guild.channels:
            if channel.category and "SECTOR" in channel.category.name:
                if channel.name not in allowed_channels:
                    try:
                        await channel.delete(reason="Purging non-standard terminal node")
                    except Exception:
                        pass

        # إنشاء الرومات وتطوير الهيكل
        for cat_name, channels in TARGET_LAYOUT.items():
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)

            for item in channels:
                ch_name = item[0] if isinstance(item, tuple) else item
                ch_type = item[1] if isinstance(item, tuple) else discord.ChannelType.text

                existing = discord.utils.get(category.channels, name=ch_name)
                if not existing:
                    if ch_type == discord.ChannelType.text:
                        await guild.create_text_channel(ch_name, category=category)
                    elif ch_type == discord.ChannelType.voice:
                        await guild.create_voice_channel(ch_name, category=category)

        await interaction.followup.send("```yaml\n[SYSTEM] System layout synchronized. Redundant nodes successfully purged.\n```")

    # 2. أمر تصفير وإلغاء جميع الرولات الإضافية بضغطة واحدة
    @app_commands.command(name="clear_roles", description="[ROOT] Strip all non-essential roles from the server.")
    @app_commands.checks.has_permissions(administrator=True)
    async def clear_roles(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        purged_count = 0
        
        for role in interaction.guild.roles:
            if role.name != "@everyone" and not role.managed and role < interaction.guild.me.top_role:
                try:
                    await role.delete(reason="Root Clearance Command Executed")
                    purged_count += 1
                except Exception:
                    pass

        await interaction.followup.send(f"```yaml\n[ROOT CLEARANCE] Execution complete. Removed {purged_count} custom roles.\n```")

    # 3. أمر التحذير الإداري
    @app_commands.command(name="warn", description="[MOD] Issue a security violation warning to a user.")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        database.add_warning(user.id, interaction.guild.id, reason, interaction.user.id)
        embed = discord.Embed(
            title="⚠️ SECURITY VIOLATION RECORDED",
            description=f"**Target:** {user.mention}\n**Reason:** {reason}\n**Issuer:** {interaction.user.mention}",
            color=discord.Color.dark_red()
        )
        await interaction.response.send_message(embed=embed)

    # 4. تفعيل / إلغاء وضع الـ RAID
    @app_commands.command(name="raid_mode", description="[SECURITY] Lock or Unlock access protocols for new accounts.")
    @app_commands.checks.has_permissions(administrator=True)
    async def raid_mode(self, interaction: discord.Interaction, enable: bool):
        database.set_raid_mode(interaction.guild.id, enable)
        status_str = "ENABLED [PROTOCOL LOCKDOWN ACTIVE]" if enable else "DISABLED [STANDARD ACCESS RESTORED]"
        
        embed = discord.Embed(
            title="🛡️ DEFENSE PROTOCOL UPDATED",
            description=f"```yaml\nStatus: {status_str}\n```",
            color=discord.Color.red() if enable else discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(SystemAdmin(bot))