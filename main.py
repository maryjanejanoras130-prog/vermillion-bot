import os
import discord
from discord.ext import commands
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route('/')
def home():
    return "Vermillion is alive!"

def run_web():
    app.run(host='0.0.0.0', port=10000)

Thread(target=run_web, daemon=True).start()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"Vermillion is online as {bot.user}")

@bot.command()
async def hello(ctx):
    await ctx.send("Hi! Vermillion is here! ❤️")

@bot.command()
async def vermillion(ctx):
    await ctx.send("Yes? I'm Vermillion, at your service!")

bot.run(os.environ.get("DISCORD_TOKEN"))
