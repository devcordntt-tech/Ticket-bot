import discord
from discord.ext import commands
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
STAFF_ROLE_NAME = "S E L L E R"


# ================= CONTROLS =================
class TicketControls(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.claimed_by = None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed_by:
            await interaction.response.send_message("❌ Already claimed!", ephemeral=True)
            return

        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can claim!", ephemeral=True)
            return

        self.claimed_by = interaction.user
        await interaction.response.send_message(f"✅ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.blurple)
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can add users!", ephemeral=True)
            return

        await interaction.response.send_message("👤 Mention the user to add:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await bot.wait_for("message", check=check)

        if msg.mentions:
            user = msg.mentions[0]
            await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
            await interaction.channel.send(f"✅ {user.mention} added to ticket")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can close!", ephemeral=True)
            return

        await interaction.channel.send("🔒 Closing ticket...")
        await interaction.channel.delete()


# ================= TICKET BUTTON =================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name="tickets")
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🎫 Nᴇxʀʏɴ Ticket",
            description=(
                f"{user.mention} welcome!\n\n"
                "Please wait for a seller to assist you.\n\n"
                "Use buttons below:\n"
                "• Claim → Seller takes ticket\n"
                "• Add User → Add someone\n"
                "• Close → Close ticket"
            ),
            color=0x2b2d31
        )

        embed.set_image(
            url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif"
        )

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=TicketControls()
        )

        await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)


# ================= PANEL =================
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Nᴇxʀʏɴ | Cheapest Prices",
        description=(
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "   💎 **WELCOME TO Nᴇxʀʏɴ STORE** 💎\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"

            "✨ Nitro • Boosts • Robux\n"
            "🎬 Streaming • 👥 Members\n"
            "🤖 Bots • 🎨 Decorations\n\n"

            "⚡ Cheapest • Fast • Trusted\n\n"
            "🔥 Click below to open ticket"
        ),
        color=0x2b2d31
    )

    embed.set_image(
        url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif"
    )

    await ctx.send(embed=embed, view=TicketView())


# ================= KEEP ALIVE =================
from flask import Flask
from threading import Thread

app = Flask("")

@app.route("/")
def home():
    return "Bot running"

def run():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    Thread(target=run).start()


keep_alive()
bot.run(TOKEN)
