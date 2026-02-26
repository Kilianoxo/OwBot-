"""
autodj.py — Génération autonome de messages, blagues et raps Overwatch.

Utilise l'API Claude (Anthropic) pour générer du contenu original.
Fallback sur des templates si ANTHROPIC_API_KEY n'est pas défini.
"""

import os
import json
import random
import asyncio
from pathlib import Path

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.fun import ALL_HEROES, HEROES, ROLE_EMOJIS
from cogs.memory import DB_PATH, PlayerDB

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

# ──────────────────────────────────────────────
# Templates fallback (sans API)
# ──────────────────────────────────────────────

RAP_TEMPLATES = [
    """🎤 *OwBot presents:*

Yo j'stack ma ult dans le payload
{hero1} pleure, {hero2} s'évade
{player1} feed mais dit que c'est le lag
{player2} clutch sur le dernier frag

Le rank monte, le mental flanche
Le samedi soir on a pas de revanche
GG WP, on recommence demain
Overwatch 2, le seul vrai destin 🎮""",

    """🎵 *Freestyle OwBot — {hero1} edition*

Main {hero1} c'est pas un game
Les haters diront que c'est du blame
{player1} sur le mic qui rage
{player2} qui hold la cage

On push le cart sur King's Row
Les tanks en front, les heals en flow
Cinq kills, team fight gagné
C'est OwBot qui vous l'avait dit 🔥""",

    """🎶 *OwBot Rap*

{player1} joue {hero1} depuis le début
{player2} sur {hero2}, le duo le plus buté
Les ennemis arrivent, le tilt commence
Mais la victoire c'est une question de patience

On lance le GG, on stack les heures
Le serveur Discord vibre et pleure
Mais OwBot est là pour documenter
Chaque clutch et chaque feeder 📋""",
]

AUTONOMOUS_MESSAGES = [
    "Je viens de calculer : {player} tilte {tilt_pct}% du temps. Impressionnant.",
    "Fun fact du jour : {player} a mentionné {hero} {count} fois. Coincidence ? Je ne crois pas.",
    "Dernière observation : {player} dit \"{phrase}\" avant chaque défaite. Corrélation établie.",
    "Statistique de la semaine : le top feeder est... {player}. Les données ne mentent pas.",
    "OwBot note que {player} joue {hero} comme un dieu. Ou pas. Les deux, en fait.",
    "Bip boop. {player} vient de battre son record de tilt. Félicitations ?",
    "Je surveille. J'apprends. {player} sait ce qu'il a fait.",
    "Analyse comportementale : {player} — Personnalité : {personality}. Accuracy : 94%.",
]


