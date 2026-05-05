import discord
from discord.ext import commands
from flask import Flask, request, session, redirect
import threading
import sqlite3
import os
import io
from datetime import datetime

# =======================
# CONFIG
# =======================
TOKEN = os.getenv("TOKEN")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ba2onekral")
SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")

BASVURU_KANAL = 1499919581253472266
LOG_KANAL = 1461791063361454290
ANNOUNCE_KANAL = 1461791063361454291

KABUL_ROL_ID_1 = 1461791062078001183
KABUL_ROL_ID_2 = 1461791062027665509

# =======================
# BOT
# =======================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# DATABASE
# =======================
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    aktiflik TEXT,
    yas TEXT,
    pc TEXT,
    olusumlar TEXT,
    fivem TEXT,
    map TEXT,
    referans TEXT,
    pov TEXT
)
""")
conn.commit()

def save_app(data):
    cursor.execute("""
    INSERT INTO applications (
        user_id, aktiflik, yas, pc, olusumlar, fivem, map, referans, pov
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data)
    conn.commit()

# =======================
# TRANSCRIPT
# =======================
async def create_transcript(channel: discord.TextChannel):

    messages = []
    async for msg in channel.history(limit=None, oldest_first=True):
        messages.append(msg)

    html = f"""
    <html>
    <body style="background:#2c2f33;color:white;font-family:Arial">
    <h2>Ticket: {channel.name}</h2><hr>
    """

    for msg in messages:
        time = msg.created_at.strftime("%Y-%m-%d %H:%M")
        content = msg.content if msg.content else ""
        html += f"<div><b>{msg.author}</b> [{time}]<br>{content}</div><hr>"

    html += "</body></html>"

    file = io.BytesIO(html.encode("utf-8"))
    return discord.File(file, filename=f"{channel.name}.html")

# =======================
# FLASK DASHBOARD
# =======================
app = Flask(__name__)
app.secret_key = SECRET_KEY

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["auth"] = True
            return redirect("/dashboard")
        return "Wrong password"

    return """
    <h2>Admin Login</h2>
    <form method="post">
        <input name="password" type="password">
        <button>Login</button>
    </form>
    """

@app.route("/dashboard")
def dashboard():
    if not session.get("auth"):
        return redirect("/")

    cursor.execute("SELECT * FROM applications ORDER BY id DESC")
    rows = cursor.fetchall()

    html = "<h2>📊 Başvurular</h2><a href='/logout'>Logout</a><br><br>"
    html += "<table border='1' cellpadding='5'>"

    html += """
    <tr>
        <th>ID</th><th>User</th><th>Aktiflik</th><th>Yaş</th>
        <th>PC</th><th>Oluşum</th><th>FiveM</th><th>Map</th>
        <th>Referans</th><th>POV</th>
    </tr>
    """

    for r in rows:
        html += "<tr>" + "".join([f"<td>{x}</td>" for x in r]) + "</tr>"

    html += "</table>"
    return html

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

# =======================
# ACTION VIEW
# =======================
class ActionView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = int(user_id)  # FIX 1

    @discord.ui.button(label="Kabul", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        try:
            user = await guild.fetch_member(self.user_id)
        except:
            return

        role_ids = [KABUL_ROL_ID_1, KABUL_ROL_ID_2]
        roles = []

        for rid in role_ids:
            role = guild.get_role(rid)
            if role:
                roles.append(role)

        if roles:  # FIX 2
            await user.add_roles(*roles)

        try:
            await user.send("🎉 Başvurun kabul edildi!")
        except:
            pass

        channel = bot.get_channel(ANNOUNCE_KANAL)
        if channel:  # FIX 3
            await channel.send(f"✅ {user.mention} BAŞVURUSU KABUL EDİLDİ 🎉")

        await interaction.message.edit(content="✅ KABUL EDİLDİ", view=None)

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        try:
            user = await guild.fetch_member(self.user_id)
        except:
            return

        try:
            await user.send("❌ Başvurun reddedildi.")
        except:
            pass

        channel = bot.get_channel(ANNOUNCE_KANAL)
        if channel:
            await channel.send(f"❌ {user.mention} BAŞVURUSU REDDEDİLDİ")

        await interaction.message.edit(content="❌ REDDEDİLDİ", view=None)

# =======================
# MODAL
# =======================
class BasvuruModal(discord.ui.Modal, title="MDRP Başvuru"):

    aktiflik = discord.ui.TextInput(label="Günlük aktiflik")
    yas = discord.ui.TextInput(label="Yaş")
    pc = discord.ui.TextInput(label="PC", style=discord.TextStyle.paragraph)
    olusumlar = discord.ui.TextInput(label="Oluşumlar", style=discord.TextStyle.paragraph)
    fivem = discord.ui.TextInput(label="FiveM saat")
    map = discord.ui.TextInput(label="Map bilgisi")
    referans = discord.ui.TextInput(label="Referans")
    pov = discord.ui.TextInput(label="POV", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):

        save_app((
            str(interaction.user.id),
            self.aktiflik.value,
            self.yas.value,
            self.pc.value,
            self.olusumlar.value,
            self.fivem.value,
            self.map.value,
            self.referans.value,
            self.pov.value
        ))

        channel = bot.get_channel(BASVURU_KANAL)

        if channel:
            embed = discord.Embed(title="📩 Yeni Başvuru", color=0x2ecc71)

            embed.add_field(name="Aktiflik", value=self.aktiflik.value, inline=False)
            embed.add_field(name="Yaş", value=self.yas.value, inline=False)
            embed.add_field(name="PC", value=self.pc.value, inline=False)
            embed.add_field(name="Oluşum", value=self.olusumlar.value, inline=False)
            embed.add_field(name="FiveM", value=self.fivem.value, inline=False)
            embed.add_field(name="Map", value=self.map.value, inline=False)
            embed.add_field(name="Referans", value=self.referans.value, inline=False)
            embed.add_field(name="POV", value=self.pov.value, inline=False)

            await channel.send(embed=embed, view=ActionView(interaction.user.id))

        await interaction.response.send_message("✅ Gönderildi", ephemeral=True)

# =======================
# TICKET CLOSE + TRANSCRIPT
# =======================
class TicketClose(discord.ui.View):

    @discord.ui.button(label="Ticket Kapat", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        log = bot.get_channel(LOG_KANAL)

        if log:
            file = await create_transcript(interaction.channel)
            await log.send(content=f"📁 Ticket kapatıldı: {interaction.channel.name}", file=file)

        await interaction.response.send_message("⛔ Kapatılıyor...", ephemeral=True)
        await interaction.channel.delete()

# =======================
# BUTTON PANELS
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

        await ch.send("🎫 Ticket açıldı", view=TicketClose())

        await interaction.response.send_message(ch.mention, ephemeral=True)

# =======================
# COMMANDS
# =======================
@bot.command()
async def basvuru(ctx):
    await ctx.message.delete()
    await ctx.send("📩 Başvuru sistemi", view=BasvuruView())

@bot.command()
async def ticket(ctx):
    await ctx.send("🎫 Ticket sistemi", view=TicketView())

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Aktif: {bot.user}")

bot.run(TOKEN)
