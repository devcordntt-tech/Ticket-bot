import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
STAFF_ROLE_NAME = "S E L L E R"

# ================= TRACK OPEN TICKETS =================
# {user_id: [ticket_type1, ticket_type2, ...]}
open_tickets = {}

# ================= QUESTIONS (EMBED STYLE) =================
async def ask_questions(channel, user, ticket_type):
    questions_map = {
        "🛒 Buy Products": [
            "What product do you want to buy?",
            "Quantity?",
            "Payment method?",
            "Any extra details?"
        ],
        "❓ Support": [
            "What issue are you facing?",
            "Provide proof/screenshot if possible",
            "Explain clearly"
        ],
        "🤝 Partnership": [
            "What kind of partnership?",
            "Your server/user stats?",
            "Details of proposal"
        ]
    }

    questions = questions_map.get(ticket_type, [])
    answers = []

    for i, q in enumerate(questions, start=1):
        embed = discord.Embed(
            title=f"📩 Question {i}",
            description=f"{user.mention}\n\n**{q}**",
            color=0x1abc9c
        )
        embed.set_footer(text="Reply below • You have 5 minutes")
        await channel.send(embed=embed)

        def check(m):
            return m.author == user and m.channel == channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            answers.append((q, msg.content))
        except asyncio.TimeoutError:
            await channel.send("⏰ Timed out. Please reopen ticket.")
            return

    summary_text = "\n\n".join([f"**{q}**\n{a}" for q, a in answers])

    embed = discord.Embed(
        title="📋 Ticket Summary",
        description=summary_text,
        color=0x1abc9c
    )

    embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

    await channel.send(embed=embed)


# ================= CONTROLS =================
class TicketControls(discord.ui.View):
    def __init__(self, user_id, ticket_type):
        super().__init__(timeout=None)
        self.claimed_by = None
        self.user_id = user_id
        self.ticket_type = ticket_type

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🟢")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if self.claimed_by:
            await interaction.response.send_message("❌ Already claimed!", ephemeral=True)
            return

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can claim!", ephemeral=True)
            return

        self.claimed_by = interaction.user
        await interaction.response.send_message(f"✅ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.blurple, emoji="👤")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can add users!", ephemeral=True)
            return

        await interaction.response.send_message("👤 Mention user to add:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        msg = await bot.wait_for("message", check=check)

        if msg.mentions:
            user = msg.mentions[0]
            await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
            await interaction.channel.send(f"✅ {user.mention} added")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not staff_role or staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers can close!", ephemeral=True)
            return

        await interaction.channel.send("🔒 Closing ticket...")
        # Remove from open_tickets
        if self.user_id in open_tickets and self.ticket_type in open_tickets[self.user_id]:
            open_tickets[self.user_id].remove(self.ticket_type)
            if len(open_tickets[self.user_id]) == 0:
                del open_tickets[self.user_id]
        await interaction.channel.delete()


# ================= DROPDOWN =================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🛒 Buy Products", description="Purchase items"),
            discord.SelectOption(label="❓ Support", description="Get help"),
            discord.SelectOption(label="🤝 Partnership", description="Business deals"),
        ]
        super().__init__(placeholder="🎫 Choose your ticket type", options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        category = discord.utils.get(guild.categories, name="tickets")
        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if not category or not staff_role:
            await interaction.response.send_message(
                "❌ Setup error (create 'tickets' category & 'S E L L E R' role)",
                ephemeral=True
            )
            return

        # 🔥 prevent duplicate of same type
        if user.id in open_tickets and ticket_type in open_tickets[user.id]:
            await interaction.response.send_message(
                f"❌ You already have an open ticket of type **{ticket_type}**!",
                ephemeral=True
            )
            return

        # Track this ticket
        if user.id not in open_tickets:
            open_tickets[user.id] = []
        open_tickets[user.id].append(ticket_type)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.id}-{len(open_tickets[user.id])}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                staff_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            }
        )

        embed = discord.Embed(
            title=f"🎫 Nᴇxʀʏɴ Ticket",
            description=f"{user.mention} opened a ticket\n📌 Type: {ticket_type}",
            color=0x1abc9c
        )

        embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

        await channel.send(
            content=f"{user.mention} {staff_role.mention}",
            embed=embed,
            view=TicketControls(user.id, ticket_type)
        )

        await interaction.response.send_message(
            f"✅ Ticket created: {channel.mention}",
            ephemeral=True
        )

        asyncio.create_task(ask_questions(channel, user, ticket_type))


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
        title="🎟️ Nᴇxʀʏɴ | ᴄʜᴇᴀᴘᴇsᴛ ᴘʀɪᴄᴇs",
        description=(
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "💎 **WELCOME TO Nᴇxʀʏɴ SHOP**\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "🛒 Buy • ❓ Support • 🤝 Deals\n\n"
            "⚡ Fast • Cheap • Trusted\n\n"
            "👇 Select below to open your ticket"
        ),
        color=0x1abc9c
    )

    embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

    await ctx.send(embed=embed, view=TicketView())


bot.run(TOKEN)
