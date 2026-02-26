import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

COGS = [
    "cogs.patchnotes",
    "cogs.fun",
    "cogs.memory",
    "cogs.autodj",
    "cogs.voice_listener",
]


@bot.event
async def on_ready():
    for cog in COGS:
        await bot.load_extension(cog)

    await bot.tree.sync()
    print(f"OwBot en ligne — {bot.user}")
    print(f"Serveurs : {[g.name for g in bot.guilds]}")
    print("Commandes disponibles : /hero /quote /taunt /duel /patchnotes /patchlink")
    print("                        /profil /addphrase /serverstats")
    print("                        /rap /roast /blague /setup_auto")
    print("                        /join /leave /setup_daily")


bot.run(TOKEN)
