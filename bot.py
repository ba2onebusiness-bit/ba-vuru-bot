import discord
from discord.ext import commands
import sqlite3
import os

# =======================
# CONFIG
# =======================
TOKEN = os.getenv("TOKEN")

ADMIN_ROLE_ID = 0  # Admin rol ID koymak istersen buraya yaz

BASVURU_KANAL = 1499919581253472266
ANNOUNCE_KANAL = 1461791063361454291

KABUL_ROL_ID_1 = 1461791062078001183
KABUL_ROL_ID_2 = 1461791062027665509

# =======================
# BOT SETUP
# =======================
intents = discord.Intents.default()
intents.members = True
intents.message_content = False

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
# KABUL / RED VIEW
# =======================
class ActionView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = int(user_id)

    async def get_user(self, guild: discord.Guild):
        member = guild.get_member(self.user_id)

        if member is None:
            try:
                member = await guild.fetch_member(self.user_id)
            except discord.NotFound:
                return None

        return member

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "❌ Bu işlem sadece sunucuda kullanılabilir.",
                ephemeral=True
            )

        user = await self.get_user(guild)

        if user is None:
            return await interaction.response.send_message(
                "❌ Kullanıcı sunucuda bulunamadı.",
                ephemeral=True
            )

        roles = []

        for role_id in [KABUL_ROL_ID_1, KABUL_ROL_ID_2]:
            role = guild.get_role(role_id)
            if role:
                roles.append(role)

        if roles:
            try:
                await user.add_roles(*roles, reason="Başvuru kabul edildi")
            except discord.Forbidden:
                return await interaction.response.send_message(
                    "❌ Rol veremedim. Botun rolü, vereceği rollerden yukarıda olmalı.",
                    ephemeral=True
                )

        try:
            await user.send("🎉 Tebrikler! Başvurun kabul edildi.")
        except discord.Forbidden:
            pass

        announce_channel = bot.get_channel(ANNOUNCE_KANAL)

        if announce_channel:
            await announce_channel.send(f"✅ {user.mention} başvurusu kabul edildi 🎉")

        await interaction.message.edit(content="✅ **BAŞVURU KABUL EDİLDİ**", embed=interaction.message.embeds[0], view=None)

        await interaction.response.send_message(
            "✅ Başvuru kabul edildi.",
            ephemeral=True
        )

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "❌ Bu işlem sadece sunucuda kullanılabilir.",
                ephemeral=True
            )

        user = await self.get_user(guild)

        if user is None:
            return await interaction.response.send_message(
                "❌ Kullanıcı sunucuda bulunamadı.",
                ephemeral=True
            )

        try:
            await user.send("❌ Başvurun reddedildi.")
        except discord.Forbidden:
            pass

        announce_channel = bot.get_channel(ANNOUNCE_KANAL)

        if announce_channel:
            await announce_channel.send(f"❌ {user.mention} başvurusu reddedildi.")

        await interaction.message.edit(content="❌ **BAŞVURU REDDEDİLDİ**", embed=interaction.message.embeds[0], view=None)

        await interaction.response.send_message(
            "❌ Başvuru reddedildi.",
            ephemeral=True
        )


