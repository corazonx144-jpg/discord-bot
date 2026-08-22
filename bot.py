import discord
from discord.ext import commands
from discord.ui import Button, View
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# تشغيل سيرفر ويب وهمي في الخلفية لترضية منصة Render وتجنب أخطاء البورتات
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"SmartHub Bot is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# بدء السيرفر الوهمي في خيط منفصل (Background Thread)
t = threading.Thread(target=run_web_server)
t.daemon = True
t.start()

# إعدادات بوت ديسكورد
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[-] SYSTEM ONLINE: Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("[-] CORE STATUS: SECURE & ENCRYPTED")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="[SYSTEM SECURE] | Type !help"))

@bot.event
async def on_member_join(member):
    for channel in member.guild.text_channels:
        if "terminal" in channel.name or "welcome" in channel.name:
            embed = discord.Embed(
                title="⚡ [SYSTEM ACCESS GRANTED] ⚡",
                description=f"Welcome to the mainframe, <@{member.id}>.\n\n> *\"The matrix has you now... Make sure your firewall is up.\"*",
                color=0x00FF66
            )
            embed.add_field(name="[+] Target ID", value=f"`{member.name}`", inline=True)
            embed.add_field(name="[+] Security Level", value="`Level 0 - Guest`", inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text="SMARTHUB CORE SYSTEM v4.0.4", icon_url=bot.user.display_avatar.url)
            
            view = View()
            button = Button(label="Acknowledge Protocols", style=discord.ButtonStyle.green, emoji="🛡️")
            
            async def button_callback(interaction):
                await interaction.response.send_message(f"Access acknowledged by <@{interaction.user.id}>. Welcome aboard, agent.", ephemeral=True)
                
            button.callback = button_callback
            view.add_item(button)
            
            await channel.send(embed=embed, view=view)
            break

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"```[SYSTEM] purged {amount} packets from the sector.```")
    await msg.delete(delay=3)

@clear.error
async def clear_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("```[ERROR] Access Denied: You lack administrator privileges.```", delete_after=5)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
