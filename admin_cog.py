import discord
from discord.ext import commands
from discord import app_commands
import database
import views

class SystemAdmin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setup_system", description="[ROOT] Purge non-standard architecture and deploy clean Cyberpunk grid.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_system(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild

        # 1. الهيكلية الدقيقة والمحصورة لمنع أي تكرار
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

        # قائمة كل أسماء القنوات المسموح بوجودها
        all_valid_names = []
        for channels in TARGET_STRUCTURE.values():
            for item in channels:
                all_valid_names.append(item[0] if isinstance(item, tuple) else item)

        # 2. تنظيف القنوات المكررة أو الزائدة أولاً قبل أي إنشاء
        existing_channels = list(guild.channels)
        for channel in existing_channels:
            if isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                # حماية رومات الـ Community الرسمية
                is_rules = (guild.rules_channel and channel.id == guild.rules_channel.id)
                is_updates = (guild.public_updates_channel and channel.id == guild.public_updates_channel.id)
                
                if not (is_rules or is_updates):
                    # لو القناة مش في القائمة أو مكررة يتم مسحها
                    if channel.name not in all_valid_names:
                        try:
                            await channel.delete(reason="System Reset")
                        except Exception:
                            pass

        created_channels = {}

        # 3. بناء الكاتيغوريز والقنوات بدون تكرار
        for cat_name, channels in TARGET_STRUCTURE.items():
            category = discord.utils.get(guild.categories, name=cat_name)
            if not category:
                category = await guild.create_category(cat_name)

            for item in channels:
                ch_name = item[0] if isinstance(item, tuple) else item
                ch_type = item[1] if isinstance(item, tuple) else discord.ChannelType.text

                # البحث عن القناة والتأكد أننا لا ننشئ نسختين
                existing = discord.utils.get(guild.channels, name=ch_name)
                
                if not existing:
                    if ch_type == discord.ChannelType.text:
                        ch_obj = await guild.create_text_channel(ch_name, category=category)
                    else:
                        ch_obj = await guild.create_voice_channel(ch_name, category=category)
                    created_channels[ch_name] = ch_obj
                else:
                    # لو موجودة انقلها للقطاع الصحيح واستخدمها
                    if existing.category != category:
                        await existing.edit(category=category)
                    created_channels[ch_name] = existing

        # مسح أي نسخ مكررة بنفس الاسم إن وجدت مسبقاً
        for ch_name in all_valid_names:
            matches = [c for c in guild.channels if c.name == ch_name]
            if len(matches) > 1:
                for duplicate in matches[1:]:
                    try:
                        await duplicate.delete(reason="Delete Duplicate Channel")
                    except Exception:
                        pass

        # 4. إعادة إرسال الواجهات الرئيسية بتنسيق Terminal احترافي

        # (أ) Arrival Terminal
        arrival_ch = created_channels.get("⚡-arrival-terminal")
        if arrival_ch:
            await arrival_ch.purge(limit=20)
            embed_arrival = discord.Embed(
                title="⚡ NEXUS ARCHITECTURE // ARRIVAL TERMINAL",
                description=(
                    "```yaml\n"
                    "SYSTEM STATUS  : ONLINE\n"
                    "FIREWALL MODE  : ENCRYPTED / ACTIVE\n"
                    "GRID PROTOCOL  : v4.0.8 CYBERPUNK NETWORK\n"
                    "```\n"
                    "**Welcome Operator to NEXUS ZERO.**\n"
                    "All incoming signals are monitored. Proceed to `#verify-access` to complete security clearance."
                ),
                color=discord.Color.from_rgb(57, 255, 20)
            )
            embed_arrival.set_footer(text="NEXUS CORE SYSTEM PROTOCOLS")
            await arrival_ch.send(embed=embed_arrival)

        # (ب) Verification Embed
        verify_ch = created_channels.get("🛡️-verify-access")
        if verify_ch:
            await verify_ch.purge(limit=20)
            embed_verify = discord.Embed(
                title="🛡️ IDENTITY & CLEARANCE AUTHORIZATION",
                description=(
                    "Access to internal network nodes is restricted to verified users only.\n\n"
                    "```yaml\n"
                    "Authorization: Click the button below\n"
                    "Assigned Clearance: [User] Verified\n"
                    "```"
                ),
                color=discord.Color.blue()
            )
            embed_verify.set_footer(text="Nexus Gateway Security • Verification Unit")
            await verify_ch.send(embed=embed_verify, view=views.VerifyView())

        # (ج) Ticket Support Embed
        ticket_ch = created_channels.get("🎟️-open-ticket")
        if ticket_ch:
            await ticket_ch.purge(limit=20)
            embed_ticket = discord.Embed(
                title="🎟️ SYSTEM OPERATOR HELPDESK",
                description=(
                    "Initialize a private encrypted terminal to communicate directly with server administrators.\n\n"
                    "```yaml\n"
                    "Service: Technical Support & Inquiries\n"
                    "Security: Encrypted Channel (User + Staff Only)\n"
                    "```"
                ),
                color=discord.Color.purple()
            )
            embed_ticket.set_footer(text="Nexus Support Terminals • Dispatch Center")
            await ticket_ch.send(embed=embed_ticket, view=views.TicketLaunchView())

        await interaction.followup.send("```yaml\n[SUCCESS] Grid fully purged, deduplicated, and initial interfaces synchronized!\n```")

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
