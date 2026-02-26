import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    await bot.load_extension("cogs.patchnotes")
    await bot.load_extension("cogs.fun")
    await bot.tree.sync()
    print(f"OwBot connecté en tant que {bot.user} !")
    print(f"Serveurs: {[g.name for g in bot.guilds]}")


bot.run(TOKEN)