class AutoDJ(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PlayerDB(DB_PATH)
        self.auto_channel_ids: list[int] = []
        self.autonomous_post_task.start()

    def cog_unload(self):
        self.autonomous_post_task.cancel()

    # ── Tâche autonome ────────────────────────

    @tasks.loop(minutes=45)
    async def autonomous_post_task(self):
        """Poste spontanément un message sur les joueurs toutes les ~45 min."""
        if not self.auto_channel_ids:
            return

        players = await self.bot.loop.run_in_executor(None, self.db.get_all_players)
        if not players:
            return

        player = random.choice([p for p in players if p["msg_count"] > 5] or players)
        channel_id = random.choice(self.auto_channel_ids)
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return

        # 30% de chance d'envoyer un rap autonome
        if random.random() < 0.3:
            rap = await self._generate_rap(players)
            await channel.send(rap)
            return

        # Sinon, message d'observation
        heroes = player["hero_counts"]
        top_hero = max(heroes, key=heroes.get) if heroes else random.choice(ALL_HEROES)
        top_count = heroes.get(top_hero, 0)
        personality = self.db.personality_label(player)
        tilt_pct = int(100 * player["tilt_count"] / max(player["msg_count"], 1))

        catchphrases = player.get("catchphrases", [])
        phrase = random.choice(catchphrases) if catchphrases else "GG"

        msg = random.choice(AUTONOMOUS_MESSAGES).format(
            player=player["username"],
            hero=top_hero,
            count=top_count,
            tilt_pct=tilt_pct,
            phrase=phrase,
            personality=personality,
        )
        await channel.send(msg)

    @autonomous_post_task.before_loop
    async def before_auto(self):
        await self.bot.wait_until_ready()

    # ── Commandes slash ───────────────────────

    @app_commands.command(name="rap", description="Génère un rap Overwatch sur les joueurs du serveur")
    async def rap(self, interaction: discord.Interaction):
        await interaction.response.defer()
        players = await self.bot.loop.run_in_executor(None, self.db.get_all_players)
        rap = await self._generate_rap(players)
        await interaction.followup.send(rap)

    @app_commands.command(name="roast", description="OwBot roaste un joueur avec ses stats")
    @app_commands.describe(joueur="La victime")
    async def roast(self, interaction: discord.Interaction, joueur: discord.Member = None):
        await interaction.response.defer()
        target = joueur or interaction.user
        player = await self.bot.loop.run_in_executor(None, self.db.get_player, target.id)

        if not player or player["msg_count"] < 3:
            await interaction.followup.send(
                f"J'ai pas assez de data sur **{target.display_name}**... mais ça viendra. 👀"
            )
            return

        roast = await self._generate_roast(player)
        await interaction.followup.send(f"🔥 **Roast de {target.display_name}** :\n\n{roast}")

    @app_commands.command(name="blague", description="Une blague Overwatch générée par l'IA")
    async def blague(self, interaction: discord.Interaction):
        await interaction.response.defer()
        hero = random.choice(ALL_HEROES)
        joke = await self._generate_joke(hero)
        await interaction.followup.send(joke)

    @app_commands.command(name="setup_auto", description="Active les messages autonomes dans ce salon (admin)")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_auto(self, interaction: discord.Interaction):
        cid = interaction.channel_id
        if cid in self.auto_channel_ids:
            self.auto_channel_ids.remove(cid)
            await interaction.response.send_message(
                f"Messages autonomes désactivés dans {interaction.channel.mention}.", ephemeral=True
            )
        else:
            self.auto_channel_ids.append(cid)
            await interaction.response.send_message(
                f"Messages autonomes activés dans {interaction.channel.mention} ! Je vais vous surveiller. 👁️",
                ephemeral=True,
            )

    # ── Génération IA ─────────────────────────

    async def _call_claude(self, prompt: str) -> str | None:
        if not ANTHROPIC_API_KEY:
            return None
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                }
                payload = {
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 400,
                    "messages": [{"role": "user", "content": prompt}],
                }
                async with session.post(ANTHROPIC_URL, headers=headers, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data["content"][0]["text"].strip()
        except Exception:
            pass
        return None

    async def _generate_rap(self, players: list[dict]) -> str:
        if players:
            sample = random.sample(players, min(3, len(players)))
            names = [p["username"] for p in sample]
            heroes_pool = []
            for p in sample:
                if p["hero_counts"]:
                    heroes_pool.append(max(p["hero_counts"], key=p["hero_counts"].get))
            if not heroes_pool:
                heroes_pool = random.sample(ALL_HEROES, 2)
        else:
            names = ["Joueur1", "Joueur2"]
            heroes_pool = random.sample(ALL_HEROES, 2)

        if ANTHROPIC_API_KEY:
            prompt = (
                f"Génère un rap freestyle drôle et décalé sur une partie d'Overwatch 2. "
                f"Inclus les joueurs : {', '.join(names)}. "
                f"Leurs héros : {', '.join(heroes_pool[:2])}. "
                f"Le rap doit être en français, avoir 8-12 lignes, utiliser des rimes, "
                f"être humoristique avec des références Overwatch. "
                f"Ajoute des emojis gaming. Pas de balises markdown, juste le texte du rap."
            )
            result = await self._call_claude(prompt)
            if result:
                return f"🎤 *OwBot Freestyle :*\n\n{result}"

        # Fallback template
        template = random.choice(RAP_TEMPLATES)
        h1 = heroes_pool[0] if heroes_pool else random.choice(ALL_HEROES)
        h2 = heroes_pool[1] if len(heroes_pool) > 1 else random.choice(ALL_HEROES)
        p1 = names[0] if names else "Quelqu'un"
        p2 = names[1] if len(names) > 1 else "Quelqu'un d'autre"
        return template.format(hero1=h1, hero2=h2, player1=p1, player2=p2)

    async def _generate_roast(self, player: dict) -> str:
        heroes = player["hero_counts"]
        top_hero = max(heroes, key=heroes.get) if heroes else "personne"
        personality = self.db.personality_label(player)
        tilt_pct = int(100 * player["tilt_count"] / max(player["msg_count"], 1))

        if ANTHROPIC_API_KEY:
            prompt = (
                f"Génère un roast bienveillant et drôle en français pour un joueur Overwatch 2. "
                f"Infos : pseudo={player['username']}, héros favori={top_hero}, "
                f"personnalité={personality}, taux de tilt={tilt_pct}%. "
                f"Maximum 4 phrases, ton humoristique, pas méchant. Ajoute des emojis."
            )
            result = await self._call_claude(prompt)
            if result:
                return result

        # Fallback
        roasts = [
            f"**{player['username']}** joue {top_hero} depuis des mois mais le win rate reste... discutable. 📉",
            f"Stats dossier : {tilt_pct}% de ses messages sont du tilt. C'est presque un talent. 🌡️",
            f"Personnalité analysée : *{personality}*. L'IA a eu pitié et n'a pas précisé le reste. 🤖",
            f"{player['username']} a mentionné {top_hero} {sum(heroes.values())} fois. Thérapie recommandée.",
        ]
        return random.choice(roasts)

    async def _generate_joke(self, hero: str) -> str:
        if ANTHROPIC_API_KEY:
            prompt = (
                f"Génère une blague courte et drôle en français sur le héros {hero} d'Overwatch 2. "
                f"Maximum 3 lignes, format punch line. Ajoute un emoji pertinent."
            )
            result = await self._call_claude(prompt)
            if result:
                return result

        jokes = [
            f"Pourquoi {hero} n'a jamais de problème ? Parce qu'il a toujours un plan B... et un dash. 💨",
            f"Qu'est-ce que {hero} dit avant chaque team fight ? \"Faites comme si j'étais pas là.\" 🤫",
            f"La différence entre {hero} et un feeder ? {hero} le fait exprès. 🎭",
            f"Ils ont dit à {hero} de prendre le point. Il a pris tout le serveur. 🏆",
        ]
        return random.choice(jokes)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoDJ(bot))