# =======================
# 2. MODAL
# =======================
class BasvuruModal2(discord.ui.Modal, title="MDRP Başvuru - 2. Aşama"):
    def __init__(self, first_data: dict):
        super().__init__()
        self.first_data = first_data

    fivem = discord.ui.TextInput(
        label="FiveM saatin kaç?",
        placeholder="Örnek: 1500 saat",
        required=True,
        max_length=100
    )

    map_bilgisi = discord.ui.TextInput(
        label="Map bilgin nasıl?",
        placeholder="Örnek: İyi / Orta / Çok iyi",
        required=True,
        max_length=300
    )

    referans = discord.ui.TextInput(
        label="Referansın var mı?",
        placeholder="Varsa isim yaz, yoksa 'Yok' yaz",
        required=True,
        max_length=300
    )

    pov = discord.ui.TextInput(
        label="POV / Video linki",
        placeholder="Varsa link at, yoksa 'Yok' yaz",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            **self.first_data,
            "fivem": self.fivem.value,
            "map": self.map_bilgisi.value,
            "referans": self.referans.value,
            "pov": self.pov.value
        }

        save_app((
            str(interaction.user.id),
            data["aktiflik"],
            data["yas"],
            data["pc"],
            data["olusumlar"],
            data["fivem"],
            data["map"],
            data["referans"],
            data["pov"]
        ))

        channel = bot.get_channel(BASVURU_KANAL)

        if channel is None:
            return await interaction.response.send_message(
                "❌ Başvuru kanalı bulunamadı. Kanal ID'sini kontrol et.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="📩 Yeni MDRP Başvurusu",
            description=f"Başvuru sahibi: {interaction.user.mention}",
            color=0x2ecc71
        )

        embed.add_field(name="👤 Kullanıcı", value=f"{interaction.user} / `{interaction.user.id}`", inline=False)
        embed.add_field(name="⏰ Günlük Aktiflik", value=data["aktiflik"], inline=False)
        embed.add_field(name="🎂 Yaş", value=data["yas"], inline=False)
        embed.add_field(name="💻 PC Bilgisi", value=data["pc"], inline=False)
        embed.add_field(name="👥 Önceki Oluşumlar", value=data["olusumlar"], inline=False)
        embed.add_field(name="🎮 FiveM Saati", value=data["fivem"], inline=False)
        embed.add_field(name="🗺️ Map Bilgisi", value=data["map"], inline=False)
        embed.add_field(name="📌 Referans", value=data["referans"], inline=False)
        embed.add_field(name="🎥 POV", value=data["pov"], inline=False)

        embed.set_footer(text="Kabul veya red işlemi için aşağıdaki butonları kullan.")

        await channel.send(
            embed=embed,
            view=ActionView(interaction.user.id)
        )

        await interaction.response.send_message(
            "✅ Başvurun başarıyla gönderildi.",
            ephemeral=True
        )


# =======================
# 1. MODAL
# =======================
class BasvuruModal1(discord.ui.Modal, title="MDRP Başvuru - 1. Aşama"):
    aktiflik = discord.ui.TextInput(
        label="Günlük aktifliğin kaç saat?",
        placeholder="Örnek: Günde 5-6 saat aktifim",
        required=True,
        max_length=200
    )

    yas = discord.ui.TextInput(
        label="Yaşın kaç?",
        placeholder="Örnek: 18",
        required=True,
        max_length=50
    )

    pc = discord.ui.TextInput(
        label="PC özelliklerin nasıl?",
        placeholder="İşlemci, ekran kartı, RAM vb.",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    olusumlar = discord.ui.TextInput(
        label="Daha önce bulunduğun oluşumlar",
        placeholder="Varsa yaz, yoksa 'Yok' yaz",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        first_data = {
            "aktiflik": self.aktiflik.value,
            "yas": self.yas.value,
            "pc": self.pc.value,
            "olusumlar": self.olusumlar.value
        }

        await interaction.response.send_modal(BasvuruModal2(first_data))


# =======================
# PANEL VIEW
# =======================
class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvuru Yap", style=discord.ButtonStyle.primary, emoji="📩")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal1())


# =======================
# SLASH COMMAND
# =======================
@bot.tree.command(name="basvuru-panel", description="Başvuru panelini gönderir.")
async def basvuru_panel(interaction: discord.Interaction):
    if interaction.guild is None:
        return await interaction.response.send_message(
            "❌ Bu komut sadece sunucuda kullanılabilir.",
            ephemeral=True
        )

    if ADMIN_ROLE_ID != 0:
        if not any(role.id == ADMIN_ROLE_ID for role in interaction.user.roles):
            return await interaction.response.send_message(
                "❌ Bu komutu kullanmak için yetkin yok.",
                ephemeral=True
            )

    embed = discord.Embed(
        title="📩 MDRP Başvuru Sistemi",
        description=(
            "Başvuru yapmak için aşağıdaki butona tıkla.\n\n"
            "Başvuru 2 aşamadan oluşur. Soruları eksiksiz doldurman gerekir."
        ),
        color=0x2f3136
    )

    embed.set_footer(text="MDRP Başvuru Paneli")

    await interaction.channel.send(
        embed=embed,
        view=PanelView()
    )

    await interaction.response.send_message(
        "✅ Başvuru paneli gönderildi.",
        ephemeral=True
    )


# =======================
# READY
# =======================
@bot.event
async def on_ready():
    try:
        bot.add_view(PanelView())
        await bot.tree.sync()
        print(f"✅ Bot aktif: {bot.user}")
    except Exception as e:
        print(f"❌ Sync hatası: {e}")


# =======================
# RUN
# =======================
if TOKEN is None:
    print("❌ TOKEN bulunamadı. Ortam değişkeni olarak TOKEN ekle.")
else:
    bot.run(TOKEN)
