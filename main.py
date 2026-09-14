import os
import discord
from discord import app_commands
from discord.ext import commands
from typing import Literal
from google import genai
from groq import Groq
import threading
import requests
from flask import Flask, redirect, url_for, request, render_template_string, session

# Setup Discord Bot
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

# ----------------- SLASH COMMANDS -----------------
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
