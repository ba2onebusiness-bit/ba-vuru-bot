import discord
from discord.ext import commands
import os
from flask import Flask
import threading

TOKEN = os.getenv("TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# :envelope_with_arrow: BAŞVURU KANALI (DEĞİŞTİR)
BASVURU_KANAL = 1501295304530722911

# :globe_with_meridians: Render için web server
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_web).start()

# :pencil: FORM
class BasvuruModal(discord.ui.Modal, title="HOOWERS Başvuru"):
    isim = discord.ui.TextInput(label="İsmin")
    yas = discord.ui.TextInput(label="Yaşın")
    deneyim = discord.ui.TextInput(label="Deneyimin", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):
        kanal = bot.get_channel(BASVURU_KANAL)

        embed = discord.Embed(title=":envelope_with_arrow: Yeni Başvuru", color=0x2ecc71)
        embed.add_field(name=":bust_in_silhouette: İsim", value=self.isim.value, inline=False)
        embed.add_field(name=":birthday: Yaş", value=self.yas.value, inline=False)
        embed.add_field(name=":books: Hangi Ekiplerde oynadın", value=self.deneyim.value, inline=False)
        embed.add_field(name="Youtube video linki (mdrp)", value=self.yas.value, inline=False)
        embed.set_footer(text=f"{interaction.user} | {interaction.user.id}")

        await kanal.send(embed=embed)
        await interaction.response.send_message(":white_check_mark: Başvurun gönderildi!", ephemeral=True)

# :radio_button: BUTON
class BasvuruView(discord.ui.View):
    @discord.ui.button(label="Başvuru Oluştur", style=discord.ButtonStyle.primary)
    async def basvur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal())

# :loudspeaker: PANEL KOMUTU (TEK MESAJ)
@bot.command()
async def basvurukur(ctx):
    # komutu yazanı sil → spam/çift görünüm engellenir
    await ctx.message.delete()

    embed = discord.Embed(
        title="CADEİM",
        description="**[ ALIMLAR AÇIK ]**\n\nBizle Olan Kazanır Tıkla Kazan!",
        color=0x2f3136
    )

    embed.set_image(
        url="https://cdn.discordapp.com/attachments/777573115177336852/1501328247219294208/c0eaa56ace2a830ccea8e17a3bde2aee.jpg?ex=69fbac63&is=69fa5ae3&hm=c2260bae740bf429bf3d358d96b936ca57708604eccab2eb5ecc8ba1196a3304&animated=true"
    )

    embed.set_footer(text="Başvuru sistemi")

    await ctx.send(embed=embed, view=BasvuruView())

# :robot: BOT READY
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

bot.run(TOKEN)
