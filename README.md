# OwBot 🎮

Bot Discord intelligent autour d'Overwatch 2 — drôle, autonome, et qui apprend à connaître tes potes.

## Fonctionnalités

### Overwatch
| Commande | Description |
|----------|-------------|
| `/patchnotes` | Derniers patch notes OW2 (scraping officiel) |
| `/patchlink` | Lien direct vers les patch notes |
| `/hero [role]` | Suggère un héros aléatoire |
| `/quote` | Citation Overwatch |
| `/taunt` | Balance un taunt post-partie |
| `/duel @joueur` | Duel de héros aléatoires |

### Mémoire & Profils joueurs
| Commande | Description |
|----------|-------------|
| `/profil [@joueur]` | Affiche le profil analysé d'un joueur |
| `/addphrase "texte" [@joueur]` | Enregistre une punchline |
| `/serverstats` | Stats globales du serveur |

### IA — Raps & Blagues
| Commande | Description |
|----------|-------------|
| `/rap` | Génère un rap freestyle sur les joueurs |
| `/roast @joueur` | Roast personnalisé basé sur ses habitudes |
| `/blague` | Blague Overwatch IA |

### Vocal
| Commande | Description |
|----------|-------------|
| `/join` | OwBot rejoint ton vocal et commente |
| `/leave` | OwBot quitte le vocal |

### Administration
| Commande | Description |
|----------|-------------|
| `/setup_auto` | Active les messages autonomes dans un salon |
| `/setup_daily` | Active le héros du jour (9h UTC) |

## Installation

```bash
# 1. Clone et install
git clone <repo>
cd OwBot-
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Édite .env avec ton token Discord

# 3. Lance
python bot.py
```

## Variables d'environnement

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `DISCORD_TOKEN` | ✅ | Token du bot Discord |
| `ANTHROPIC_API_KEY` | ❌ | API Claude pour raps/blagues IA |
| `OPENAI_API_KEY` | ❌ | API Whisper pour transcription vocale |

Sans les clés optionnelles, le bot utilise des templates intégrés.

## Transcription vocale locale (sans API)

```bash
pip install faster-whisper
```

Décommente la ligne dans `requirements.txt` et le bot transcrit l'audio localement.

## Structure

```
OwBot-/
├── bot.py                  # Entrée principale
├── cogs/
│   ├── patchnotes.py       # Patch notes OW2
│   ├── fun.py              # Commandes fun + réactions auto
│   ├── memory.py           # Apprentissage des habitudes joueurs
│   ├── autodj.py           # Raps, roasts, messages autonomes
│   └── voice_listener.py  # Écoute vocale + commentaires
├── data/
│   └── owbot.db            # Base SQLite (générée automatiquement)
└── requirements.txt
```
