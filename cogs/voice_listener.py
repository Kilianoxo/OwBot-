"""
voice_listener.py — OwBot écoute les salons vocaux Overwatch et fait des blagues.

Fonctionnement :
  1. /join   → le bot rejoint le salon vocal de l'utilisateur
  2. Le bot enregistre l'audio (PCM) par tranches de ~5 s
  3. Transcription via faster-whisper (local, gratuit) ou OpenAI Whisper API
  4. Génération d'une blague/commentaire via Claude ou templates
  5. Envoi du commentaire dans le salon texte associé

Dépendances optionnelles :
  - faster-whisper  (pip install faster-whisper)   ← STT local
  - openai          (pip install openai)             ← Whisper API alternative
"""

import os
import io
import wave
import asyncio
import random
import struct
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from cogs.autodj import AutoDJ
from cogs.fun import ALL_HEROES

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Mots Overwatch → réaction drôle automatique
VOICE_KEYWORDS = {
    "ultime": ["L'ultime est lancée ! ⚡", "L'ult arrive... ou pas 💀", "ULTIMATE INCOMING 🔥"],
    "ult": ["Ult spotted 🎯", "Fais attention à l'ult 👁️", "L'ult change tout. Peut-être. ⚡"],
    "feed": ["Quelqu'un a mentionné le feeder... 🐔", "Le feed commence... 📉", "Dossier feed mis à jour. 📋"],
    "tilt": ["TILT ALERT 🌡️🌡️🌡️", "Le mental est parti en vacances.", "Tilt confirmé. Recommandation : respire. 🧘"],
    "reinhardt": ["HAMMER DOWN 🔨", "Le bouclier tient... jusqu'à ce qu'il tienne plus.", "REIN ! REIN ! REIN ! 🛡️"],
    "widow": ["Quelqu'un a peur de Widowmaker ? Moi aussi. 🎯", "One shot, one kill... ou miss.", "La Widow est là. Bonne chance. 💀"],
    "mercy": ["Ressuscitée ! Ou pas. 🕊️", "Mercy main spotted 💛", "La Valkyrie entend vos prières. 🌟"],
    "genji": ["I need healing. Probablement Genji. 💚⚔️", "Ryuu ga waga teki wo kurau ! 🐉", "Le Genji qui demande des heals... intemporel."],
    "sombra": ["Hackeada 💜", "Sombra est déjà là. Elle l'a toujours été.", "Vous avez été hackés. Ou vous l'allez être."],
    "ranked": ["Le ranked... le vrai boss d'Overwatch 😰", "Classé = souffrance volontaire.", "En ranked, tout le monde est un expert sauf toi."],
    "gg": ["GG ! 🎉", "GGGGGG les champions !", "GG WP, on recommence ?"],
    "noob": ["Noob detected 🔍", "Chacun débute un jour. Certains plus longtemps que d'autres.", "Le noob d'aujourd'hui... reste souvent noob. 😬"],
    "ana": ["Ana spotted 💉", "Le Nano Boost va changer le game. Pour quelqu'un.", "Anti-heal ou Nano ? Ana décide de votre sort."],
    "bastion": ["Bastion en tourelle... le cauchemar de ceux sans cover. 🤖", "Attention au Bastion ! Ou pas, si tu joues bien."],
    "dva": ["D.Va à l'attaque ! NERF THIS ! 💣", "Les boosters de D.Va arrivent. Cover recommandée."],
    "zarya": ["Grav incoming ? Graviton en approche... 🌀", "L'énergie de Zarya monte. Mauvais signe pour vous."],
    "zenyatta": ["Experience tranquility... ou pas. ☮️", "Orbe de Discorde placé. Quelqu'un va souffrir."],
    "hanzo": ["Scatter... oh wait, c'est plus là. 😅", "Dragon incoming ! 🐉 — à toi de choisir la direction."],
    "reaper": ["Death walks among you... 💀", "Le Reaper teleporte derrière vous. Classique."],
    "push": ["On push ! Ou on fait semblant de push. 📦", "Push le payload ! Non, l'autre. Non, cet autre-là."],
    "inter": ["Inter signalé. OwBot prend note avec tristesse. 😔", "L'inter... plongeon spectaculaire dans le néant. 🤡"],
    "clutch": ["CLUTCH MOMENT 🏆 — OwBot s'incline.", "Le clutch arrive ? OwBot retient son souffle."],
    "nano": ["NANO BOOST ! ⚡ — Quelqu'un va faire des choses terribles.", "La nano est lâchée. Le monde tremble."],
}

