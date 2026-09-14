import os
import discord
from discord import app_commands
from discord.ext import commands

# Initialize bot client with required intents
intents = discord.Intents.default()
intents.members = True  # Required for member lookup in kick/ban commands

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        # Sync slash commands globally across all servers
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")


# ---------------------------------------------------------
# Utility Commands
# ---------------------------------------------------------

@bot.tree.command(name="ping", description="Replies with latency")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! Latency is {latency}ms.")


@bot.tree.command(name="serverinfo", description="Displays basic server information")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.send_message(
        f"**Server Name:** {guild.name}\n**Total Members:** {guild.member_count}"
    )


@bot.tree.command(name="say", description="Makes the bot send a message to a channel")
@app_commands.checks.has_permissions(manage_messages=True)
async def say(
    interaction: discord.Interaction, 
    message: str, 
    channel: discord.TextChannel = None
):
    target_channel = channel or interaction.channel
    await target_channel.send(message)
    await interaction.response.send_message(f"Message sent to {target_channel.mention}!", ephemeral=True)


# ---------------------------------------------------------
# Moderation Commands
# ---------------------------------------------------------

@bot.tree.command(name="kick", description="Kicks a member from the server")
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    # Role hierarchy check
    if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
        await interaction.response.send_message("You cannot kick someone with a role equal to or higher than yours.", ephemeral=True)
        return

    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked **{member.display_name}** | Reason: {reason}")


@bot.tree.command(name="ban", description="Bans a member from the server")
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    # Role hierarchy check
    if member.top_role >= interaction.user.top_role and interaction.guild.owner != interaction.user:
        await interaction.response.send_message("You cannot ban someone with a role equal to or higher than yours.", ephemeral=True)
        return

    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned **{member.display_name}** | Reason: {reason}")


@bot.tree.command(name="clear", description="Deletes a specified number of recent messages (1-100)")
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("Please enter a number between 1 and 100.", ephemeral=True)
        return

    # Defer response to avoid timeout during bulk deletion
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"Successfully deleted {len(deleted)} message(s).", ephemeral=True)


# ---------------------------------------------------------
# Permission Error Handler
# ---------------------------------------------------------

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You do not have the required permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ An unexpected error occurred while running this command.", ephemeral=True)


# ---------------------------------------------------------
# Start Bot
# ---------------------------------------------------------

TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing.")
