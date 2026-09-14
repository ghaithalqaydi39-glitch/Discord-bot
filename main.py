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
    # Defer response since AI might take 1-2 seconds to think
    await interaction.response.defer()
    
    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
        )
        # Discord message limit is 2000 characters
        answer = response.text[:1900]
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer}")
    except Exception as e:
        await interaction.followup.send(f"Error generating response: {e}")

# ----------------- AUTO-REPLY ON @MENTION -----------------
@bot.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # If the bot is tagged/mentioned in a message
    if bot.user in message.mentions:
        # Remove the @bot mention from the prompt text
        clean_text = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not clean_text:
            await message.reply("Hey! How can I help you today?")
            return

        async with message.channel.typing():
            try:
                response = gemini_client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=clean_text,
                )
                answer = response.text[:1900]
                await message.reply(answer)
            except Exception as e:
                await message.reply(f"Sorry, I ran into an issue: {e}")

    await bot.process_commands(message)

# Run the Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing!")
