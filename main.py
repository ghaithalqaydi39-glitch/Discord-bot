import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Set your Discord User ID here (e.g. 123456789012345678)
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_DISCORD_USER_ID_HERE"))

# Setup Gemini AI Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# State variables
is_offline_mode = False
channel_chats = {}

def get_chat_session(channel_id):
    if channel_id not in channel_chats:
        channel_chats[channel_id] = gemini_client.chats.create(
            model="gemini-3.6-flash",
            config={
                "system_instruction": (
                    "You are a helpful, friendly Discord AI assistant. "
                    "You have conversation memory and remember details shared with you in chat."
                )
            }
        )
    return channel_chats[channel_id]

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ----------------- DIRECT MESSAGE SLASH COMMAND -----------------
@bot.tree.command(name="dm", description="Send a direct message to a specific user.")
@app_commands.describe(user="The user you want to message", message="The message content to send")
async def dm_cmd(interaction: discord.Interaction, user: discord.User, message: str):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ Message successfully sent to {user.mention}!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Couldn't send DM to {user.mention}. They may have Direct Messages turned off or blocked the bot.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

# ----------------- OWNER STATUS COMMANDS -----------------
@bot.tree.command(name="offline", description="Put the bot into invisible/maintenance mode (Owner only).")
async def offline_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    is_offline_mode = True
    await bot.change_presence(status=discord.Status.invisible)
    await interaction.response.send_message("🤫 Bot is now in offline mode. It will ignore non-owners.", ephemeral=True)

@bot.tree.command(name="online", description="Bring the bot back online (Owner only).")
async def online_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
        return

    is_offline_mode = False
    await bot.change_presence(status=discord.Status.online)
    await interaction.response.send_message("🟢 Bot is now back online!", ephemeral=True)

# ----------------- AI CHAT SLASH COMMAND -----------------
@bot.tree.command(name="chat", description="Ask the AI anything!")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    await interaction.response.defer()
    
    try:
        chat_session = get_chat_session(interaction.channel_id)
        response = chat_session.send_message(prompt)
        answer = response.text[:1900]
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer}")
    except Exception as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            await interaction.followup.send("⏳ **Rate Limit Hit:** Please wait 1 minute before trying again.")
        else:
            await interaction.followup.send("Sorry, I ran into an issue generating a response.")

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
                chat_session = get_chat_session(message.channel.id)
                response = chat_session.send_message(clean_text)
                answer = response.text[:1900]
                await message.reply(answer)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    await message.reply("⏳ **Rate Limit Hit:** Please wait 1 minute before trying again.")
                else:
                    await message.reply("Sorry, I ran into an issue generating a response.")

    await bot.process_commands(message)

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
