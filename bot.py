import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import os
import io

# =======================
# CONFIG
# =======================
TOKEN = os.getenv("TOKEN")

ADMIN_ROLE_ID = 1234567890  # ← kendi admin rol ID
GUILD_ID = 1234567890       # ← server ID

BASVURU_KANAL = 1234567890
ANNOUNCE_KANAL = 1234567890
LOG_KANAL = 1234567890

KABUL_ROL_ID_1 = 1234567890
KABUL_ROL_ID_2 = 1234567890

# =======================
# BOT
# =======================
intents = discord.Intents.default()
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync(guild=discord.Object(id=GUILD_ID))

bot = MyBot()

# =======================
# DATABASE
# =======================
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    aktiflik TEXT,
    yas TEXT,
    pc TEXT,
    fivem TEXT
)
""")
conn.commit()

def save_app(data):
    cursor.execute("""
    INSERT INTO applications (user_id, aktiflik, yas, pc, fivem)
    VALUES (?, ?, ?, ?, ?)
    """, data)
    conn.commit()

# =======================
# CHECK ADMIN
# =======================
def is_admin(interaction: discord.Interaction):
    return any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles)

# =======================
# TRANSCRIPT
# =======================
async def create_transcript(channel: discord.TextChannel):
    msgs = []
    async for m in channel.history(limit=None, oldest_first=True):
        content = m.content or ""
        msgs.append(f"{m.author}: {content}")

    html = "<html><body style='background:#2c2f33;color:white'>"
    html += "<h2>Ticket Transcript</h2><hr>"

    for m in msgs:
        html += f"<p>{m}</p><hr>"

    html += "</body></html>"

    file = io.BytesIO(html.encode())
    return discord.File(file, filename=f"{channel.name}.html")

# =======================
# ACTION VIEW
# =======================
class ActionView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = int(user_id)

    async def get_user(self, guild):
        try:
            return await guild.fetch_member(self.user_id)
        except:
            return guild.get_member(self.user_id)

    @discord.ui.button(label="KABUL", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = await self.get_user(interaction.guild)
        if not user:
            return

        roles = [
            interaction.guild.get_role(KABUL_ROL_ID_1),
            interaction.guild.get_role(KABUL_ROL_ID_2)
        ]

        await user.add_roles(*[r for r in roles if r])

        try:
            await user.send("🎉 Başvurun kabul edildi!")
        except:
            pass

        ch = bot.get_channel(ANNOUNCE_KANAL)
        await ch.send(f"✅ {user.mention} BAŞVURUSU KABUL EDİLDİ")

        await interaction.message.edit(content="KABUL EDİLDİ", view=None)

    @discord.ui.button(label="RED", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = await self.get_user(interaction.guild)
        if not user:
            return

        try:
            await user.send("❌ Reddedildin.")
        except:
            pass

        ch = bot.get_channel(ANNOUNCE_KANAL)
        await ch.send(f"❌ {user.mention} BAŞVURUSU REDDEDİLDİ")

        await interaction.message.edit(content="REDDEDİLDİ", view=None)

# =======================
# MODAL
# =======================
class BasvuruModal(discord.ui.Modal, title="Başvuru Formu"):

    aktiflik = discord.ui.TextInput(label="Günlük aktiflik")
    yas = discord.ui.TextInput(label="Yaş")
    pc = discord.ui.TextInput(label="PC")
    fivem = discord.ui.TextInput(label="FiveM saat")

    async def on_submit(self, interaction: discord.Interaction):

        save_app((
            str(interaction.user.id),
            self.aktiflik.value,
            self.yas.value,
            self.pc.value,
            self.fivem.value
        ))

        ch = bot.get_channel(BASVURU_KANAL)

        embed = discord.Embed(title="Yeni Başvuru", color=0x00ff00)
        embed.add_field(name="Aktiflik", value=self.aktiflik.value)
        embed.add_field(name="Yaş", value=self.yas.value)
        embed.add_field(name="PC", value=self.pc.value)
        embed.add_field(name="FiveM", value=self.fivem.value)

        await ch.send(embed=embed, view=ActionView(interaction.user.id))

        await interaction.response.send_message("Gönderildi", ephemeral=True)

# =======================
# TICKET
# =======================
class TicketView(discord.ui.View):

    @discord.ui.button(label="Ticket Aç", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        ch = await interaction.guild.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites=overwrites
        )

        await ch.send("Ticket açıldı")

        await interaction.response.send_message(ch.mention, ephemeral=True)

class TicketClose(discord.ui.View):

    @discord.ui.button(label="Kapat", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        log = bot.get_channel(LOG_KANAL)
        file = await create_transcript(interaction.channel)

        await log.send(file=file)

        await interaction.channel.delete()

# =======================
# SLASH COMMANDS
# =======================

@app_commands.command(name="basvuru")
async def basvuru(interaction: discord.Interaction):
    await interaction.response.send_modal(BasvuruModal())

@app_commands.command(name="basvuru-panel")
async def panel(interaction: discord.Interaction):

    if not is_admin(interaction):
        return await interaction.response.send_message("Yetkin yok", ephemeral=True)

    embed = discord.Embed(
        title="Başvuru Panel",
        description="Başvurmak için butona bas",
        color=0x2f3136
    )

    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("Panel kuruldu", ephemeral=True)

bot.tree.add_command(basvuru)
bot.tree.add_command(panel)

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Aktif: {bot.user}")

bot.run(TOKEN)
