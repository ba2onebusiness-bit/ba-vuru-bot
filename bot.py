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

bot = commands.Bot(command_prefix="!", intents=intents)

# =======================
# DB
# =======================
conn = sqlite3.connect("data.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    guild_id TEXT PRIMARY KEY,
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

def get_log_channel(guild_id: int):
    cursor.execute("SELECT log_channel_id FROM settings WHERE guild_id = ?", (str(guild_id),))
    result = cursor.fetchone()
    return int(result[0]) if result else None

# =======================
# LOG SET COMMAND
# =======================
@bot.command()
async def logkanal(ctx, channel: discord.TextChannel):

    if not is_admin(ctx.author):
        return await ctx.send("Yetkin yok")

    cursor.execute("""
    INSERT OR REPLACE INTO settings (guild_id, log_channel_id)
    VALUES (?, ?)
    """, (str(ctx.guild.id), str(channel.id)))

    conn.commit()

    await ctx.send(f"✅ Log kanalı ayarlandı: {channel.mention}")

# =======================
# TICKET VIEW
# =======================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Başvur", style=discord.ButtonStyle.primary)
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
            title="📩 Başvuru",
            description="\n".join([f"{i+1}) {q}" for i, q in enumerate(QUESTIONS)]),
            color=090909
        )

        embed.set_image(url=BANNER_URL)

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

        # =======================
        # USER GET
        # =======================
        if not channel.topic or "APPLICANT_ID:" not in channel.topic:
            return await interaction.followup.send("User bulunamadı", ephemeral=True)

        user_id = int(channel.topic.split(":")[1])
        member = await guild.fetch_member(user_id)

        # =======================
        # ROLE GIVE
        # =======================
        if result == "KABUL":
            roles = [guild.get_role(rid) for rid in KABUL_ROLLER]
            roles = [r for r in roles if r]

            try:
                await member.add_roles(*roles, reason="Başvuru Kabul")
            except Exception as e:
                print("ROLE ERROR:", e)

        # =======================
        # LOG CHANNEL (DYNAMIC)
        # =======================
        log_id = get_log_channel(guild.id)
        log = guild.get_channel(log_id) if log_id else None

        if log:
            embed = discord.Embed(
                title=f"📁 Başvuru {result}",
                color=0x00ff00 if result == "KABUL" else 0xff0000
            )
            embed.add_field(name="Aday", value=member.mention)
            await log.send(embed=embed)

        await interaction.message.edit(content=f"İşlem: {result}", view=None)
        await channel.delete()

# =======================
# AUTO PANEL
# =======================
@bot.event
async def on_ready():
    print(f"Bot aktif: {bot.user}")

    # PANEL OTOMATİK LOG KANALINA GİDER
    cursor.execute("SELECT log_channel_id FROM settings LIMIT 1")
    row = cursor.fetchone()

    if row:
        channel = bot.get_channel(int(row[0]))

        if channel:
            embed = discord.Embed(
                title="📢 Başvuru Sistemi",
                description="Başlamak için tıkla",
                color=0x5865F2
            )

            embed.set_image(url=BANNER_URL)

            await channel.send(embed=embed, view=TicketView())

bot.run(TOKEN)
