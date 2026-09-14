import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from google import genai
from groq import Groq
import threading
from flask import Flask, session, redirect, url_for, request, render_template_string

# Setup Discord Bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Set your Discord User ID here (or via Render Environment Variables)
OWNER_ID = int(os.getenv("OWNER_ID", "YOUR_DISCORD_USER_ID_HERE"))

# Target Channel ID for Staff Results
STAFF_RESULTS_CHANNEL_ID = 1546885221071200276

# State variables & Dynamic Server Settings
is_offline_mode = False
channel_chats = {}
bot_settings = {
    "auto_responder": True,
    "moderation_logging": True,
    "welcome_messages": True
}

def ask_ai(channel_id, prompt):
    last_error = None
    gemini_keys = [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]
    groq_keys = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")] if k]

    for g_key in gemini_keys:
        try:
            client = genai.Client(api_key=g_key)
            if channel_id not in channel_chats:
                channel_chats[channel_id] = client.chats.create(
                    model="gemini-2.0-flash",
                    config={
                        "system_instruction": "You are a helpful, friendly Discord AI assistant with conversation memory."
                    }
                )
            response = channel_chats[channel_id].send_message(prompt)
            return response.text
        except Exception as e:
            last_error = e
            if channel_id in channel_chats:
                del channel_chats[channel_id]
            continue

    for gr_key in groq_keys:
        try:
            groq_client = Groq(api_key=gr_key)
            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a helpful Discord AI backup assistant."},
                    {"role": "user", "content": prompt}
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"All 4 AI keys failed. Last error: {last_error}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ----------------- AI CHAT & MENTIONS -----------------
@bot.tree.command(name="chat", description="Ask the AI anything!")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    if is_offline_mode and interaction.user.id != OWNER_ID:
        await interaction.response.send_message("The bot is currently offline.", ephemeral=True)
        return

    await interaction.response.defer()
    try:
        answer_text = ask_ai(interaction.channel_id, prompt)
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer_text[:1900]}")
    except Exception as e:
        await interaction.followup.send(f"❌ **Debug Error:** {e}")

@bot.event
async def on_message(message):
    if message.author == bot.user or not bot_settings["auto_responder"]:
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
                await message.reply(answer_text[:1900])
            except Exception as e:
                await message.reply(f"❌ **Debug Error:** {e}")

    await bot.process_commands(message)

# ----------------- CARI-STYLE UTILITY & MOD COMMANDS -----------------
@bot.tree.command(name="poll", description="Create a community poll with reactions.")
@app_commands.describe(question="The question for the poll")
async def poll_cmd(interaction: discord.Interaction, question: str):
    embed = discord.Embed(title="📊 Server Poll", description=question, color=discord.Color.blue())
    embed.set_footer(text=f"Created by {interaction.user.name}")
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    await message.add_reaction("👍")
    await message.add_reaction("👎")

@bot.tree.command(name="kick", description="Kick a member from the server.")
@app_commands.checks.has_permissions(kick_members=True)
async def kick_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"✅ Kicked {member.mention}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member from the server.")
@app_commands.checks.has_permissions(ban_members=True)
async def ban_cmd(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"✅ Banned {member.mention}", ephemeral=True)

@bot.tree.command(name="offline", description="Put the bot into maintenance mode (Owner Only).")
async def offline_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    is_offline_mode = True
    await bot.change_presence(status=discord.Status.invisible)
    await interaction.response.send_message("🤫 Bot is now offline.", ephemeral=True)

@bot.tree.command(name="online", description="Bring the bot back online (Owner Only).")
async def online_cmd(interaction: discord.Interaction):
    global is_offline_mode
    if interaction.user.id != OWNER_ID:
        await interaction.response.send_message("❌ Unauthorized.", ephemeral=True)
        return
    is_offline_mode = False
    await bot.change_presence(status=discord.Status.online)
    await interaction.response.send_message("🟢 Bot is now online!", ephemeral=True)

# ----------------- FLASK OWNER-ONLY WEB DASHBOARD -----------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-key-change-me")

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Server Owner Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; text-align: center; }
        .container { max-width: 600px; margin: auto; background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; margin-bottom: 10px; }
        .badge { background: #0284c7; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }
        .setting-box { background: #334155; margin: 15px 0; padding: 15px 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        button { background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:hover { background: #0284c7; }
        .off { background: #ef4444; }
        .off:hover { background: #dc2626; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛡️ Owner Control Panel</h1>
        <p>Manage your bot features dynamically like advanced management dashboards.</p>
        <span class="badge">Restricted: Server Owner Access Only</span>
        
        <hr style="border: 0; border-top: 1px solid #475569; margin: 25px 0;">

        <form method="POST" action="/update">
            <div class="setting-box">
                <span>🤖 AI Auto-Responder</span>
                <button name="toggle" value="auto_responder" class="{{ 'off' if not settings.auto_responder else '' }}">
                    {{ 'Enabled' if settings.auto_responder else 'Disabled' }}
                </button>
            </div>
            <div class="setting-box">
                <span>🛡️ Moderation Logging</span>
                <button name="toggle" value="moderation_logging" class="{{ 'off' if not settings.moderation_logging else '' }}">
                    {{ 'Enabled' if settings.moderation_logging else 'Disabled' }}
                </button>
            </div>
            <div class="setting-box">
                <span>👋 Welcome Messages</span>
                <button name="toggle" value="welcome_messages" class="{{ 'off' if not settings.welcome_messages else '' }}">
                    {{ 'Enabled' if settings.welcome_messages else 'Disabled' }}
                </button>
            </div>
        </form>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(DASHBOARD_HTML, settings=bot_settings)

@app.route('/update', methods=['POST'])
def update_setting():
    feature = request.form.get('toggle')
    if feature in bot_settings:
        bot_settings[feature] = not bot_settings[feature]
    return redirect(url_for('home'))

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()

# Run the Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
else:
    print("Error: DISCORD_TOKEN environment variable is missing!")
