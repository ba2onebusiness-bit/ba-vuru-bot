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

# 🎯 KABUL ROLLERİ (2 adet)
KABUL_ROLLER = [
    1461791062078001183,
    1461791062027665509
]

BANNER_URL = "https://media.discordapp.net/attachments/777573115177336852/1499923963696906371/92425a4c-2a54-4acb-a58a-d91252053326.png"

# =======================
# INTENTS
# =======================
intents = discord.Intents.default()
intents.members = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Slash sync OK")

bot = MyBot()

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
def get_count(user_id: str):
    cursor.execute("SELECT COUNT(*) FROM applications WHERE user_id = ?", (user_id,))
    return cursor.fetchone()[0]

# =======================
# TICKET CONTROL
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

        embed.add_field(name="Cevaplar", value=content[:1000] or "Boş", inline=False)

        # =======================
        # KABUL = 2 ROL VER
        # =======================
        if result == "KABUL":
            member = interaction.guild.get_member(int(channel.name.split("-")[-1])) or None

            # fallback: channel owner bulma
            async for msg in channel.history(limit=1, oldest_first=True):
                member = msg.author

            if member:
                roles = []
                for rid in KABUL_ROLLER:
                    role = interaction.guild.get_role(rid)
                    if role:
                        roles.append(role)

                if roles:
                    await member.add_roles(*roles)

        if log:
            await log.send(embed=embed)

        await interaction.response.send_message("Kapatılıyor...", ephemeral=True)
        await channel.delete()

# =======================
# TICKET VIEW
# =======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        count = get_count(str(interaction.user.id))

        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await interaction.guild.create_text_channel(
            name=f"basvuru-{interaction.user.id}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📩 Başvuru Formu",
            description="\n".join([f"{i+1}) {q}" for i, q in enumerate(QUESTIONS)]),
            color=0x5865F2
        )

        embed.add_field(
            name="📊 Toplam Başvuruların",
            value=str(count),
            inline=False
        )

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView()
        )

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
        title="📢 CADEİM Başvuru",
        description="Kazanan tarafta olmak için aşağıdaki butona tıkla 😁",
        color=0x5865F2
    )

    embed.set_image(url=BANNER_URL)

    await interaction.response.send_message(embed=embed, view=TicketView())

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

bot.run(TOKEN)
