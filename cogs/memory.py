"""
memory.py — Apprend les habitudes des joueurs et les stocke en SQLite.

Tables :
  players    : profil de chaque joueur (héros préférés, stats sociales)
  messages   : historique des messages (pour extraire les patterns)
  habits     : habitudes détectées (expressions récurrentes, tilts, etc.)
"""

import re
import json
import time
import random
import sqlite3
from collections import Counter
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from cogs.fun import HEROES, ALL_HEROES, ROLE_EMOJIS

DB_PATH = Path("data/owbot.db")

# Mots Overwatch qui révèlent des habitudes
HERO_ALIASES = {
    "rein": "Reinhardt", "reine": "Reinhardt",
    "dva": "D.Va", "d.va": "D.Va",
    "ball": "Wrecking Ball", "hamster": "Wrecking Ball",
    "cass": "Cassidy", "mcree": "Cassidy",
    "geni": "Genji",
    "widow": "Widowmaker", "widou": "Widowmaker",
    "ana": "Ana", "moira": "Moira", "mercy": "Mercy",
    "lucio": "Lúcio", "lúcio": "Lúcio",
    "zen": "Zenyatta",
    "pharah": "Pharah",
    "bastion": "Bastion",
    "sigma": "Sigma",
    "zarya": "Zarya",
    "sombra": "Sombra",
}

TILT_WORDS = ["feed", "feeder", "feedé", "nul", "noob", "report", "trollé", "afk", "inter"]
CARRY_WORDS = ["ez", "gg ez", "facile", "clutch", "outplayed", "insane", "pog", "lets go"]


def _get_hero_from_text(text: str) -> str | None:
    t = text.lower()
    for alias, hero in HERO_ALIASES.items():
        if alias in t:
            return hero
    for hero in ALL_HEROES:
        if hero.lower() in t:
            return hero
    return None


