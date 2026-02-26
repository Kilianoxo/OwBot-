import discord
from discord import app_commands
from discord.ext import commands, tasks
import random
from datetime import time, timezone

# ──────────────────────────────────────────────
# Données Overwatch
# ──────────────────────────────────────────────

HEROES = {
    "Tank": [
        "D.Va", "Doomfist", "Junker Queen", "Mauga", "Orisa",
        "Ramattra", "Reinhardt", "Roadhog", "Sigma", "Winston",
        "Wrecking Ball", "Zarya",
    ],
    "Damage": [
        "Ashe", "Bastion", "Cassidy", "Echo", "Genji", "Hanzo",
        "Junkrat", "Mei", "Pharah", "Reaper", "Soldier: 76",
        "Sojourn", "Sombra", "Symmetra", "Torbjörn", "Tracer",
        "Venture", "Widowmaker",
    ],
    "Support": [
        "Ana", "Baptiste", "Brigitte", "Illari", "Juno", "Kiriko",
        "Lifeweaver", "Lúcio", "Mercy", "Moira", "Zenyatta",
    ],
}

ALL_HEROES = [h for heroes in HEROES.values() for h in heroes]

HERO_TIPS = {
    "Reinhardt": "Garde ton bouclier pour les moments critiques, pas en permanence.",
    "Mercy": "Utilise ta mobilité pour rester en vie, pas seulement pour heal.",
    "Genji": "Garde ton dash de reset pour fuir, pas juste pour les kills.",
    "Tracer": "Rappel efface les dégâts reçus, utilise-le réactivement.",
    "Widowmaker": "Place-toi pour avoir une sortie de secours, pas seulement le meilleur angle.",
    "Zenyatta": "L'Orbe de Discorde est ton outil le plus puissant, utilise-le sur le tank ennemi.",
    "D.Va": "Tes boosters peuvent aussi bloquer des projectiles (ex : Grav de Zarya).",
    "Ana": "Le Grenade biologique est ton move le plus important en teamfight.",
    "Lucio": "Change de mur régulièrement pour rester imprévisible.",
    "Moira": "Tes orbes de dégâts te génèrent des ressources de heal.",
    "Sigma": "Place ton bouclier en avançant/reculant pour créer de la pression.",
}

OVERWATCH_QUOTES = [
    "\"Limit break!\" — Kiriko",
    "\"Justice rains from above!\" — Pharah",
    "\"It's a perfect day for some mayhem.\" — Reaper",
    "\"Heroes never die!\" — Mercy",
    "\"Ryuu ga waga teki wo kurau!\" — Hanzo",
    "\"The dragon hungers.\" — Hanzo",
    "\"I am your shield. I am your sword.\" — Reinhardt",
    "\"Nerf this!\" — D.Va",
    "\"Hello, luv.\" — Tracer",
    "\"Embrace the darkness.\" — Moira",
    "\"Death walks among you.\" — Reaper",
    "\"Take it one game at a time.\" — Soldier: 76",
    "\"Scatter arrow never misses.\" — personne depuis longtemps",
    "\"I play to win.\" — Symmetra",
    "\"Let's go!\" — Cassidy",
]

TAUNTS = [
    "GG EZ les gars !",
    "Vous jouez comme des bots de pratique...",
    "Quelqu'un a vu mon aim ? Je l'ai laissé quelque part.",
    "On requeue ? Je viens de chauffer.",
    "Les ennemis ont eu de la chance, c'est tout.",
    "Ma connexion lag. (non)",
    "T'façon je jouais à moitié.",
    "On est tous en diamant dans notre cœur.",
    "Le prochain c'est le bon.",
    "Blame le tank.",
]

ROLE_EMOJIS = {"Tank": "🛡️", "Damage": "⚔️", "Support": "💚"}

# Mots-clés qui déclenchent une réaction automatique
AUTO_REACT_KEYWORDS = {
    "gg": ["🎉", "👏"],
    "gg ez": ["😤", "🙄"],
    "feedé": ["🐔", "😂"],
    "feeder": ["🐔", "😂"],
    "report": ["📋", "👀"],
    "trollé": ["🤡", "😭"],
    "ranked": ["😰", "🏆"],
    "skill issue": ["😬", "💀"],
    "ultime": ["⚡", "🔥"],
    "ult": ["⚡", "🔥"],
    "oneshot": ["💀", "😵"],
}


# ──────────────────────────────────────────────
# Cog
# ──────────────────────────────────────────────

