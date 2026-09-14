import random
import datetime

# ----------------- 30+ MEMBER COMMANDS -----------------

# --- FUN & GAMES ---
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


# --- UTILITY & INFO ---
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


# --- TEXT & FUNNY GENERATORS ---
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
    await interaction.response.send_message(f"```fix\n{text.upper()}\n```")

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


# --- RANDOM SELECTION & UTILITY ---
@bot.tree.command(name="choose", description="Pick randomly between multiple options separated by commas.")
@app_commands.describe(options="Options separated by commas (e.g. Pizza, Burger, Tacos)")
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


# --- TIME & DATE ---
@bot.tree.command(name="time", description="Check current UTC server time.")
async def current_time(interaction: discord.Interaction):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    await interaction.response.send_message(f"🕒 Current Bot System Time (UTC): **{now}**")


# --- DUMMY ECONOMY & FUN COMMANDS ---
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


# --- MEME / FUN TEXT ---
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
