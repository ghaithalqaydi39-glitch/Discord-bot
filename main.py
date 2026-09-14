import os
import random
import datetime
import threading
import requests
from typing import Literal
from flask import Flask, redirect, url_for, request, render_template_string, session

import discord
from discord import app_commands
from discord.ext import commands
from google import genai
from groq import Groq

# 1. Setup Discord Bot FIRST
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# OAuth2 Credentials from Environment Variables
CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "YOUR_DISCORD_CLIENT_ID")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "YOUR_DISCORD_CLIENT_SECRET")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://discord-bot-3gb8.onrender.com/callback")

# Target Channel ID for Staff Results
STAFF_RESULTS_CHANNEL_ID = int(os.getenv("STAFF_RESULTS_CHANNEL_ID", "1546885221071200276"))

# Per-server settings storage
server_settings = {}

def get_server_config(guild_id):
    guild_id_str = str(guild_id)
    if guild_id_str not in server_settings:
        server_settings[guild_id_str] = {
            "auto_responder": True,
            "moderation_logging": True,
            "welcome_messages": True
        }
    return server_settings[guild_id_str]

def ask_ai(prompt):
    last_error = None
    gemini_keys = [k for k in [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")] if k]
    groq_keys = [k for k in [os.getenv("GROQ_API_KEY"), os.getenv("GROQ_API_KEY_2")] if k]

    # 1. Try Gemini Keys
    for g_key in gemini_keys:
        try:
            client = genai.Client(api_key=g_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            return response.text
        except Exception as e:
            last_error = e
            continue

    # 2. Try Groq Keys
    for gr_key in groq_keys:
        try:
            groq_client = Groq(api_key=gr_key)
            completion = groq_client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": "You are a helpful Discord AI assistant."},
                    {"role": "user", "content": prompt}
                ],
            )
            return completion.choices[0].message.content
        except Exception as e:
            last_error = e
            continue

    raise Exception(f"All AI keys failed. Last error: {last_error}")

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ----------------- ESSENTIAL COMMANDS -----------------
@bot.tree.command(name="chat", description="Ask the AI anything using slash commands!")
@app_commands.describe(prompt="What would you like to ask?")
async def chat(interaction: discord.Interaction, prompt: str):
    guild_id = interaction.guild_id if interaction.guild_id else "DM"
    config = get_server_config(guild_id)
    if guild_id != "DM" and not config["auto_responder"]:
        await interaction.response.send_message("❌ AI Auto-Responder is disabled for this server via the web panel.", ephemeral=True)
        return

    await interaction.response.defer()
    try:
        answer_text = ask_ai(prompt)
        await interaction.followup.send(f"**Question:** {prompt}\n\n**Answer:**\n{answer_text[:1900]}")
    except Exception as e:
        await interaction.followup.send(f"❌ **Debug Error:** {e}")

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
        await interaction.response.send_message(f"✅ Staff result sent successfully!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to send message: {e}", ephemeral=True)

@bot.tree.command(name="poll", description="Create a community poll.")
@app_commands.describe(question="The question for the poll")
async def poll_cmd(interaction: discord.Interaction, question: str):
    embed = discord.Embed(title="📊 Server Poll", description=question, color=discord.Color.blurple())
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


# ----------------- 30+ MEMBER COMMANDS -----------------
@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question.")
@app_commands.describe(question="The question to ask")
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = [
        "It is certain.", "It is decidedly so.", "Without a doubt.",
        "Yes – definitely.", "You may rely on it.", "As I see it, yes.",
        "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.",
        "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
        "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.",
        "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."
    ]
    embed = discord.Embed(title="🎱 Magic 8-Ball", color=discord.Color.dark_purple())
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    embed.set_footer(text=f"Asked by {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="coinflip", description="Flip a coin (Heads or Tails).")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    embed = discord.Embed(title="🪙 Coin Flip", description=f"The coin landed on: **{result}**!", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roll", description="Roll a dice (1-100 or custom).")
@app_commands.describe(maximum="Maximum number on the dice (default 100)")
async def roll(interaction: discord.Interaction, maximum: int = 100):
    if maximum < 1:
        maximum = 100
    result = random.randint(1, maximum)
    await interaction.response.send_message(f"🎲 {interaction.user.mention} rolled a **{result}** (1-{maximum})")

@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors against the bot.")
@app_commands.describe(choice="Choose rock, paper, or scissors")
async def rps(interaction: discord.Interaction, choice: Literal["rock", "paper", "scissors"]):
    bot_choice = random.choice(["rock", "paper", "scissors"])
    choice = choice.lower()
    
    if choice == bot_choice:
        result = f"It's a tie! We both chose {bot_choice}."
        color = discord.Color.orange()
    elif (choice == "rock" and bot_choice == "scissors") or \
         (choice == "paper" and bot_choice == "rock") or \
         (choice == "scissors" and bot_choice == "paper"):
        result = f"🎉 You win! I chose {bot_choice}."
        color = discord.Color.green()
    else:
        result = f"❌ You lose! I chose {bot_choice}."
        color = discord.Color.red()
        
    embed = discord.Embed(title="✂️ Rock, Paper, Scissors", description=result, color=color)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="joke", description="Get a random joke.")
