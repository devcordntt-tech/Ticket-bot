import discord
from discord.ext import commands
import os
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

TOKEN = os.getenv("TOKEN")
STAFF_ROLE_NAME = "S E L L E R"

open_tickets = {}

# ================= QUESTIONS =================
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
            "Provide proof if possible",
            "Explain clearly"
        ],
        "🤝 Partnership": [
            "What kind of partnership?",
            "Your stats?",
            "Details"
        ]
    }

    answers = []

    for i, q in enumerate(questions_map.get(ticket_type, []), start=1):
        embed = discord.Embed(
            title=f"📩 Question {i}",
            description=f"╭───────────────╮\n{user.mention}\n\n**{q}**\n╰───────────────╯",
            color=0x2b2d31
        )
        embed.set_footer(text="Reply below • Timeout: 5 mins")
        await channel.send(embed=embed)

        def check(m):
            return m.author == user and m.channel == channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=300)
            answers.append((q, msg.content))
        except asyncio.TimeoutError:
            await channel.send("⏰ Time expired.")
            return

    summary = "\n\n".join([f"**{q}**\n➜ {a}" for q, a in answers])

    embed = discord.Embed(
        title="📋 Ticket Summary",
        description=f"╭───────────────╮\n{summary}\n╰───────────────╯",
        color=0x2b2d31
    )

    await channel.send(embed=embed)


# ================= CONTROLS =================
class TicketControls(discord.ui.View):
    def __init__(self, user_id, ticket_type):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.ticket_type = ticket_type
        self.claimed_by = None

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.green, emoji="🟢", custom_id="claim_btn")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if self.claimed_by:
            return await interaction.response.send_message("❌ Already claimed", ephemeral=True)

        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Seller only", ephemeral=True)

        self.claimed_by = interaction.user
        await interaction.response.send_message(f"✅ Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.blurple, emoji="👤", custom_id="add_user_btn")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Seller only", ephemeral=True)

        await interaction.response.send_message("👤 Mention the user to add", ephemeral=True)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=60)
        except asyncio.TimeoutError:
            return await interaction.followup.send("⏰ Timeout", ephemeral=True)

        if not msg.mentions:
            return await interaction.followup.send("❌ No user mentioned", ephemeral=True)

        member = msg.mentions[0]

        await interaction.channel.set_permissions(
            member,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        await interaction.followup.send(f"✅ Added {member.mention}", ephemeral=True)
        await interaction.channel.send(f"👤 {member.mention} has been added to this ticket")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, emoji="🔒", custom_id="close_btn")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)

        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Seller only", ephemeral=True)

        if self.user_id in open_tickets and self.ticket_type in open_tickets[self.user_id]:
            open_tickets[self.user_id].remove(self.ticket_type)
            if not open_tickets[self.user_id]:
                del open_tickets[self.user_id]

        await interaction.response.send_message("🔒 Closing ticket...")
        await interaction.channel.delete()


# ================= DROPDOWN =================
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🛒 Buy Products"),
            discord.SelectOption(label="❓ Support"),
            discord.SelectOption(label="🤝 Partnership"),
        ]
        super().__init__(placeholder="🎫 Open a Ticket", options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        ticket_type = self.values[0]

        category = discord.utils.get(guild.categories, name="tickets")
        role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)

        if not category or not role:
            return await interaction.response.send_message("❌ Setup missing", ephemeral=True)

        if user.id in open_tickets and ticket_type in open_tickets[user.id]:
            return await interaction.response.send_message("❌ Already opened this type", ephemeral=True)

        open_tickets.setdefault(user.id, []).append(ticket_type)

        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True),
                role: discord.PermissionOverwrite(view_channel=True),
            }
        )

        embed = discord.Embed(
            title="🎫 Nᴇxʀʏɴ Ticket",
            description=(
                f"╭━━━━━━━━━━━━━━━━━━━━╮\n"
                f"👤 {user.mention}\n"
                f"📌 Type: {ticket_type}\n"
                f"╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
                f"⚡ A seller will assist you shortly"
            ),
            color=0x2b2d31
        )

        embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

        await channel.send(
            content=f"{user.mention} {role.mention}",
            embed=embed,
            view=TicketControls(user.id, ticket_type)
        )

        await interaction.response.send_message(f"✅ Created {channel.mention}", ephemeral=True)

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
        title="🎟️ Nᴇxʀʏɴ | ᴄʜᴇᴀᴘᴇsᴛ ᴘʀɪᴄᴇs",
        description=(
            "╭━━━━━━━━━━━━━━━━━━━━╮\n"
            "💎 PREMIUM STORE PANEL\n"
            "╰━━━━━━━━━━━━━━━━━━━━╯\n\n"
            "🛒 Buy • ❓ Support • 🤝 Deals\n\n"
            "⚡ Fast • Cheap • Trusted\n\n"
            "👇 Open a ticket below"
        ),
        color=0x2b2d31
    )

    embed.set_image(url="https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExaGh4cHY3Z2o1dWR0eXBsNGdkcWg2ZW44M2g3c3U5emJudzhtZjFrOCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/qvNpPZYqNkRo0c3TDv/giphy.gif")

    await ctx.send(embed=embed, view=TicketView())


bot.run(TOKEN)
