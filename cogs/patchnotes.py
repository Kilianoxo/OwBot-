import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
from bs4 import BeautifulSoup

PATCH_NOTES_URL = "https://overwatch.blizzard.com/en-us/news/patch-notes/"

HERO_COLORS = {
    "tank": 0x4FC3F7,
    "damage": 0xEF5350,
    "support": 0x66BB6A,
    "default": 0xFF6B00,
}


class PatchNotes(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="patchnotes", description="Affiche les derniers patch notes Overwatch 2")
    async def patchnotes(self, interaction: discord.Interaction):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; OwBot/1.0)"}
                async with session.get(PATCH_NOTES_URL, headers=headers) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            "Impossible de récupérer les patch notes pour le moment. Réessaie plus tard !",
                            ephemeral=True,
                        )
                        return
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")

            # Titre du dernier patch (balise h1 ou h2 principale)
            patch_title = soup.find("h1", class_=lambda c: c and "PatchNotes" in c)
            if not patch_title:
                patch_title = soup.find("h1")

            title_text = patch_title.get_text(strip=True) if patch_title else "Dernière mise à jour"

            # Date du patch
            patch_date = soup.find("div", class_=lambda c: c and "date" in (c or "").lower())
            date_text = patch_date.get_text(strip=True) if patch_date else ""

            # Sections principales (héros modifiés)
            sections = []
            hero_sections = soup.find_all(
                ["h4", "h3"],
                class_=lambda c: c and ("Hero" in (c or "") or "hero" in (c or "")),
                limit=8,
            )

            if not hero_sections:
                # Fallback : récupérer les premiers titres de sections
                hero_sections = soup.find_all(["h3", "h4"], limit=8)

            for section in hero_sections[:6]:
                name = section.get_text(strip=True)
                if name:
                    sections.append(f"• {name}")

            embed = discord.Embed(
                title=f"Patch Notes — {title_text}",
                url=PATCH_NOTES_URL,
                description=(
                    f"**{date_text}**\n\n"
                    + (
                        "**Héros modifiés :**\n" + "\n".join(sections)
                        if sections
                        else "Consulte la page officielle pour les détails complets."
                    )
                ),
                color=HERO_COLORS["default"],
            )
            embed.set_footer(text="Source : overwatch.blizzard.com")
            embed.set_thumbnail(
                url="https://blz-contentstack-images.akamaized.net/v3/assets/blt9c12f249ac15c7ec/blt2f18bf5fb3c3f5c8/Overwatch_Logo.png"
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"Une erreur s'est produite : `{e}`\nVoici le lien direct : {PATCH_NOTES_URL}",
                ephemeral=True,
            )

    @app_commands.command(name="patchlink", description="Donne le lien vers les patch notes officiels")
    async def patchlink(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Patch Notes Overwatch 2",
            description=f"[Cliquez ici pour lire les derniers patch notes]({PATCH_NOTES_URL})",
            color=HERO_COLORS["default"],
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(PatchNotes(bot))
