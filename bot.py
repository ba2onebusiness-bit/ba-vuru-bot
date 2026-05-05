import discord
from discord.ext import commands
import os
from flask import Flask
import threading

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

BASVURU_KANAL = 1501295304530722911

# Flask (Render için)
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# Modal
class BasvuruModal(discord.ui.Modal, title="Başvuru"):
    isim = discord.ui.TextInput(label="İsim")
    yas = discord.ui.TextInput(label="Yaş")
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        kanal = bot.get_channel(BASVURU_KANAL)

        embed = discord.Embed(title="Yeni Başvuru", color=0x2ecc71)
        embed.add_field(name="İsim", value=self.isim.value, inline=False)
        embed.add_field(name="Yaş", value=self.yas.value, inline=False)
        embed.add_field(name="Deneyim", value=self.deneyim.value, inline=False)

        await kanal.send(embed=embed)
        await interaction.response.send_message("Başvuru gönderildi!", ephemeral=True)

# Buton
class BasvuruView(discord.ui.View):
    @discord.ui.button(label="Başvuru Oluştur", style=discord.ButtonStyle.primary)
    async def basvur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal())

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="Başvuru Paneli",
        description="Başvuru yapmak için butona bas",
        color=0x8e44ad
    )
    await ctx.send(embed=embed, view=BasvuruView())

bot.run(TOKEN)
