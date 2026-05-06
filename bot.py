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

KABUL_ROLLER = [
    1461791062078001183,
    1461791062027665509
]

BANNER_URL = "https://cdn.discordapp.com/attachments/777573115177336852/1499923963696906371/92425a4c-2a54-4acb-a58a-d91252053326.png"

# =======================
# INTENTS
# =======================
intents = discord.Intents.default()
intents.members = True
intents.guilds = True

# =======================
# BOT
# =======================
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Slash sync OK")

bot = MyBot()

# =======================
# DB
# =======================
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id TEXT PRIMARY KEY,
    panel_channel_id TEXT,
    log_channel_id TEXT
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
def is_admin(member: discord.Member):
    return any(r.id == ADMIN_ROLE_ID for r in member.roles)

def get_settings(guild_id: int):
    cursor.execute(
        "SELECT panel_channel_id, log_channel_id FROM settings WHERE guild_id = ?",
        (str(guild_id),)
    )
    return cursor.fetchone()

# =======================
# SETUP UI
# =======================
class SetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.panel = None
        self.log = None

    @discord.ui.channel_select(placeholder="📌 Panel kanalını seç")
    async def panel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.panel = select.values[0]
        await interaction.response.send_message(f"Panel seçildi: {self.panel.mention}", ephemeral=True)

    @discord.ui.channel_select(placeholder="📊 Log kanalını seç")
    async def log_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        self.log = select.values[0]
        await interaction.response.send_message(f"Log seçildi: {self.log.mention}", ephemeral=True)

    @discord.ui.button(label="🚀 Kur", style=discord.ButtonStyle.success)
    async def install(self, interaction: discord.Interaction, button: discord.ui.Button):

        if not self.panel or not self.log:
            return await interaction.response.send_message("Panel ve log seç", ephemeral=True)

        cursor.execute("""
        INSERT OR REPLACE INTO settings (guild_id, panel_channel_id, log_channel_id)
        VALUES (?, ?, ?)
        """, (str(interaction.guild.id), str(self.panel.id), str(self.log.id)))
        conn.commit()

        embed = discord.Embed(
            title="📢 CADEİM Başvuru",
            description="Kazanmak için tıkla 😁",
            color=0x5865F2
        )
        embed.set_image(url=BANNER_URL)

        await self.panel.send(embed=embed, view=TicketView())

        await interaction.response.send_message(
            f"Kuruldu!\nPanel: {self.panel.mention}\nLog: {self.log.mention}",
            ephemeral=True
        )

# =======================
# /SETUP
# =======================
@bot.tree.command(name="setup", description="Sistemi kur")
async def setup(interaction: discord.Interaction):

    if not is_admin(interaction.user):
        return await interaction.response.send_message("Yetkin yok", ephemeral=True)

    embed = discord.Embed(
        title="⚙️ Setup Panel",
        description="Panel ve log seç",
        color=0x5865F2
    )

    await interaction.response.send_message(embed=embed, view=SetupView(), ephemeral=True)

# =======================
# TICKET VIEW
# =======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru Aç", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"basvuru-{interaction.user.id}",
            topic=f"APPLICANT_ID:{interaction.user.id}",
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="📩 Başvuru Formu",
            description="\n".join([f"{i+1}) {q}" for i, q in enumerate(QUESTIONS)]),
            color=0x5865F2
        )
        embed.set_image(url=BANNER_URL)

        await channel.send(
            content=interaction.user.mention,
            embed=embed,
            view=TicketControlView()
        )

        await interaction.response.send_message(
            f"Ticket açıldı: {channel.mention}",
            ephemeral=True
        )

# =======================
# CONTROL VIEW
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

    async def finish(self, interaction: discord.Interaction, result: str):

        await interaction.response.defer()

        if not is_admin(interaction.user):
            return await interaction.followup.send("Yetkin yok", ephemeral=True)

        guild = interaction.guild
        channel = interaction.channel

        if not channel.topic or "APPLICANT_ID:" not in channel.topic:
            return await interaction.followup.send("User yok", ephemeral=True)

        user_id = int(channel.topic.split(":")[1])
        member = await guild.fetch_member(user_id)

        if result == "KABUL":
            roles = [guild.get_role(r) for r in KABUL_ROLLER]
            roles = [r for r in roles if r]
            await member.add_roles(*roles, reason="Başvuru Kabul")

        settings = get_settings(guild.id)
        log = guild.get_channel(int(settings[1])) if settings else None

        if log:
            embed = discord.Embed(
                title=f"Başvuru {result}",
                color=0x00ff00 if result == "KABUL" else 0xff0000
            )
            embed.add_field(name="Aday", value=member.mention)
            await log.send(embed=embed)

        await channel.delete()

# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

bot.run(TOKEN)