async def joke(interaction: discord.Interaction):
    jokes = [
        ("Why don't scientists trust atoms?", "Because they make up everything!"),
        ("Why did the scarecrow win an award?", "Because he was outstanding in his field!"),
        ("Why don't skeletons fight each other?", "They don't have the guts."),
        ("What do you call a fake noodle?", "An impasta!"),
        ("Why did the bicycle fall over?", "Because it was two tired!")
    ]
    setup, punchline = random.choice(jokes)
    embed = discord.Embed(title="😂 Random Joke", description=f"**{setup}**\n\n||{punchline}||", color=discord.Color.blue())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="fact", description="Get a random interesting fact.")
async def fact(interaction: discord.Interaction):
    facts = [
        "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still edible.",
        "Bananas are curved because they grow towards the sun against gravity.",
        "A group of flamingos is called a 'flamboyance'.",
        "Octopuses have three hearts and blue blood.",
        "Earth is the only planet not named after a god or goddess."
    ]
    await interaction.response.send_message(f"💡 **Did you know?**\n{random.choice(facts)}")

@bot.tree.command(name="ping", description="Check the bot's latency response time.")
async def ping(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Latency: **{latency}ms**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="View information about this server.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(title=f"📊 {guild.name} Info", color=discord.Color.blurple())
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
    embed.add_field(name="📅 Created On", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="🛡️ Roles", value=len(guild.roles), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Get information about a user.")
@app_commands.describe(member="The member to inspect (leave blank for yourself)")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"👤 User Info - {member.name}", color=member.color)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=member.id, inline=True)
    embed.add_field(name="🏷️ Nickname", value=member.nick or "None", inline=True)
    embed.add_field(name="📅 Joined Server", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "Unknown", inline=True)
    embed.add_field(name="🎂 Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
    roles = [role.mention for role in member.roles if role != interaction.guild.default_role]
    embed.add_field(name=f"🛡️ Roles ({len(roles)})", value=" ".join(roles[:10]) if roles else "None", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="View a user's full-size avatar.")
@app_commands.describe(member="The member whose avatar you want to see")
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"🖼️ Avatar for {member.name}", color=member.color)
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="botinfo", description="View stats and details about this bot.")
async def botinfo(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Serenity Bot Info", description="A multi-server utility & AI assistant bot powered by Gemini and Groq.", color=discord.Color.teal())
    embed.add_field(name="🌐 Servers Active", value=len(bot.guilds), inline=True)
    embed.add_field(name="⚡ Python Framework", value="Discord.py & Flask", inline=True)
    embed.add_field(name="🔒 Dashboard", value="Multi-server OAuth2 Web Panel Active", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="say", description="Make the bot say something in chat.")
@app_commands.describe(message="What you want the bot to say")
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(message)

@bot.tree.command(name="reverse", description="Reverse text backwards.")
@app_commands.describe(text="Text to reverse")
async def reverse(interaction: discord.Interaction, text: str):
    await interaction.response.send_message(f"🔄 {text[::-1]}")

@bot.tree.command(name="ascii", description="Convert text into cool ASCII block letters.")
@app_commands.describe(text="Short text to convert (max 10 chars)")
async def ascii_text(interaction: discord.Interaction, text: str):
    if len(text) > 10:
        await interaction.response.send_message("❌ Keep it under 10 characters for proper formatting!", ephemeral=True)
        return
    clean_txt = text.upper()
    await interaction.response.send_message(f"```fix\n{clean_txt}\n```")

@bot.tree.command(name="rate", description="Rate something out of 10 randomly.")
@app_commands.describe(thing="What do you want me to rate?")
async def rate(interaction: discord.Interaction, thing: str):
    score = random.randint(0, 10)
    await interaction.response.send_message(f"⭐ I'd rate **{thing}** a **{score}/10**!")

@bot.tree.command(name="ship", description="Calculate compatibility match between two users.")
@app_commands.describe(user1="First user", user2="Second user")
async def ship(interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
    score = random.randint(0, 100)
    bar = "█" * (score // 10) + "░" * (10 - (score // 10))
    embed = discord.Embed(title="💖 Matchmaking Calculator", description=f"Matching {user1.mention} & {user2.mention}\n\n**{score}%**\n`[{bar}]`", color=discord.Color.magenta())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="choose", description="Pick randomly between multiple options.")
@app_commands.describe(options="Options separated by commas (e.g. Pizza, Burger)")
async def choose(interaction: discord.Interaction, options: str):
    choice_list = [opt.strip() for opt in options.split(",")]
    if len(choice_list) < 2:
        await interaction.response.send_message("❌ Please provide at least two options separated by a comma!", ephemeral=True)
        return
    selected = random.choice(choice_list)
    await interaction.response.send_message(f"🎯 I choose: **{selected}**!")

@bot.tree.command(name="rollrange", description="Roll a random number between a minimum and maximum.")
@app_commands.describe(min_val="Minimum number", max_val="Maximum number")
async def rollrange(interaction: discord.Interaction, min_val: int, max_val: int):
    if min_val >= max_val:
        await interaction.response.send_message("❌ Minimum must be lower than maximum!", ephemeral=True)
        return
    result = random.randint(min_val, max_val)
    await interaction.response.send_message(f"🎲 Random number between {min_val} and {max_val}: **{result}**")

@bot.tree.command(name="time", description="Check current UTC server time.")
async def current_time(interaction: discord.Interaction):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(f"🕒 Current Bot System Time (UTC): **{now}**")

@bot.tree.command(name="balance", description="Check your virtual bank balance.")
async def balance(interaction: discord.Interaction):
    coins = random.randint(100, 5000)
    embed = discord.Embed(title=f"🏦 {interaction.user.name}'s Bank", description=f"Balance: **{coins} 🪙 Coins**", color=discord.Color.gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="daily", description="Claim your daily free server coins.")
async def daily(interaction: discord.Interaction):
    reward = 500
    embed = discord.Embed(title="🎁 Daily Claim", description=f"You successfully claimed your daily **{reward} 🪙 Coins**!", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="work", description="Do a random job to earn server coins.")
async def work(interaction: discord.Interaction):
    jobs = [
        ("Discord Moderator", 150),
        ("Bug Hunter", 300),
        ("Bot Developer", 450),
        ("Pizza Delivery", 100),
        ("Server Cleaner", 75)
    ]
    job, earned = random.choice(jobs)
    await interaction.response.send_message(f"💼 You worked as a **{job}** and earned **{earned} 🪙 Coins**!")

@bot.tree.command(name="slots", description="Play the slot machine for coins.")
async def slots(interaction: discord.Interaction):
    symbols = ["🍒", "🍋", "🍊", "🍇", "🔔", "💎"]
    res = [random.choice(symbols) for _ in range(3)]
    if res[0] == res[1] == res[2]:
        msg = f"{' '.join(res)}\n🎉 **Jackpot! You won 1,000 coins!**"
    elif res[0] == res[1] or res[1] == res[2]:
        msg = f"{' '.join(res)}\n✨ **Small win! You won 200 coins!**"
    else:
        msg = f"{' '.join(res)}\n❌ **You lost! Better luck next time.**"
    embed = discord.Embed(title="🎰 Slot Machine", description=msg, color=discord.Color.dark_gold())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="vaporwave", description="Aestheticize your text.")
@app_commands.describe(text="Text to vaporwave")
async def vaporwave(interaction: discord.Interaction, text: str):
    converted = "".join([chr(ord(c) + 65248) if 33 <= ord(c) <= 126 else c for c in text])
    await interaction.response.send_message(converted)

@bot.tree.command(name="mock", description="Mocker spongebob text generator.")
@app_commands.describe(text="Text to mock")
async def mock(interaction: discord.Interaction, text: str):
    mocked = "".join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)])
    await interaction.response.send_message(f"🧽 {mocked}")

