import os
import discord
from discord.ext import commands

# إعداد الصلاحيات الأساسية للبوت
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

# تعريف البوت وتحديد بادئة الأوامر (مثل !)
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
  print(f"تم تسجيل الدخول بنجاح باسم: {bot.user.name}")
  print("البوت يعمل الآن وجاهز لخدمتك!")


# أمر تجريبي بسيط لكتابته في السيرفر
@bot.command()
async def hello(ctx):
  await ctx.send("أهلاً بك! أنا أعمل بكفاءة تامة 🚀")


# قراءة التوكن بأمان من إعدادات الاستضافة
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN is None:
  print("خطأ: لم يتم العثور على متغير البيئة DISCORD_TOKEN!")
else:
  bot.run(TOKEN)