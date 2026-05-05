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

# =======================
# BOT CLASS
# =======================
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):

        guild = discord.Object(id=GUILD_ID)

        # 🔥 GLOBAL + GUILD DOUBLE SYNC (100% garanti fix)
        try:
            await self.tree.sync(guild=guild)
            print("✅ Guild slash sync OK")
        except Exception as e:
            print("Guild sync error:", e)

        try:
            await self.tree.sync()
            print("🌍 Global slash sync OK")
        except Exception as e:
            print("Global sync error:", e)

bot = Bot()

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
# ACTIVE TICKETS
# =======================
active_tickets = set()

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
def get_count(user_id: str):
    cursor.execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

# =======================
# TICKET VIEW
# =======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru Aç", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        if interaction.user.id in active_tickets:
            return await interaction.response.send_message(
                "❌ Zaten aktif başvurun var!",
                ephemeral=True
            )

        active_tickets.add(interaction.user.id)

        count = get_count(str(interaction.user.id))

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"basvuru-{interaction.user.name}".lower(),
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📩 Başvuru Formu",
            description="\n".join([f"{i+1}) {q}" for i, q in enumerate(QUESTIONS)]),
            color=0x5865F2
        )

        embed.add_field(
            name="📊 Önceki Başvurular",
            value=str(count),
            inline=False
        )

        await channel.send(content=interaction.user.mention, embed=embed, view=TicketControlView())

        await interaction.response.send_message(
            f"🎫 Ticket açıldı: {channel.mention}",
            ephemeral=True
        )

# =======================
# ADMIN VIEW
# =======================
class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="KABUL", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction, "KABUL")

    @discord.ui.button(label="RED", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.finish(interaction, "RED")

    @discord.ui.button(label="KAPAT", style=discord.ButtonStyle.secondary)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        active_tickets.discard(interaction.user.id)
        await interaction.channel.delete()

    async def finish(self, interaction, result: str):

        if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
            return await interaction.response.send_message("Yetkin yok", ephemeral=True)

        channel = interaction.channel
        log = bot.get_channel(LOG_CHANNEL_ID)

        messages = [m async for m in channel.history(limit=30)]
        messages.reverse()

        content = "\n".join([f"{m.author}: {m.content}" for m in messages if m.content])

        embed = discord.Embed(
            title=f"📁 Başvuru {result}",
            color=0x00ff00 if result == "KABUL" else 0xff0000
        )

        embed.add_field(name="Cevaplar", value=content[:1000] or "Boş")

        if log:
            await log.send(embed=embed)

        active_tickets.discard(channel.topic or 0)

        await interaction.response.send_message("Kapatılıyor...", ephemeral=True)
        await channel.delete()

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
    print(f"Bot aktif: {bot.user}")
    print("Slash commands ready!")

bot.run(TOKEN)
