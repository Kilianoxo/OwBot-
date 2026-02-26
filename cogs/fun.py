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
        "D.Va", "Doomfist", "Hazard", "Junker Queen", "Mauga", "Orisa",
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
    "Lúcio": "Change de mur régulièrement pour rester imprévisible.",
    "Moira": "Tes orbes de dégâts te génèrent des ressources de heal.",
    "Sigma": "Place ton bouclier en avançant/reculant pour créer de la pression.",
    "Roadhog": "Hook + clic gauche + melee = combo létal. Entraîne-toi à l'enchaîner.",
    "Orisa": "Ton Javelot peut interrompre les ultimes ennemis. Use-le défensivement.",
    "Wrecking Ball": "La vitesse est ta survie. Ne reste jamais immobile sous les tirs.",
    "Winston": "Saute sur les healers, pas sur les tanks. Isole tes cibles.",
    "Zarya": "Attends que l'ennemi tire avant de buller pour gonfler ton énergie.",
    "Junker Queen": "Tes blessures peuvent être healées, mais seulement si tu attaques. Reste agressive.",
    "Mauga": "Tes deux miniguns fonctionnent mieux ensemble. Ne tire pas qu'un seul.",
    "Ramattra": "Forme Nemesis est limitée. Utilise-la pour push ou absorber une ultime.",
    "Hazard": "Tes sauts muraux te donnent de l'angle. Explore la verticalité pour surprendre.",
    "Doomfist": "Garde ton Block pour absorber les dégâts et recharger tes cooldowns.",
    "Ashe": "Coach Gun te sert à fuir autant qu'à pousser les ennemis. Ne l'oublie pas.",
    "Bastion": "En mode Tourelle, positionne-toi avec une sortie de secours derrière toi.",
    "Cassidy": "Flashbang → clic droit à bout portant = combo élimination quasi garanti.",
    "Echo": "Duplicate les bons ultimates (Earthshatter, Graviton) pour changer le combat.",
    "Hanzo": "Storm Arrows est ton meilleur outil anti-tank à courte portée.",
    "Junkrat": "Tes mines sont un outil de mobilité autant que d'attaque. Pratique les sauts.",
    "Mei": "Glace sur toi-même pour survivre, pas seulement pour geler les ennemis.",
    "Pharah": "Reste en l'air et en mouvement. Une Pharah statique est une cible facile.",
    "Reaper": "Teleport derrière les healers ennemis pour tuer le soutien en priorité.",
    "Soldier: 76": "Utilise Sprint pour te repositionner après chaque échange. Ne reste pas exposé.",
    "Sojourn": "Accumule le charge sur les ennemis, puis one-shot avec le clic droit chargé.",
    "Sombra": "Hack les supports d'abord, pas les tanks. Neutralise le heal ennemi.",
    "Symmetra": "Place tes tourelles dans des angles inattendus, pas au sol au milieu du couloir.",
    "Torbjörn": "Molten Core change le teamfight. Lance-le avant que l'ennemi push.",
    "Venture": "Burrow te rend invulnérable. Utilise-le pour esquiver les ultimes.",
    "Baptiste": "Champ d'immortalité sauve les équipes mais déplace le problème. Use-le tôt.",
    "Brigitte": "Inspire heal tes alliés quand tu frappes. Reste proche pour maximiser le soutien.",
    "Illari": "Ta Lanterne Solar tient autant que tu la protèges. Mets-la à l'abri.",
    "Juno": "Ton Hyperring booste la mobilité de ton équipe. Lance-le sur le payload.",
    "Kiriko": "Téléport à travers les murs vers tes alliés. La mobilité est ta survie.",
    "Lifeweaver": "Grip sauve des vies mais peut aussi mal les repositionner. Use-le avec précaution.",
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
    "\"Experience tranquility.\" — Zenyatta",
    "\"Hammer down!\" — Reinhardt",
    "\"Sombra always knows.\" — Sombra",
    "\"I need healing.\" — Genji (probablement)",
    "\"My Barrier is up.\" — Sigma, toujours trop tard",
    "\"Tactical visor activated.\" — Soldier: 76",
    "\"The iris embraces you.\" — Zenyatta",
    "\"This is my curse.\" — Genji (sur sa solo queue)",
    "\"Halt!\" — Orisa (le mot le plus craint du ranked)",
    "\"Pew pew pew.\" — D.Va, les doigts dans le nez",
    "\"Je reviendrai.\" — Reaper, encore une fois",
    "\"La lumière guidera nos pas.\" — Baptiste",
    "\"On va les avoir !\" — Reinhardt, chaque partie",
    "\"Apaga la luz.\" — Sombra, dans le vocal ennemi",
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
    "Les heals étaient nuls. Les heals, pas moi.",
    "J'aurais dû swap. Mais j'aurais quand même perdu.",
    "C'est le matchmaking. Le matchmaking décide tout.",
    "Ranked le matin = erreur de vie. Validé.",
    "J'ai eu un 6v1 pendant 30 secondes. C'est ça le problème.",
    "Mon vrai elo c'est facilement 500 SR au-dessus.",
    "Le dernier push était chaud, non ? Non ? OK.",
    "On a perdu mais moi j'ai pogchampé.",
    "La prochaine map c'est la mienne. Statistiquement.",
    "Blame le support. C'est plus original.",
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
    "rip": ["🪦", "😔"],
    "clutch": ["🏆", "🔥"],
    "pogchamp": ["😮", "🔥"],
    "pog": ["😮", "👀"],
    "inter": ["🤡", "😭"],
    "noob": ["🔍", "😬"],
    "ez": ["😤", "😏"],
    "on perd": ["😩", "📉"],
    "victoire": ["🥳", "🏆"],
    "défaite": ["😭", "📉"],
    "afk": ["🚶", "😤"],
    "hack": ["💜", "🔓"],
    "nano": ["💉", "⚡"],
    "grav": ["🌀", "💥"],
    "dragonblade": ["🐉", "⚔️"],
    "blizzard": ["❄️", "🥶"],
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
