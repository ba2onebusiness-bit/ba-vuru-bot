import discord
from discord.ext import commands
import os
from flask import Flask
import threading

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 📩 BAŞVURU KANALI (DEĞİŞTİR!)
BASVURU_KANAL = 123456789012345678

# 🌐 Render için web server
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# 📝 BAŞVURU FORMU
class BasvuruModal(discord.ui.Modal, title="HOOWERS Başvuru"):
    isim = discord.ui.TextInput(label="İsmin")
    yas = discord.ui.TextInput(label="Yaşın")
    deneyim = discord.ui.TextInput(label="Deneyimin", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        kanal = bot.get_channel(BASVURU_KANAL)

        embed = discord.Embed(
            title="📩 Yeni Başvuru",
            color=0x2ecc71
        )

        embed.add_field(name="👤 İsim", value=self.isim.value, inline=False)
        embed.add_field(name="🎂 Yaş", value=self.yas.value, inline=False)
        embed.add_field(name="📚 Deneyim", value=self.deneyim.value, inline=False)

        embed.set_footer(text=f"{interaction.user} | {interaction.user.id}")

        await kanal.send(embed=embed)
        await interaction.response.send_message("✅ Başvurun gönderildi!", ephemeral=True)

# 🔘 BUTON
class BasvuruView(discord.ui.View):
    @discord.ui.button(label="Başvuru Oluştur", style=discord.ButtonStyle.primary)
    async def basvur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal())

# 📢 PANEL KOMUTU
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="HOOWERS",
        description="**[ ALIMLAR AÇIK ]**\n\nSende kazanan tarafın yanında olmak istiyorsan başvuru oluştur!",
        color=0x2f3136
    )

    # 📸 BURAYA KENDİ GÖRSELİNİ KOY
    embed.set_image(url="https://i.imgur.com/8XhFZQp.png")

    embed.set_footer(text="Başvuru sistemi")

    await ctx.send(embed=embed, view=BasvuruView())

# 🤖 BOT READY
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

bot.run(TOKEN)
