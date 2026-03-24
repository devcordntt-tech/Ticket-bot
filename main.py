import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
STAFF_ROLE_NAME = "S E L L E R"

open_tickets = {}  # {user_id: count}
MAX_TICKETS = 10


# ================= QUESTIONS =================
async def ask_questions(channel, user, ticket_type):
    questions_map = {
        "buy": [
            "What product do you want?",
            "Quantity?",
            "Payment method?",
            "Extra details?"
        ],
        "support": [
            "What issue?",
            "Send proof if possible",
            "Explain clearly"
        ],
        "partner": [
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
        except:
            await channel.send("⏰ Timeout.")
            return

    summary = "\n\n".join([f"**{q}**\n{a}" for q, a in answers])

    embed = discord.Embed(
        title="📋 Summary",
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

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, custom_id="claim_btn")
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

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.blurple, custom_id="add_user_btn")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers", ephemeral=True)
            return

        await interaction.response.send_message("👤 Mention user:", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
            if msg.mentions:
                user = msg.mentions[0]
                await interaction.channel.set_permissions(user, view_channel=True, send_messages=True)
                await interaction.channel.send(f"✅ Added {user.mention}")
        except:
            await interaction.channel.send("❌ Timeout")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="close_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            await interaction.response.send_message("❌ Only sellers", ephemeral=True)
            return

        # reduce count
        if self.user_id in open_tickets:
            open_tickets[self.user_id] -= 1
            if open_tickets[self.user_id] <= 0:
                del open_tickets[self.user_id]

        await interaction.channel.send("🔒 Closing...")
        await interaction.channel.delete()


# ================= BUTTON PANEL =================
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction, ticket_type, display_name):
        await interaction.response.defer()

        guild = interaction.guild
        user = interaction.user

        category = discord.utils.get(guild.categories, name="tickets")
        role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if not category or not role:
            await interaction.followup.send("❌ Setup missing", ephemeral=True)
            return

        count = open_tickets.get(user.id, 0)
        if count >= MAX_TICKETS:
            await interaction.followup.send("❌ Max 10 tickets reached", ephemeral=True)
            return

        open_tickets[user.id] = count + 1

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{open_tickets[user.id]}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True),
                role: discord.PermissionOverwrite(view_channel=True),
            }
        )

        embed = discord.Embed(
            title="🎟️ Nᴇxʀʏɴ Ticket",
            description=(
                f"{user.mention} opened a ticket\n\n"
                f"📌 Type: {display_name}\n"
                f"⚡ Wait for seller"
            ),
            color=0x2b2d31
        )

        embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

        await channel.send(
            content=f"{user.mention} {role.mention}",
            embed=embed,
            view=TicketControls(user.id)
        )

        await interaction.followup.send(f"✅ {channel.mention}", ephemeral=True)

        asyncio.create_task(ask_questions(channel, user, ticket_type))

    # ===== BUTTONS =====
    @discord.ui.button(label="Buy Products", style=discord.ButtonStyle.green, emoji="🛒", custom_id="btn_buy")
    async def buy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "buy", "🛒 Buy Products")

    @discord.ui.button(label="Support", style=discord.ButtonStyle.blurple, emoji="❓", custom_id="btn_support")
    async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "support", "❓ Support")

    @discord.ui.button(label="Partnership", style=discord.ButtonStyle.gray, emoji="🤝", custom_id="btn_partner")
    async def partner(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "partner", "🤝 Partnership")


# ================= READY =================
@bot.event
async def on_ready():
    bot.add_view(TicketButtons())
    print(f"Logged in as {bot.user}")


# ================= PANEL =================
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="🎟️ Nᴇxʀʏɴ | Cheapest Prices",
        description=(
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "💎 **WELCOME TO Nᴇxʀʏɴ SHOP**\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "🛒 Buy • ❓ Support • 🤝 Deals\n\n"
            "⚡ Fast • Cheap • Trusted\n\n"
            "👇 Click a button below"
        ),
        color=0x2b2d31
    )

    embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

    await ctx.send(embed=embed, view=TicketButtons())


bot.run(TOKEN)