class PlayerDB:
    """Wrapper synchrone SQLite (utilisé depuis le thread asyncio via run_in_executor)."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS players (
                user_id      INTEGER PRIMARY KEY,
                username     TEXT,
                hero_counts  TEXT DEFAULT '{}',
                tilt_count   INTEGER DEFAULT 0,
                carry_count  INTEGER DEFAULT 0,
                msg_count    INTEGER DEFAULT 0,
                catchphrases TEXT DEFAULT '[]',
                last_seen    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS messages (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   INTEGER,
                content   TEXT,
                ts        INTEGER,
                channel   INTEGER
            );
            CREATE TABLE IF NOT EXISTS habits (
                user_id     INTEGER PRIMARY KEY,
                top_phrases TEXT DEFAULT '[]',
                top_heroes  TEXT DEFAULT '[]',
                personality TEXT DEFAULT 'mystère'
            );
        """)
        self.conn.commit()

    # ── Lecture / écriture ────────────────────

    def upsert_message(self, user_id: int, username: str, content: str, channel_id: int):
        c = self.conn.cursor()
        ts = int(time.time())

        c.execute(
            "INSERT OR IGNORE INTO players (user_id, username) VALUES (?, ?)",
            (user_id, username),
        )

        hero = _get_hero_from_text(content)
        tilt = int(any(w in content.lower() for w in TILT_WORDS))
        carry = int(any(w in content.lower() for w in CARRY_WORDS))

        c.execute(
            """UPDATE players SET
                username=?, msg_count=msg_count+1,
                tilt_count=tilt_count+?, carry_count=carry_count+?,
                last_seen=?
               WHERE user_id=?""",
            (username, tilt, carry, ts, user_id),
        )

        if hero:
            row = c.execute("SELECT hero_counts FROM players WHERE user_id=?", (user_id,)).fetchone()
            counts = json.loads(row[0]) if row else {}
            counts[hero] = counts.get(hero, 0) + 1
            c.execute("UPDATE players SET hero_counts=? WHERE user_id=?", (json.dumps(counts), user_id))

        c.execute(
            "INSERT INTO messages (user_id, content, ts, channel) VALUES (?, ?, ?, ?)",
            (user_id, content[:500], ts, channel_id),
        )
        self.conn.commit()

    def get_player(self, user_id: int) -> dict | None:
        c = self.conn.cursor()
        row = c.execute(
            "SELECT user_id, username, hero_counts, tilt_count, carry_count, msg_count, catchphrases FROM players WHERE user_id=?",
            (user_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "user_id": row[0],
            "username": row[1],
            "hero_counts": json.loads(row[2]),
            "tilt_count": row[3],
            "carry_count": row[4],
            "msg_count": row[5],
            "catchphrases": json.loads(row[6]),
        }

    def get_all_players(self) -> list[dict]:
        c = self.conn.cursor()
        rows = c.execute(
            "SELECT user_id, username, hero_counts, tilt_count, carry_count, msg_count FROM players"
        ).fetchall()
        return [
            {
                "user_id": r[0], "username": r[1],
                "hero_counts": json.loads(r[2]),
                "tilt_count": r[3], "carry_count": r[4], "msg_count": r[5],
            }
            for r in rows
        ]

    def get_recent_messages(self, user_id: int, limit: int = 50) -> list[str]:
        c = self.conn.cursor()
        rows = c.execute(
            "SELECT content FROM messages WHERE user_id=? ORDER BY ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [r[0] for r in rows]

    def add_catchphrase(self, user_id: int, phrase: str):
        c = self.conn.cursor()
        row = c.execute("SELECT catchphrases FROM players WHERE user_id=?", (user_id,)).fetchone()
        if not row:
            return
        phrases = json.loads(row[0])
        if phrase not in phrases:
            phrases.append(phrase)
            phrases = phrases[-10:]  # garder les 10 dernières
        c.execute("UPDATE players SET catchphrases=? WHERE user_id=?", (json.dumps(phrases), user_id))
        self.conn.commit()

    def personality_label(self, player: dict) -> str:
        if not player["msg_count"]:
            return "fantôme"
        tilt_rate = player["tilt_count"] / player["msg_count"]
        carry_rate = player["carry_count"] / player["msg_count"]
        if tilt_rate > 0.15:
            return "tilteur chronique"
        if carry_rate > 0.1:
            return "clutch master"
        if player["msg_count"] > 200:
            return "papa du serveur"
        heroes = player["hero_counts"]
        if heroes:
            top = max(heroes, key=heroes.get)
            return f"main {top}"
        return "joueur mystérieux"


class Memory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PlayerDB(DB_PATH)
        self.compute_habits_task.start()

    def cog_unload(self):
        self.compute_habits_task.cancel()

    # ── Écoute passive ────────────────────────

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        await self.bot.loop.run_in_executor(
            None,
            self.db.upsert_message,
            message.author.id,
            message.author.display_name,
            message.content,
            message.channel.id,
        )

    # ── Tâche périodique : recalcule les habitudes ──

    @tasks.loop(hours=1)
    async def compute_habits_task(self):
        players = await self.bot.loop.run_in_executor(None, self.db.get_all_players)
        for p in players:
            label = self.db.personality_label(p)
            heroes = sorted(p["hero_counts"], key=p["hero_counts"].get, reverse=True)[:3]
            await self.bot.loop.run_in_executor(
                None,
                self._save_habits,
                p["user_id"],
                heroes,
                label,
            )

    def _save_habits(self, user_id: int, top_heroes: list, personality: str):
        c = self.db.conn.cursor()
        c.execute(
            """INSERT OR REPLACE INTO habits (user_id, top_heroes, personality)
               VALUES (?, ?, ?)""",
            (user_id, json.dumps(top_heroes), personality),
        )
        self.db.conn.commit()

    @compute_habits_task.before_loop
    async def before_habits(self):
        await self.bot.wait_until_ready()

    # ── Commandes slash ───────────────────────

    @app_commands.command(name="profil", description="Affiche le profil OwBot d'un joueur")
    @app_commands.describe(joueur="Laisse vide pour ton propre profil")
    async def profil(self, interaction: discord.Interaction, joueur: discord.Member = None):
        target = joueur or interaction.user
        player = await self.bot.loop.run_in_executor(None, self.db.get_player, target.id)

        if not player or player["msg_count"] == 0:
            await interaction.response.send_message(
                f"{target.display_name} est encore un mystère pour moi...", ephemeral=True
            )
            return

        heroes = sorted(player["hero_counts"], key=player["hero_counts"].get, reverse=True)[:3]
        personality = self.db.personality_label(player)

        hero_str = " · ".join(heroes) if heroes else "aucun héros détecté"

        embed = discord.Embed(
            title=f"📊 Profil OwBot — {target.display_name}",
            color=0xFF6B00,
        )
        embed.add_field(name="Personnalité", value=f"*{personality}*", inline=False)
        embed.add_field(name="Héros favoris", value=hero_str, inline=False)
        embed.add_field(name="Messages analysés", value=str(player["msg_count"]), inline=True)
        embed.add_field(name="Tilts détectés", value=str(player["tilt_count"]), inline=True)
        embed.add_field(name="Clutch mentions", value=str(player["carry_count"]), inline=True)

        if player["catchphrases"]:
            embed.add_field(
                name="Ses punchlines",
                value="\n".join(f"*\"{p}\"*" for p in player["catchphrases"][-3:]),
                inline=False,
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="addphrase", description="Enregistre une punchline pour toi ou un pote")
    @app_commands.describe(phrase="La phrase légendaire", joueur="Le joueur concerné")
    async def addphrase(
        self,
        interaction: discord.Interaction,
        phrase: str,
        joueur: discord.Member = None,
    ):
        target = joueur or interaction.user
        await self.bot.loop.run_in_executor(None, self.db.add_catchphrase, target.id, phrase)
        await interaction.response.send_message(
            f"Phrase de **{target.display_name}** enregistrée : *\"{phrase}\"* 📝"
        )

    @app_commands.command(name="serverstats", description="Stats globales du serveur")
    async def serverstats(self, interaction: discord.Interaction):
        players = await self.bot.loop.run_in_executor(None, self.db.get_all_players)
        if not players:
            await interaction.response.send_message("Pas encore assez de data, laissez-moi observer...", ephemeral=True)
            return

        total_msgs = sum(p["msg_count"] for p in players)
        top_tilter = max(players, key=lambda p: p["tilt_count"])
        top_carry = max(players, key=lambda p: p["carry_count"])

        all_heroes: list[str] = []
        for p in players:
            for hero, count in p["hero_counts"].items():
                all_heroes.extend([hero] * count)
        top_hero = Counter(all_heroes).most_common(1)

        embed = discord.Embed(title="📈 Stats du serveur", color=0x4FC3F7)
        embed.add_field(name="Messages analysés", value=str(total_msgs), inline=True)
        embed.add_field(name="Joueurs observés", value=str(len(players)), inline=True)
        embed.add_field(
            name="Tilteur #1",
            value=f"{top_tilter['username']} ({top_tilter['tilt_count']} tilts)",
            inline=False,
        )
        embed.add_field(
            name="Clutch #1",
            value=f"{top_carry['username']} ({top_carry['carry_count']} carry moments)",
            inline=False,
        )
        if top_hero:
            embed.add_field(name="Héros le + mentionné", value=top_hero[0][0], inline=True)

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Memory(bot))