FUNNY_VOICE_COMMENTS = [
    "J'ai entendu quelque chose de suspect... 👂",
    "Mes capteurs détectent du {hero} dans la conversation.",
    "Analyse vocale en cours... résultat : chaos total.",
    "Je prends note. Tout. Absolument tout. 📋",
    "La tension monte dans le vocal ! 📈",
    "OwBot confirme : personne ne s'entend dans ce vocal.",
    "Classement mental : {player} est au fond du gouffre.",
    "Le vocal sonne comme une partie de ranked. C'est pas un compliment.",
    "Bruit ambiant analysé. Conclusion : vous avez besoin d'aide. 🧠",
    "OwBot enregistre ce moment pour la postérité... et vos dossiers.",
    "La communication en vocal est... intéressante. Très intéressante.",
    "J'entends du {hero} mentionné. Situation tactique réévaluée.",
    "Niveau de stress vocal mesuré : ÉLEVÉ. Recommandation : eau fraîche.",
    "La stratégie discutée ici est... créative. On va dire ça.",
    "Vocal analysis report : cohérence tactique = 12%. Normal pour ce serveur.",
    "OwBot écoute sans juger. (OwBot juge en silence.)",
    "{player} semble particulièrement expressif ce soir. Notes prises.",
    "La qualité du callout ici est... documentée. Je dirai pas plus.",
]


