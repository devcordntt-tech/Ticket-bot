import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
STAFF_ROLE_NAME = "S E L L E R"

# ================= TRACK =================
open_tickets = {}  # {user_id: count}
MAX_TICKETS = 10


# ================= QUESTIONS =================
async def ask_questions(channel, user, ticket_type):
    questions_map = {
        "🛒 Buy Products": [
            "What product do you want?",
            "Quantity?",
            "Payment method?",
            "Extra details?"
        ],
        "❓ Support": [
            "What issue?",
            "Send proof if possible",
            "Explain clearly"
        ],
        "🤝 Partnership": [
            "Partnership type?",
            "Your stats?",
            "Details?"
        ]
    }

    questions = questions_map.get(ticket_type, [])
    answers = []

    for i, q in enumerate(questions, 1):
        embed = discord.Embed(
            title=f"📩 Question {i}",
            description=f"{user.mention}\n\n**{q}**",
            color=0x2b2d31
        )
        embed.set_footer(text="Reply in chat • 5 min timeout")

        await channel.send(embed=embed)

        def check(m):
            return m.author == user and m.channel == channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            answers.append((q, msg.content))
        except asyncio.TimeoutError:
            await channel.send("⏰ Timeout.")
            return

    summary = "\n\n".join([f"**{q}**\n{a}" for q, a in answers])

    embed = discord.Embed(
        title="📋 Ticket Summary",
        description=summary,
        color=0x2b2d31
    )

    await channel.send(embed=embed)


# ================= CONTROLS =================
class TicketControls(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.claimed = None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if self.claimed:
            await interaction.followup.send("❌ Already claimed", ephemeral=True)
            return

        if not role or role not in interaction.user.roles:
            await interaction.followup.send("❌ Only sellers", ephemeral=True)
            return

        self.claimed = interaction.user
        await interaction.channel.send(f"✅ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.blurple)
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers", ephemeral=True)
            return

        await interaction.response.send_message("👤 Mention user to add:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            if not msg.mentions:
                await interaction.channel.send("❌ No user mentioned")
                return

            user = msg.mentions[0]
            await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
            await interaction.channel.send(f"✅ Added {user.mention}")

        except asyncio.TimeoutError:
            await interaction.channel.send("❌ Timeout")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers", ephemeral=True)
            return

        # remove ticket safely
        if self.user_id in open_tickets:
            open_tickets[self.user_id] -= 1
            if open_tickets[self.user_id] <= 0:
                del open_tickets[self.user_id]

        await interaction.channel.send("🔒 Closing...")
        await interaction.channel.delete()


# ================= DROPDOWN =================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🛒 Buy Products"),
            discord.SelectOption(label="❓ Support"),
            discord.SelectOption(label="🤝 Partnership"),
        ]
        super().__init__(placeholder="🎫 Select ticket type", options=options)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        category = discord.utils.get(guild.categories, name="tickets")
        role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if not category or not role:
            await interaction.followup.send(
                "❌ Create 'tickets' category & 'S E L L E R' role",
                ephemeral=True
            )
            return

        # limit tickets
        user_count = open_tickets.get(user.id, 0)

        if user_count >= MAX_TICKETS:
            await interaction.followup.send("❌ Max 10 tickets reached", ephemeral=True)
            return

        # increase count
        open_tickets[user.id] = user_count + 1

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{user_count+1}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
        )

        embed = discord.Embed(
            title="🎟️ Nᴇxʀʏɴ Ticket",
            description=(
                f"{user.mention} opened a ticket\n\n"
                f"📌 Type: {ticket_type}\n"
                f"⚡ Wait for seller\n"
            ),
            color=0x2b2d31
        )

        embed.set_image(
            url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif"
        )

        await channel.send(
            content=f"{user.mention} {role.mention}",
            embed=embed,
            view=TicketControls(user.id)
        )

        await interaction.followup.send(f"✅ {channel.mention}", ephemeral=True)

        asyncio.create_task(ask_questions(channel, user, ticket_type))


# ================= VIEW =================
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


# ================= READY =================
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"Logged in as {bot.user}")


# ================= PANEL =================
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Nᴇxʀʏɴ | Cheapest Prices",
        description=(
            "💎 **WELCOME TO STORE**\n\n"
            "🛒 Buy • ❓ Support • 🤝 Deals\n\n"
            "⚡ Fast • Cheap • Trusted\n\n"
            "👇 Open ticket below"
        ),
        color=0x2b2d31
    )

    embed.set_image(
        url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif"
    )

    await ctx.send(embed=embed, view=TicketView())


bot.run(TOKEN)