@bot.tree.command(name="hug", description="Send a virtual hug to someone.")
@app_commands.describe(member="Member to hug")
async def hug(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🤗 {interaction.user.mention} gives a warm hug to {member.mention}!")

@bot.tree.command(name="pat", description="Pat a user gently on the head.")
@app_commands.describe(member="Member to pat")
async def pat(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"✋ {interaction.user.mention} softly pats {member.mention} on the head!")

@bot.tree.command(name="highfive", description="Give someone a high five.")
@app_commands.describe(member="Member to high five")
async def highfive(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"🙌 {interaction.user.mention} high-fives {member.mention}!")

@bot.tree.command(name="slap", description="Slap a user playfully.")
@app_commands.describe(member="Member to slap")
async def slap(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"👋 {interaction.user.mention} slaps {member.mention} around a bit with a large trout!")


# ----------------- PUBLIC FLASK WEBSITE & OAUTH2 -----------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super-secret-oauth-key")

LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Serenity Bot - Multi-Server Management</title>
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 0; text-align: center; }
        header { display: flex; justify-content: space-between; align-items: center; padding: 20px 50px; background: #1e293b; }
        .logo { font-size: 22px; font-weight: bold; color: #38bdf8; }
        .hero { padding: 100px 20px; }
        h1 { font-size: 50px; color: #f1f5f9; margin-bottom: 10px; }
        p { color: #94a3b8; font-size: 18px; margin-bottom: 30px; }
        .btn { background: #5865F2; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: bold; display: inline-block; margin: 10px; }
        .btn:hover { background: #4752C4; }
        .btn-dashboard { background: #10b981; }
        .btn-dashboard:hover { background: #059669; }
    </style>
</head>
<body>
    <header>
        <div class="logo">🤖 Serenity Bot Hub</div>
        <div>
            {% if 'user' in session %}
                <a href="/dashboard" class="btn btn-dashboard">Control Panel</a>
                <a href="/logout" class="btn" style="background: #ef4444;">Logout</a>
            {% else %}
                <a href="/login" class="btn">Login with Discord</a>
            {% endif %}
        </div>
    </header>
    <div class="hero">
        <h1>Supercharge Your Discord Server</h1>
        <p>Advanced AI failover, moderation logs, and custom management features for any community.</p>
        <a href="https://discord.com/oauth2/authorize?client_id={{ client_id }}&scope=bot+applications.commands&permissions=8" target="_blank" class="btn">Add to Discord</a>
    </div>
</body>
</html>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Server Management Dashboard</title>
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; text-align: center; }
        .container { max-width: 700px; margin: auto; background: #1e293b; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; }
        .server-box { background: #334155; margin: 15px 0; padding: 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        .btn { background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; text-decoration: none; }
        .btn:hover { background: #0284c7; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome, {{ user.username }}! 👋</h1>
        <p>Select a server where you have administrative privileges to configure features.</p>
        <hr style="border: 0; border-top: 1px solid #475569; margin: 25px 0;">
        
        {% for guild in guilds %}
            {% if (guild.permissions | int) & 0x8 == 0x8 or (guild.permissions | int) & 0x20 == 0x20 %}
                <div class="server-box">
                    <span><b>{{ guild.name }}</b></span>
                    <a href="/manage/{{ guild.id }}" class="btn">Manage Settings</a>
                </div>
            {% endif %}
        {% endfor %}
        <br>
        <a href="/" class="btn" style="background: #64748b;">Back to Home</a>
    </div>
</body>
</html>
"""

MANAGEMENT_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Managing Server</title>
    <style>
        body { font-family: 'Inter', sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; text-align: center; }
        .container { max-width: 600px; margin: auto; background: #1e293b; padding: 40px; border-radius: 16px; }
        .setting-box { background: #334155; margin: 15px 0; padding: 15px 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
        button { background: #0ea5e9; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .off { background: #ef4444; }
        .btn { background: #64748b; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>⚙️ Server Configuration</h1>
        <form method="POST">
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
        </form>
        <a href="/dashboard" class="btn">Back to Server List</a>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(LANDING_PAGE_HTML, client_id=CLIENT_ID)

@app.route('/login')
def login():
    discord_login_url = f"https://discord.com/api/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify+guilds"
    return redirect(discord_login_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    token_json = r.json()
    
    access_token = token_json.get('access_token')
    if not access_token:
        return redirect('/')

    user_headers = {'Authorization': f'Bearer {access_token}'}
    user_resp = requests.get('https://discord.com/api/users/@me', headers=user_headers).json()
    session['user'] = user_resp

    guilds_resp = requests.get('https://discord.com/api/users/@me/guilds', headers=user_headers).json()
    session['guilds'] = guilds_resp

    return redirect('/dashboard')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template_string(DASHBOARD_HTML, user=session['user'], guilds=session['guilds'])

@app.route('/manage/<guild_id>', methods=['GET', 'POST'])
def manage_server(guild_id):
    if 'user' not in session:
        return redirect('/')
    
    config = get_server_config(guild_id)
    if request.method == 'POST':
        feature = request.form.get('toggle')
        if feature in config:
            config[feature] = not config[feature]
            
    return render_template_string(MANAGEMENT_HTML, settings=config)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

def run_web():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_web, daemon=True).start()

# Run Bot
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