class VoiceListener(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_clients: dict[int, discord.VoiceClient] = {}
        self.text_channels: dict[int, discord.TextChannel] = {}
        self.listening: dict[int, bool] = {}

    # ── Commandes slash ───────────────────────

    @app_commands.command(name="join", description="OwBot rejoint ton salon vocal pour écouter et commenter")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message(
                "T'es pas dans un salon vocal ! Rejoins-en un d'abord.", ephemeral=True
            )
            return

        voice_channel = interaction.user.voice.channel
        guild_id = interaction.guild_id

        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
            await self.voice_clients[guild_id].move_to(voice_channel)
        else:
            vc = await voice_channel.connect()
            self.voice_clients[guild_id] = vc

        self.text_channels[guild_id] = interaction.channel
        self.listening[guild_id] = True

        await interaction.response.send_message(
            f"Je suis dans **{voice_channel.name}** ! Je vais tout écouter... 👁️🎤\n"
            f"Mes commentaires arriveront ici. Soyez prudents avec vos mots."
        )

        # Lancer l'écoute en arrière-plan
        asyncio.create_task(self._listen_loop(guild_id, voice_channel))

    @app_commands.command(name="leave", description="OwBot quitte le salon vocal")
    async def leave(self, interaction: discord.Interaction):
        guild_id = interaction.guild_id
        self.listening[guild_id] = False

        if guild_id in self.voice_clients and self.voice_clients[guild_id].is_connected():
            await self.voice_clients[guild_id].disconnect()
            del self.voice_clients[guild_id]

        await interaction.response.send_message("J'ai tout entendu. Je pars avec les secrets. 🤫")

    # ── Logique d'écoute ─────────────────────

    async def _listen_loop(self, guild_id: int, voice_channel: discord.VoiceChannel):
        """Boucle d'écoute — enregistre des tranches audio et les transcrit."""
        vc = self.voice_clients.get(guild_id)
        if vc is None:
            return

        try:
            sink = discord.sinks.WaveSink()
            vc.start_recording(sink, self._recording_finished, guild_id)

            # Toutes les 8 secondes, on coupe et on analyse
            while self.listening.get(guild_id) and vc.is_connected():
                await asyncio.sleep(8)
                if not self.listening.get(guild_id) or not vc.is_connected():
                    break

                vc.stop_recording()
                await asyncio.sleep(0.5)

                # Relancer pour la prochaine tranche
                if self.listening.get(guild_id) and vc.is_connected():
                    sink = discord.sinks.WaveSink()
                    vc.start_recording(sink, self._recording_finished, guild_id)

        except Exception as e:
            channel = self.text_channels.get(guild_id)
            if channel:
                await channel.send(f"Problème d'écoute vocale : `{e}`")

    async def _recording_finished(self, sink: discord.sinks.WaveSink, guild_id: int):
        """Callback quand l'enregistrement s'arrête — transcrit et commente."""
        text_channel = self.text_channels.get(guild_id)
        if not text_channel:
            return

        transcripts = []
        for user_id, audio in sink.audio_data.items():
            transcript = await self._transcribe(audio.file)
            if transcript:
                transcripts.append((user_id, transcript))

        if not transcripts:
            return

        # Réaction sur mots-clés détectés
        full_text = " ".join(t for _, t in transcripts).lower()
        reaction_sent = False

        for keyword, reactions in VOICE_KEYWORDS.items():
            if keyword in full_text:
                await text_channel.send(f"🎙️ *{random.choice(reactions)}*")
                reaction_sent = True
                break

        # Commentaire autonome aléatoire (20% de chance si pas déjà réagi)
        if not reaction_sent and random.random() < 0.2:
            autodj: Optional[AutoDJ] = self.bot.cogs.get("AutoDJ")
            if autodj and VOICE_KEYWORDS:
                comment = await self._generate_voice_comment(transcripts, autodj)
                if comment:
                    await text_channel.send(f"🎙️ {comment}")

    async def _transcribe(self, audio_file: io.BytesIO) -> str:
        """Transcrit un fichier audio en texte."""
        audio_file.seek(0)
        data = audio_file.read()
        if len(data) < 1000:
            return ""

        # Option 1 : faster-whisper (local)
        try:
            from faster_whisper import WhisperModel
            import tempfile

            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(data)
                tmp_path = f.name

            segments, _ = model.transcribe(tmp_path, language="fr")
            return " ".join(s.text for s in segments).strip()
        except ImportError:
            pass

        # Option 2 : OpenAI Whisper API
        if OPENAI_API_KEY:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    form = aiohttp.FormData()
                    form.add_field("file", data, filename="audio.wav", content_type="audio/wav")
                    form.add_field("model", "whisper-1")
                    form.add_field("language", "fr")
                    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
                    async with session.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers=headers,
                        data=form,
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            return result.get("text", "")
            except Exception:
                pass

        return ""

    async def _generate_voice_comment(
        self, transcripts: list[tuple[int, str]], autodj: AutoDJ
    ) -> str:
        full_text = " ".join(t for _, t in transcripts)

        # Essayer Claude pour un commentaire contextuel
        if os.getenv("ANTHROPIC_API_KEY"):
            prompt = (
                f"Voici ce qui a été dit dans un vocal Discord Overwatch : \"{full_text[:200]}\"\n"
                f"Génère un commentaire drôle, décalé et court (1-2 phrases max) en français "
                f"comme si tu étais un bot Overwatch qui espionnait la conversation. "
                f"Sois sarcastique et geek. Pas de balises markdown."
            )
            result = await autodj._call_claude(prompt)
            if result:
                return result

        # Fallback
        hero = random.choice(ALL_HEROES)
        comment = random.choice(FUNNY_VOICE_COMMENTS)
        return comment.format(hero=hero, player="quelqu'un")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        """Commentaire quand quelqu'un rejoint/quitte le vocal."""
        guild_id = member.guild.id
        if guild_id not in self.text_channels:
            return
        if member.bot:
            return

        channel = self.text_channels[guild_id]

        if before.channel is None and after.channel is not None:
            msgs = [
                f"**{member.display_name}** vient de rejoindre le vocal. Que le tilt commence. 🎮",
                f"**{member.display_name}** est là. OwBot prend des notes. 📋",
                f"Bienvenue **{member.display_name}** ! Les ennemis tremblent (ou pas).",
                f"**{member.display_name}** entre dans l'arène. Que le spectacle commence. 🎭",
                f"OwBot détecte **{member.display_name}** dans le vocal. Surveillance activée. 👁️",
                f"**{member.display_name}** connecté. Statistiques de tilt prêtes à être mises à jour.",
            ]
            await channel.send(random.choice(msgs))

        elif before.channel is not None and after.channel is None:
            msgs = [
                f"**{member.display_name}** a quitté. Probablement après une défaite. 🚪",
                f"**{member.display_name}** s'échappe. Sagement. 💨",
                f"**{member.display_name}** déconnecté. Le mental n'a pas tenu. 📉",
                f"**{member.display_name}** est parti. OwBot garde les preuves. 📁",
                f"Déconnexion de **{member.display_name}**. Défaite ou problème technique ? Les deux probablement.",
                f"**{member.display_name}** a raccroché. On ne le blâme pas. On le comprend. 🫡",
            ]
            await channel.send(random.choice(msgs))


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceListener(bot))
