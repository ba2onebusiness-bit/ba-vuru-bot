import discord
from discord.ext import commands
import os
import sqlite3

# =======================
# CONFIG
# =======================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN bulunamadı")

GUILD_ID = 1461791061419622402
ADMIN_ROLE_ID = 1461791062078001187
LOG_CHANNEL_ID = 1461791063361454291

# =======================
# INTENTS
# =======================
intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# MEMORY (active tickets)
# =======================
active_tickets = set()

# =======================
# DB
# =======================
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    answers TEXT
)
""")
conn.commit()

# =======================
# QUESTIONS
# =======================
QUESTIONS = [
    "MD geçmişiniz var mı?",
    "Günlük aktiflik süreniz?",
    "Daha önce hangi ekiplerde oynadınız?",
    "MD kill POV atınız (POV yoksa RED)",
    "Referansınız var mı?"
]

# =======================
# HELPERS
# =======================
def get_application_count(user_id: str):
    cursor.execute(
        "SELECT COUNT(*) FROM applications WHERE user_id = ?",
        (user_id,)
    )
    return cursor.fetchone()[0]

def save_application(user_id: str, content: str):
    cursor.execute(
        "INSERT INTO applications (user_id, answers) VALUES (?, ?)",
        (user_id, content)
    )
    conn.commit()

# =======================
# TICKET CONTROL
# =======================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="KABUL", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Yetkin yok", ephemeral=True)

        await self.finish(interaction, "KABUL")

    @discord.ui.button(label="RED", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Yetkin yok", ephemeral=True)

        await self.finish(interaction, "RED")

    @discord.ui.button(label="KAPAT", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        active_tickets.discard(interaction.channel.id)
        await interaction.channel.delete()

    async def finish(self, interaction, result: str):

        channel = interaction.channel
        log = bot.get_channel(LOG_CHANNEL_ID)

        messages = [m async for m in channel.history(limit=30)]
        messages.reverse()

        content = "\n".join([f"{m.author}: {m.content}" for m in messages if m.content])

        embed = discord.Embed(
            title=f"📁 Başvuru {result}",
            color=0x00ff00 if result == "KABUL" else 0xff0000
        )

        embed.add_field(name="Cevaplar", value=content[:1000] or "Boş", inline=False)

        if log:
            await log.send(embed=embed)

        active_tickets.discard(channel.id)

        await interaction.response.send_message("İşlem tamamlandı, kanal kapanıyor...", ephemeral=True)
        await channel.delete()

# =======================
# TICKET VIEW
# =======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru Aç", style=discord.ButtonStyle.primary)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):

        user = interaction.user

        # ⛔ ACTIVE TICKET CHECK
        if user.id in active_tickets:
            return await interaction.response.send_message(
                "❌ Zaten açık bir başvurun var!",
                ephemeral=True
            )

        count = get_application_count(str(user.id))

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"basvuru-{user.name}".lower(),
            overwrites=overwrites
        )

        active_tickets.add(user.id)

        embed = discord.Embed(
            title="📩 Başvuru Formu",
            description="\n".join([f"{i+1}) {q}" for i, q in enumerate(QUESTIONS)]),
            color=0x5865F2
        )

        embed.add_field(
            name="📊 Önceki Başvuruların",
            value=f"{count}",
            inline=False
        )

        await channel.send(content=user.mention, embed=embed, view=TicketControlView())

        await interaction.response.send_message(
            f"🎫 Ticket açıldı: {channel.mention}",
            ephemeral=True
        )

# =======================
# SLASH COMMAND
# =======================
@bot.tree.command(name="basvuru-panel", description="Başvuru paneli kurar")
async def panel(interaction: discord.Interaction):

    if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("Yetkin yok", ephemeral=True)

    embed = discord.Embed(
        title="📢 MD Başvuru Sistemi",
        description="Başvurmak için butona tıkla",
        color=0x5865F2
    )

    await interaction.response.send_message(embed=embed, view=TicketView())

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    print(f"Bot aktif: {bot.user}")

bot.run(TOKEN)
