import discord
from discord.ext import commands
from discord import app_commands
import database
import views

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_system", description="[ROOT] Purge non-standard architecture and deploy core Cyberpunk design.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_system(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # الهيكلية المعتمدة
        TARGET_STRUCTURE = {
            "🔒 – SECTOR 00 | GATEWAY": [
                "⚡-arrival-terminal",
                "🛡️-verify-access",
                "📜-protocol-rules"
            ],
            "🧬 – SECTOR 01 | CLEARANCE": [
                "🔑-announcements",
                "📡-system-status"
            ],
            "⚡ – SECTOR 02 | TERMINAL": [
                "🌐-global-network",
                "💻-command-shell"
            ],
            "🎧 – SECTOR 03 | NODES": [
                ("net_00_safe_zone", discord.ChannelType.voice),
                ("net_01_black_ops", discord.ChannelType.voice)
            ],
            "🎛️ – SECTOR 04 | SERVICES": [
                "🎮-create-node",
                "🎟️-open-ticket"
            ],
            "📁 – SECTOR 05 | ARCHIVE": [
                "📦-data-vault",
                "📜-patch-notes"
            ],
            "👁️ – SECTOR 06 | CONTROL": [
                "📊-surveillance-logs",
                "🚨-security-alerts"
            ],
            "💻 – SECTOR 07 | DEV OPS": [
                "🛠️-bot-console"
            ],
            "💎 – SECTOR 08 | VAULT": [
                "🏆-top-users",
                "⭐-vip-lounge"
            ]
        }

        all_valid_names = []
        for channels in TARGET_STRUCTURE.values():
            for item in channels:
                all_valid_names.append(item[0] if isinstance(item, tuple) else item)

        # 1. تنظيف القنوات الزائدة والمكررة
        existing_channels = list(guild.channels)
        for channel in existing_channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                is_rules = (guild.rules_channel and channel.id == guild.rules_channel.id)
                is_updates = (guild.public_updates_channel and channel.id == guild.public_updates_channel.id)
                
                if not (is_rules or is_updates):
                    if channel.name not in all_valid_names:
                        try:
                            await channel.delete(reason="System Reset")
                        except Exception:
                            pass

        created_channels = {}

        # 2. إنشاء وتجميع القطاعات
        for cat_name, channels in TARGET_STRUCTURE.items():
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)

            for item in channels:
                ch_name = item[0] if isinstance(item, tuple) else item
                ch_type = item[1] if isinstance(item, tuple) else discord.ChannelType.text

                existing = discord.utils.get(guild.channels, name=ch_name)
                if not existing:
                    if ch_type == discord.ChannelType.text:
                        ch_obj = await guild.create_text_channel(ch_name, category=category)
                    else:
                        ch_obj = await guild.create_voice_channel(ch_name, category=category)
                    created_channels[ch_name] = ch_obj
                else:
                    if existing.category != category:
                        await existing.edit(category=category)
                    created_channels[ch_name] = existing

        # 3. إزالة أي مكررات إضافية
        for ch_name in all_valid_names:
            matches = [c for c in guild.channels if c.name == ch_name]
            if len(matches) > 1:
                for duplicate in matches[1:]:
                    try:
                        await duplicate.delete(reason="Purge Duplicate")
                    except Exception:
                        pass

        # 4. إعادة التصميم الأصلي (Full Cyberpunk Terminal UI)

        # ---------------- ARRIVAL TERMINAL ----------------
        arrival_ch = created_channels.get("⚡-arrival-terminal")
        if arrival_ch:
            await arrival_ch.purge(limit=20)
            embed_arrival = discord.Embed(
                title="═══ [ NEXUS SYSTEM // ENTRY TERMINAL ] ═══",
                description=(
                    "```yaml\n"
                    "╔══════════════════════════════════════════════════════════════╗\n"
                    "║  SYSTEM STATUS : ONLINE                                      ║\n"
                    "║  FIREWALL      : ENCRYPTED // ACTIVE                         ║\n"
                    "║  NODE PROTOCOL : CYBERPUNK NETWORK GRID v4.0.8               ║\n"
                    "╚══════════════════════════════════════════════════════════════╝\n"
                    "```\n"
                    "> **[!] INCOMING SIGNAL DETECTED**\n"
                    "> Welcome to **NEXUS ZERO**. All network activity is logged and encrypted.\n\n"
                    "📌 **NEXT STEP:** Head over to <#verify-access> to request identity clearance."
                ),
                color=0x00FF66
            )
            embed_arrival.set_image(url="https://i.imgur.com/xV7N4Zb.gif") # خيارات الجرافيك السايبر
            embed_arrival.set_footer(text="NEXUS CORE OS // SECURITY CLEARANCE REQUIRED", icon_url=guild.icon.url if guild.icon else None)
            await arrival_ch.send(embed=embed_arrival)

        # ---------------- VERIFICATION TERMINAL ----------------
        verify_ch = created_channels.get("🛡️-verify-access")
        if verify_ch:
            await verify_ch.purge(limit=20)
            embed_verify = discord.Embed(
                title="═══ [ SECURITY PROTOCOL // VERIFICATION ] ═══",
                description=(
                    "```ini\n"
                    "[ AUTHORIZATION REQUIRED TO ACCESS INTERNAL NODES ]\n"
                    "```\n"
                    "```yaml\n"
                    "Status   : CLEARANCE PENDING\n"
                    "Action   : Click [AUTHORIZE ACCESS] below to sync profile.\n"
                    "Role Granted : [User] Verified\n"
                    "```\n"
                    "⚠️ *Unverified users are restricted from executing commands or viewing private network sectors.*"
                ),
                color=0x0099FF
            )
            embed_verify.set_footer(text="GATEWAY CONTROL // PROTOCOL 00", icon_url=guild.icon.url if guild.icon else None)
            await verify_ch.send(embed=embed_verify, view=views.VerifyView())

        # ---------------- TICKET SUPPORT TERMINAL ----------------
        ticket_ch = created_channels.get("🎟️-open-ticket")
        if ticket_ch:
            await ticket_ch.purge(limit=20)
            embed_ticket = discord.Embed(
                title="═══ [ SYSTEM HELPDESK // DISPATCH TERMINAL ] ═══",
                description=(
                    "```yaml\n"
                    "╔══════════════════════════════════════════════════════════════╗\n"
                    "║  DIRECT SUPPORT LINE : ACTIVE                               ║\n"
                    "║  ENCRYPTION LEVEL   : END-TO-END SYSTEM ENCRYPTED           ║\n"
                    "╚══════════════════════════════════════════════════════════════╝\n"
                    "```\n"
                    "> Need system assistance, custom permissions, or technical support?\n"
                    "> Click **OPEN SYSTEM TICKET** below to launch a dedicated secure terminal."
                ),
                color=0x9900FF
            )
            embed_ticket.set_footer(text="NEXUS SERVICES // TERMINAL DISPATCH", icon_url=guild.icon.url if guild.icon else None)
            await ticket_ch.send(embed=embed_ticket, view=views.TicketLaunchView())

        await interaction.followup.send("```yaml\n[SUCCESS] Original Cyberpunk Terminal UI successfully redeployed without duplicates!\n```")

    @app_commands.command(name="clear_roles", description="[ROOT] Purge custom non-essential roles.")
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
