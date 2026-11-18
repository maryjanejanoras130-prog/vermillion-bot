import os
import random
import discord
import aiohttp
from discord.ext import commands
from flask import Flask
from threading import Thread
from datetime import timedelta

# --- Keep Alive Web Server (for Render) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Vermillion is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

Thread(target=run_web, daemon=True).start()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # IMPORTANT: Also turn ON Server Members Intent in Developer Portal!

bot = commands.Bot(command_prefix='!', intents=intents)

warns = {}

HELLO_MSGS = [
    "Hi! Vermillion is here! ❤️",
    "Heyyy! You called? 💖",
    "Hiii! I missed you!",
    "Yo! Vermillion reporting for duty ✨",
]

VERMILLION_MSGS = [
    "Yes? I'm Vermillion, at your service!",
    "You rang? I'm here 💅",
    "At your service, bestie!",
]

# --- AI Setup (Groq - Free) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

async def ask_ai(user_message: str) -> str:
    if not GROQ_API_KEY:
        return "I don't have my AI brain yet! Ask my owner to add my GROQ_API_KEY in Render 😅"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are Vermillion, a fun, sweet, sassy, and loyal Discord bot and moderator. You talk like a friendly bestie, use emojis sometimes, keep replies short (under 2 sentences unless asked for more), and you're playful. Never say you're ChatGPT or Meta AI, you are Vermillion."},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.8,
        "max_tokens": 300,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(GROQ_URL, headers=headers, json=data, timeout=30) as resp:
                if resp.status != 200:
                    return "My brain lagged for a sec, try again? 🥺"
                result = await resp.json()
                reply = result["choices"][0]["message"]["content"]
                return reply[:1900]
    except Exception as e:
        print(f"AI Error: {e}")
        return "Oops, my brain glitched! Try again in a sec 💭"

@bot.event
async def on_ready():
    print(f"✅ Vermillion is online as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands: {[c.name for c in synced]}")
    except Exception as e:
        print(f"❌ Failed to sync slash commands: {e}")

# --- Fun Commands ---
@bot.command(name="hello")
async def hello_cmd(ctx):
    await ctx.send(random.choice(HELLO_MSGS))

@bot.command(name="vermillion")
async def vermillion_cmd(ctx):
    await ctx.send(random.choice(VERMILLION_MSGS))

@bot.command(name="ping")
async def ping_cmd(ctx):
    latency = round(bot.latency * 1000)
    await ctx.send(f"Pong! {latency}ms")

@bot.tree.command(name="hello", description="Say hi to Vermillion")
async def hello_slash(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(HELLO_MSGS))

@bot.tree.command(name="vermillion", description="Call Vermillion")
async def vermillion_slash(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(VERMILLION_MSGS))

@bot.tree.command(name="ping", description="Check if Vermillion is awake")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"Pong! {latency}ms")

@bot.tree.command(name="ask", description="Ask Vermillion anything (AI)")
async def ask_slash(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    reply = await ask_ai(question)
    await interaction.followup.send(reply)

# --- MODERATION: Prefix Commands ---
@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx, member: discord.Member, *, reason="No reason given"):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"👢 Kicked {member.mention} | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I can't kick them - their role is higher than mine! Move my role up in Server Settings > Roles.")

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx, member: discord.Member, *, reason="No reason given"):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"🔨 Banned {member.mention} | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I can't ban them - their role is higher than mine!")

@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def timeout_cmd(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason given"):
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"⏰ Timed out {member.mention} for {minutes} min | Reason: {reason}")
    except discord.Forbidden:
        await ctx.send("❌ I can't timeout them - their role is higher than mine!")

@bot.command(name="warn")
@commands.has_permissions(moderate_members=True)
async def warn_cmd(ctx, member: discord.Member, *, reason="No reason given"):
    warns[member.id] = warns.get(member.id, 0) + 1
    await ctx.send(f"⚠️ Warned {member.mention} ({warns[member.id]}/3) | Reason: {reason}")
    if warns[member.id] >= 3:
        try:
            await member.timeout(timedelta(minutes=10), reason="3 warns")
            await ctx.send(f"⏰ {member.mention} got 3 warns, auto timed out for 10 min!")
        except discord.Forbidden:
            await ctx.send("❌ Can't auto-timeout, their role is higher than mine!")

