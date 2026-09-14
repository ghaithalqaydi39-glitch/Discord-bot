import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from google import genai
from groq import Groq

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Set your Discord User ID here (or via Render Environment Variables)
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_DISCORD_USER_ID_HERE"))

# Target Channel ID for Staff Results
STAFF_RESULTS_CHANNEL_ID = 1546885221071200276

# State variables
is_offline_mode = False
channel_chats = {}

def ask_ai(channel_id, prompt):
    """
    Tries 2 Gemini keys, then falls back to 2 Groq keys sequentially.
    """
    last_error = None

    # Collect available keys from environment variables
    gemini_keys = [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]
    groq_keys = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")] if k]

    # 1. Try Gemini Keys (Gemini 2.0 Flash)
    for g_key in gemini_keys:
        try:
            client = genai.Client(api_key=g_key)
            if channel_id not in channel_chats:
                channel_chats[channel_id] = client.chats.create(
                    model="gemini-2.0-flash",
                    config={
                        "system_instruction": (
                            "You are a helpful, friendly Discord AI assistant. "
                            "You have conversation memory and remember details shared with you in chat."
                        )
                    }
                )
            response = channel_chats[channel_id].send_message(prompt)
            return response.text
        except Exception as e:
            last_error = e
            print(f"Gemini key failed: {e}")
            if channel_id in channel_chats:
                del channel_chats[channel_id]
            continue  # Try next Gemini key

    # 2. Try Groq Keys (Using llama-3.3-70b-versatile)
    for gr_key in groq_keys:
        try:
            groq_client = Groq(api_key=gr_key)
            completion = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are a helpful Discord AI assistant acting as a backup model."
                    },
                    {"role": "user", "content": prompt}
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_error = e
            print(f"Groq key failed: {e}")
            continue  # Try next Groq key

    raise Exception(f"All 4 AI keys failed or are unconfigured. Last error: {last_error}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ----------------- AI CHAT SLASH COMMAND -----------------
@bot.tree.command(name="chat", description="Ask the AI anything!")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    await interaction.response.defer()
    
    try:
        answer_text = ask_ai(interaction.channel_id, prompt)
        answer = answer_text[:1900]
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer}")
    except Exception as e:
        await interaction.followup.send(f"❌ **Debug Error:** {e}")

# ----------------- AUTO-REPLY ON @MENTION -----------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if is_offline_mode and message.author.id != OWNER_ID:
        return

    if bot.user in message.mentions:
        clean_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not clean_text:
            await message.reply("Hey! How can I help you today?")
            return

        async with message.channel.typing():
            try:
                answer_text = ask_ai(message.channel.id, clean_text)
                answer = answer_text[:1900]
                await message.reply(answer)
            except Exception as e:
                await message.reply(f"❌ **Debug Error:** {e}")

    await bot.process_commands(message)

# ----------------- STAFF RESULT SLASH COMMAND -----------------
@bot.tree.command(name="staff_result", description="Announce a staff application result.")
@app_commands.describe(
    status="Select whether the applicant was accepted or denied",
    applicant="The user whose application was processed",
    reason="Optional reason or additional notes for the decision"
)
async def staff_result(
    interaction: discord.Interaction, 
    status: Literal["accepted", "denied"], 
    applicant: discord.User,
    reason: str = "Thank you for taking the time to apply!"
):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    channel = bot.get_channel(STAFF_RESULTS_CHANNEL_ID)
    if not channel:
        try:
            channel = await bot.fetch_channel(STAFF_RESULTS_CHANNEL_ID)
        except Exception:
            await interaction.response.send_message("❌ Error: Could not find staff results channel.", ephemeral=True)
            return

    if status == "accepted":
        embed = discord.Embed(
            title="🎉 Staff Application Status: ACCEPTED!",
            description=f"Congratulations {applicant.mention}, your application has been **accepted**! Welcome to the team.",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Applicant", value=f"{applicant.mention} ({applicant.name})", inline=True)
        embed.add_field(name="🛡️ Reviewer", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_thumbnail(url=applicant.display_avatar.url)
    else:
        embed = discord.Embed(
            title="❌ Staff Application Status: DENIED",
            description=f"Hello {applicant.mention}, your application has been **denied** at this time.",
            color=discord.Color.red()
        )
        embed.add_field(name="👤 Applicant", value=f"{applicant.mention} ({applicant.name})", inline=True)
        embed.add_field(name="🛡️ Reviewer", value=interaction.user.mention, inline=True)
        embed.add_field(name="📝 Reason", value=reason, inline=False)
        embed.set_thumbnail(url=applicant.display_avatar.url)

    try:
        await channel.send(content=f"{applicant.mention}", embed=embed)
        await interaction.response.send_message(f"✅ Staff result sent to <#{STAFF_RESULTS_CHANNEL_ID}>!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to send message: {e}", ephemeral=True)

# ----------------- DIRECT MESSAGE SLASH COMMAND -----------------
@bot.tree.command(name="dm", description="Send a direct message to a specific user.")
@app_commands.describe(user="The user you want to message", message="The message content to send")
async def dm_cmd(interaction: discord.Interaction, user: discord.User, message: str):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ Message sent to {user.mention}!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Could not send DM: {e}", ephemeral=True)

# ----------------- OWNER STATUS COMMANDS -----------------
@bot.tree.command(name="offline", description="Put the bot into invisible/maintenance mode.")
async def offline_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    is_offline_mode = True
    await bot.change_presence(status=discord.Status.invisible)
    await interaction.response.send_message("🤫 Bot is now offline.", ephemeral=True)

@bot.tree.command(name="online", description="Bring the bot back online.")
async def online_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    is_offline_mode = False
    await bot.change_presence(status=discord.Status.online)
    await interaction.response.send_message("🟢 Bot is now online!", ephemeral=True)

# ----------------- RESET MEMORY COMMAND -----------------
@bot.tree.command(name="resetchat", description="Clear channel conversation memory.")
async def resetchat(interaction: discord.Interaction):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    if interaction.channel_id in channel_chats:
        del channel_chats[interaction.channel_id]
        await interaction.response.send_message("🧹 Memory reset!")
    else:
        await interaction.response.send_message("No chat memory found for this channel.")

# Run the Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing!")
