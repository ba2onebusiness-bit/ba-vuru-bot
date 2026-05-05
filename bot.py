import discord
from discord.ext import commands
from flask import Flask
import threading
import os
import sqlite3

# =======================
# TOKEN CHECK (CRITICAL FIX)
# =======================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise Exception("TOKEN bulunamadı! Render env kontrol et.")

# =======================
# INTENTS
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# CONFIG
# =======================
BASVURU_KANAL = 123456789012345678
LOG_KANAL = 123456789012345678
KABUL_ROL_ID = 123456789012345678

# =======================
# DATABASE (SAFE MODE)
# =======================
conn = sqlite3.connect("basvurular.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS basvurular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    isim TEXT,
    yas TEXT,
    deneyim TEXT,
    youtube TEXT
)
""")
conn.commit()

def save_app(user_id, isim, yas, deneyim, youtube):
    cursor.execute("""
    INSERT INTO basvurular (user_id, isim, yas, deneyim, youtube)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, isim, yas, deneyim, youtube))
    conn.commit()

# =======================
# FLASK (SAFE THREAD)
# =======================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot aktif"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

threading.Thread(target=run_web, daemon=True).start()

# =======================
# TICKET CLOSE (FIXED)
# =======================
class TicketCloseView(discord.ui.View):

    @discord.ui.button(label="Ticket Kapat", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("⛔ Ticket kapanıyor...", ephemeral=True)

        await discord.utils.sleep_until(discord.utils.utcnow())

        await interaction.channel.delete()

# =======================
# ACTION VIEW
# =======================
class BasvuruActionView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__()
        self.user_id = int(user_id)

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = guild.get_member(self.user_id)
        role = guild.get_role(KABUL_ROL_ID)

        if user and role:
            await user.add_roles(role)

        try:
            await user.send("🎉 Başvurun kabul edildi!")
        except:
            pass

        await interaction.message.edit(content="✅ KABUL EDİLDİ", view=None)

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = guild.get_member(self.user_id)

        if user:
            try:
                await user.send("❌ Başvurun reddedildi.")
            except:
                pass

        await interaction.message.edit(content="❌ REDDEDİLDİ", view=None)

# =======================
# MODAL
# =======================
class BasvuruModal(discord.ui.Modal, title="Başvuru Formu"):

    isim = discord.ui.TextInput(label="İsim")
    yas = discord.ui.TextInput(label="Yaş")
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph)
    youtube = discord.ui.TextInput(label="YouTube", required=False)

    async def on_submit(self, interaction: discord.Interaction):

        save_app(
            str(interaction.user.id),
            self.isim.value,
            self.yas.value,
            self.deneyim.value,
            self.youtube.value or "Yok"
        )

        kanal = bot.get_channel(BASVURU_KANAL)

        embed = discord.Embed(title="📩 Yeni Başvuru", color=0x2ecc71)
        embed.add_field(name="İsim", value=self.isim.value, inline=False)
        embed.add_field(name="Yaş", value=self.yas.value, inline=False)
        embed.add_field(name="Deneyim", value=self.deneyim.value, inline=False)
        embed.add_field(name="YouTube", value=self.youtube.value or "Yok", inline=False)

        await kanal.send(embed=embed, view=BasvuruActionView(interaction.user.id))

        await interaction.response.send_message("Gönderildi", ephemeral=True)

# =======================
# BUTTONS
# =======================
class BasvuruView(discord.ui.View):

    @discord.ui.button(label="Başvuru Yap", style=discord.ButtonStyle.primary)
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal())

class TicketView(discord.ui.View):

    @discord.ui.button(label="Ticket Aç", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }

        ch = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        await ch.send("🎫 Ticket açıldı", view=TicketCloseView())

        await interaction.response.send_message(ch.mention, ephemeral=True)

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Aktif: {bot.user}")

bot.run(TOKEN)
