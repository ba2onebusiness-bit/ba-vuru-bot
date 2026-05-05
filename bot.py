import discord
from discord.ext import commands
import os
import sqlite3

# =======================
# CONFIG
# =======================
TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise RuntimeError("TOKEN bulunamadı (Render environment variables)")

GUILD_ID = 1461791061419622402
ADMIN_ROLE_ID = 1461791062078001187

BASVURU_KANAL = 1499919581253472266
ANNOUNCE_KANAL = 1461791063361454291

KABUL_ROL_1 = 1461791062078001183
KABUL_ROL_2 = 1461791062027665509


# =======================
# INTENTS
# =======================
intents = discord.Intents.default()
intents.members = True

# =======================
# BOT
# =======================
class Bot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        try:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("✅ Slash sync OK")
        except Exception as e:
            print("Slash sync error:", e)

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
    isim TEXT,
    yas TEXT,
    deneyim TEXT
)
""")
conn.commit()


# =======================
# SAFE HELPERS
# =======================
async def safe_channel(channel_id):
    ch = bot.get_channel(channel_id)
    return ch


async def get_member(guild, user_id: int):
    try:
        return await guild.fetch_member(user_id)
    except:
        return guild.get_member(user_id)


# =======================
# ACTION VIEW
# =======================
class ActionView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = int(user_id)

    @discord.ui.button(label="KABUL", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = await get_member(guild, self.user_id)

        if not user:
            return await interaction.response.send_message("User bulunamadı", ephemeral=True)

        roles = []
        for rid in [KABUL_ROL_1, KABUL_ROL_2]:
            role = guild.get_role(rid)
            if role:
                roles.append(role)

        if roles:
            await user.add_roles(*roles)

        try:
            await user.send("🎉 Başvurun KABUL edildi!")
        except:
            pass

        log = await safe_channel(ANNOUNCE_KANAL)
        if log:
            await log.send(f"✅ {user.mention} BAŞVURUSU KABUL EDİLDİ")

        await interaction.message.edit(content="✅ KABUL EDİLDİ", view=None)
        await interaction.response.defer()


    @discord.ui.button(label="RED", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):

        guild = interaction.guild
        user = await get_member(guild, self.user_id)

        if not user:
            return await interaction.response.send_message("User bulunamadı", ephemeral=True)

        try:
            await user.send("❌ Başvurun REDDEDİLDİ")
        except:
            pass

        log = await safe_channel(ANNOUNCE_KANAL)
        if log:
            await log.send(f"❌ {user.mention} BAŞVURUSU REDDEDİLDİ")

        await interaction.message.edit(content="❌ REDDEDİLDİ", view=None)
        await interaction.response.defer()


# =======================
# MODAL
# =======================
class BasvuruModal(discord.ui.Modal, title="Başvuru Formu"):

    isim = discord.ui.TextInput(label="İsim")
    yas = discord.ui.TextInput(label="Yaş")
    deneyim = discord.ui.TextInput(label="Deneyim", style=discord.TextStyle.paragraph)

    async def on_submit(self, interaction: discord.Interaction):

        cursor.execute(
            "INSERT INTO applications (user_id, isim, yas, deneyim) VALUES (?, ?, ?, ?)",
            (str(interaction.user.id), self.isim.value, self.yas.value, self.deneyim.value)
        )
        conn.commit()

        channel = await safe_channel(BASVURU_KANAL)

        if not channel:
            return await interaction.response.send_message("Başvuru kanalı yok", ephemeral=True)

        embed = discord.Embed(
            title="📩 Yeni Başvuru",
            color=0x2ecc71
        )

        embed.add_field(name="İsim", value=self.isim.value, inline=False)
        embed.add_field(name="Yaş", value=self.yas.value, inline=False)
        embed.add_field(name="Deneyim", value=self.deneyim.value, inline=False)

        await channel.send(embed=embed, view=ActionView(interaction.user.id))

        await interaction.response.send_message("Başvuru gönderildi", ephemeral=True)


# =======================
# PANEL VIEW
# =======================
class PanelView(discord.ui.View):

    @discord.ui.button(label="Başvuru Aç", style=discord.ButtonStyle.primary)
    async def open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(BasvuruModal())


# =======================
# SLASH COMMAND
# =======================
@bot.tree.command(name="basvuru-panel", description="Başvuru paneli kurar")
async def basvuru_panel(interaction: discord.Interaction):

    if not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Sunucuda kullanılmalı", ephemeral=True)

    if ADMIN_ROLE_ID not in [r.id for r in interaction.user.roles]:
        return await interaction.response.send_message("Yetkin yok", ephemeral=True)

    embed = discord.Embed(
        title="📢 Başvuru Sistemi",
        description="Başvurmak için butona bas",
        color=0x2f3136
    )

    await interaction.channel.send(embed=embed, view=PanelView())
    await interaction.response.send_message("Panel kuruldu", ephemeral=True)


# =======================
# READY
# =======================
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")


bot.run(TOKEN)
