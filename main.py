import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Setup Gemini AI Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Dictionary to hold chat memory for each channel
channel_chats = {}

def get_chat_session(channel_id):
    """Retrieve active chat session or create a new memory session if one doesn't exist."""
    if channel_id not in channel_chats:
        channel_chats[channel_id] = gemini_client.chats.create(
            model="gemini-3.6-flash",
            config={
                "system_instruction": "You are a helpful and friendly Discord AI assistant."
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

# ----------------- AI CHAT SLASH COMMAND WITH MEMORY -----------------
@bot.tree.command(name="chat", description="Ask the AI anything! It remembers conversation history.")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    
    try:
        chat_session = get_chat_session(interaction.channel_id)
        response = chat_session.send_message(prompt)
        answer = response.text[:1900]
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer}")
    except Exception as e:
        await interaction.followup.send(f"Error generating response: {e}")

# ----------------- AUTO-REPLY ON @MENTION WITH MEMORY -----------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
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
                await message.reply(f"Sorry, I ran into an issue: {e}")

    await bot.process_commands(message)

# ----------------- RESET MEMORY SLASH COMMAND -----------------
@bot.tree.command(name="resetchat", description="Clear the AI's conversation memory in this channel.")
async def resetchat(interaction: discord.Interaction):
    if interaction.channel_id in channel_chats:
        del channel_chats[interaction.channel_id]
        await interaction.response.send_message("🧹 Memory reset! The bot has forgotten previous messages in this channel.")
    else:
        await interaction.response.send_message("No existing chat memory found for this channel.")

# Run the Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing!")
import os
import discord
from discord import app_commands
from discord.ext import commands
from google import genai

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Setup Gemini AI Client
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Dictionary to hold chat memory for each channel
channel_chats = {}

def get_chat_session(channel_id):
    """Retrieve active chat session or create a new memory session if one doesn't exist."""
    if channel_id not in channel_chats:
        channel_chats[channel_id] = gemini_client.chats.create(
            model="gemini-3.6-flash",
            config={
                "system_instruction": "You are a helpful and friendly Discord AI assistant."
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

# ----------------- AI CHAT SLASH COMMAND WITH MEMORY -----------------
@bot.tree.command(name="chat", description="Ask the AI anything! It remembers conversation history.")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    await interaction.response.defer()
    
    try:
        chat_session = get_chat_session(interaction.channel_id)
        response = chat_session.send_message(prompt)
        answer = response.text[:1900]
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer}")
    except Exception as e:
        await interaction.followup.send(f"Error generating response: {e}")

# ----------------- AUTO-REPLY ON @MENTION WITH MEMORY -----------------
@bot.event
async def on_message(message):
    if message.author == bot.user:
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
                await message.reply(f"Sorry, I ran into an issue: {e}")

    await bot.process_commands(message)

# ----------------- RESET MEMORY SLASH COMMAND -----------------
@bot.tree.command(name="resetchat", description="Clear the AI's conversation memory in this channel.")
async def resetchat(interaction: discord.Interaction):
    if interaction.channel_id in channel_chats:
        del channel_chats[interaction.channel_id]
        await interaction.response.send_message("🧹 Memory reset! The bot has forgotten previous messages in this channel.")
    else:
        await interaction.response.send_message("No existing chat memory found for this channel.")

# Run the Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing!")