@bot.command(name="clear")
@commands.has_permissions(manage_messages=True)
async def clear_cmd(ctx, amount: int = 10):
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"🧹 Deleted {len(deleted)-1} messages!", delete_after=3)

# --- MODERATION: Slash Commands ---
@bot.tree.command(name="kick", description="Kick a member")
@discord.app_commands.checks.has_permissions(kick_members=True)
async def kick_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👢 Kicked {member.mention} | Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't kick them - their role is higher than mine! Move my role up.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def ban_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Banned {member.mention} | Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't ban them - their role is higher than mine!", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a member by name")
@discord.app_commands.checks.has_permissions(ban_members=True)
async def unban_slash(interaction: discord.Interaction, username: str):
    async for entry in interaction.guild.bans():
        if entry.user.name == username:
            await interaction.guild.unban(entry.user)
            await interaction.response.send_message(f"✅ Unbanned {username}")
            return
    await interaction.response.send_message(f"Couldn't find {username} in bans.")

@bot.tree.command(name="timeout", description="Timeout a member")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def timeout_slash(interaction: discord.Interaction, member: discord.Member, minutes: int = 10, reason: str = "No reason given"):
    try:
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await interaction.response.send_message(f"⏰ Timed out {member.mention} for {minutes} min | Reason: {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't timeout them - their role is higher than mine!", ephemeral=True)

@bot.tree.command(name="untimeout", description="Remove timeout from a member")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def untimeout_slash(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"✅ Removed timeout from {member.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't untimeout them - their role is higher than mine!", ephemeral=True)

@bot.tree.command(name="warn", description="Warn a member")
@discord.app_commands.checks.has_permissions(moderate_members=True)
async def warn_slash(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason given"):
    warns[member.id] = warns.get(member.id, 0) + 1
    await interaction.response.send_message(f"⚠️ Warned {member.mention} ({warns[member.id]}/3) | Reason: {reason}")
    if warns[member.id] >= 3:
        try:
            await member.timeout(timedelta(minutes=10), reason="3 warns")
            await interaction.followup.send(f"⏰ {member.mention} got 3 warns, auto timed out for 10 min!")
        except discord.Forbidden:
            await interaction.followup.send("❌ Can't auto-timeout, their role is higher than mine!")

@bot.tree.command(name="clear", description="Delete messages")
@discord.app_commands.checks.has_permissions(manage_messages=True)
async def clear_slash(interaction: discord.Interaction, amount: int = 10):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages!", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode in seconds")
@discord.app_commands.checks.has_permissions(manage_channels=True)
async def slowmode_slash(interaction: discord.Interaction, seconds: int = 0):
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"🐢 Slowmode set to {seconds}s")

# --- Alive: Auto-replies + AI Chat ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content = message.content.lower().strip()
    if content in ["hi", "hello", "hey", "heyy", "hii"]:
        await message.channel.send(random.choice(HELLO_MSGS))
        return
    if content in ["bye", "goodbye", "good night", "goodnight"]:
        await message.channel.send("Bye bye! Come back soon! 💖")
        return
    if "lol" in content or "lmao" in content:
        await message.channel.send("LMAOOO 😭💀")
        return
    if bot.user in message.mentions:
        clean_text = message.content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
        if not clean_text:
            clean_text = "Hi!"
        async with message.channel.typing():
            reply = await ask_ai(clean_text)
        await message.reply(reply)
        return
    await bot.process_commands(message)

# --- Error handling ---
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to do that!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ You're missing something! Check the command again.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have permission to do that! Check my role.")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.MissingPermissions):
        try:
            await interaction.response.send_message("❌ You don't have permission to do that!", ephemeral=True)
        except:
            pass

# --- Start Bot ---
bot.run(os.environ.get("DISCORD_TOKEN"))