class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_hero_channel_id: int | None = None
        self.daily_hero_task.start()

    def cog_unload(self):
        self.daily_hero_task.cancel()

    # ── Tâche quotidienne ──────────────────────

    @tasks.loop(time=time(9, 0, tzinfo=timezone.utc))
    async def daily_hero_task(self):
        if not self.daily_hero_channel_id:
            return
        channel = self.bot.get_channel(self.daily_hero_channel_id)
        if channel is None:
            return

        hero, role = self._random_hero_with_role()
        tip = HERO_TIPS.get(hero, "Essaie-le aujourd'hui et donne ton avis !")
        embed = self._build_hero_embed(hero, role, tip, daily=True)
        await channel.send(embed=embed)

    @daily_hero_task.before_loop
    async def before_daily(self):
        await self.bot.wait_until_ready()

    # ── Commandes slash ───────────────────────

    @app_commands.command(name="hero", description="Suggère un héros aléatoire à jouer")
    @app_commands.describe(role="Filtre par rôle (optionnel)")
    @app_commands.choices(role=[
        app_commands.Choice(name="Tank", value="Tank"),
        app_commands.Choice(name="Damage", value="Damage"),
        app_commands.Choice(name="Support", value="Support"),
    ])
    async def hero(self, interaction: discord.Interaction, role: str = None):
        if role:
            heroes = HEROES.get(role, [])
            chosen = random.choice(heroes)
            chosen_role = role
        else:
            chosen, chosen_role = self._random_hero_with_role()

        tip = HERO_TIPS.get(chosen, "Lance-toi et montre ce que tu vaux !")
        embed = self._build_hero_embed(chosen, chosen_role, tip)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="quote", description="Affiche une citation Overwatch aléatoire")
    async def quote(self, interaction: discord.Interaction):
        q = random.choice(OVERWATCH_QUOTES)
        embed = discord.Embed(description=f"*{q}*", color=0xFF6B00)
        embed.set_footer(text="Overwatch 2")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="taunt", description="Balance un taunt post-partie")
    async def taunt(self, interaction: discord.Interaction):
        await interaction.response.send_message(random.choice(TAUNTS))

    @app_commands.command(name="duel", description="Affronte un ami dans un duel de héros aléatoires !")
    @app_commands.describe(adversaire="Mentionne ton adversaire")
    async def duel(self, interaction: discord.Interaction, adversaire: discord.Member):
        h1, r1 = self._random_hero_with_role()
        h2, r2 = self._random_hero_with_role()

        winner = random.choice([interaction.user.display_name, adversaire.display_name])

        embed = discord.Embed(
            title="⚔️  Duel Overwatch",
            color=0xFFD700,
        )
        embed.add_field(
            name=f"{ROLE_EMOJIS[r1]} {interaction.user.display_name}",
            value=f"**{h1}**",
            inline=True,
        )
        embed.add_field(name="VS", value="\u200b", inline=True)
        embed.add_field(
            name=f"{ROLE_EMOJIS[r2]} {adversaire.display_name}",
            value=f"**{h2}**",
            inline=True,
        )
        embed.add_field(
            name="🏆 Vainqueur",
            value=f"**{winner}** remporte le duel !",
            inline=False,
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setup_daily", description="Configure le salon pour le héros du jour (admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_daily(self, interaction: discord.Interaction):
        self.daily_hero_channel_id = interaction.channel_id
        await interaction.response.send_message(
            f"Héros du jour activé dans {interaction.channel.mention} — chaque matin à 9h UTC !",
            ephemeral=True,
        )

    # ── Réactions automatiques ────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content_lower = message.content.lower()

        for keyword, emojis in AUTO_REACT_KEYWORDS.items():
            if keyword in content_lower:
                for emoji in emojis:
                    try:
                        await message.add_reaction(emoji)
                    except discord.HTTPException:
                        pass
                break

    # ── Helpers ───────────────────────────────

    def _random_hero_with_role(self) -> tuple[str, str]:
        role = random.choice(list(HEROES.keys()))
        hero = random.choice(HEROES[role])
        return hero, role

    def _build_hero_embed(self, hero: str, role: str, tip: str, daily: bool = False) -> discord.Embed:
        title = f"🎯 Héros du jour : {hero}" if daily else f"{ROLE_EMOJIS[role]} Héros suggéré : {hero}"
        embed = discord.Embed(title=title, color=self._role_color(role))
        embed.add_field(name="Rôle", value=f"{ROLE_EMOJIS[role]} {role}", inline=True)
        embed.add_field(name="Conseil", value=tip, inline=False)
        if daily:
            embed.set_footer(text="Bonne session ! — OwBot")
        return embed

    @staticmethod
    def _role_color(role: str) -> int:
        return {"Tank": 0x4FC3F7, "Damage": 0xEF5350, "Support": 0x66BB6A}.get(role, 0xFF6B00)


async def setup(bot: commands.Bot):
    await bot.add_cog(Fun(bot))
