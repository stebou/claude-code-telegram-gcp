# 🤖 Claude Code via Telegram Bot

**Contrôlez Claude Code CLI directement depuis Telegram** - Un bot Telegram qui donne accès complet à Claude Code avec tous ses outils (Read, Write, Edit, Bash, Git, etc.)

## ✨ Ce que ça fait

Envoyez des messages à votre bot Telegram et Claude Code exécute les tâches :
- 📖 Lire/modifier du code
- 🔧 Exécuter des commandes (tests, build, git)
- 🌐 Faire des recherches web
- ✍️ Créer/éditer des fichiers
- 💬 Poser des questions interactives
- ⚡ Animations en temps réel (typing indicator ●●●)

**Architecture** : CLI subprocess (comme [richardatct](https://github.com/RichardAtCT/claude-code-telegram)) avec streaming complet des outils.

## 🚀 Installation Rapide (5 min)

### 1. Prérequis

- **GCP Account** ([free tier OK](https://cloud.google.com/free))
- **Token Telegram** : Créez un bot via [@BotFather](https://t.me/botfather)
- **Claude CLI** : Compte Anthropic ([console](https://console.anthropic.com/))
- **Votre Telegram ID** : Obtenez-le via [@userinfobot](https://t.me/userinfobot)

### 2. Créer la VM GCP

```bash
# Clone ce repo
git clone https://github.com/stebou/claude-code-telegram-gcp.git
cd claude-code-telegram-gcp

# Créer la VM (e2-small, 2GB RAM, 30GB disk)
gcloud compute instances create telegram-bot-vm \
  --zone=us-central1-a \
  --machine-type=e2-small \
  --image-family=ubuntu-2204-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=30GB
```

### 3. Installer le bot

```bash
# SSH dans la VM
gcloud compute ssh telegram-bot-vm --zone=us-central1-a

# Installer dépendances
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv git tmux

# Installer Poetry
curl -sSL https://install.python-poetry.org | python3 -
export PATH="$HOME/.local/bin:$PATH"

# Installer Claude CLI
npm install -g @anthropic-ai/claude

# Cloner le bot
mkdir -p ~/telegram-bot
cd ~/telegram-bot
git clone https://github.com/stebou/claude-code-telegram-gcp.git
cd claude-code-telegram-gcp/bot

# Installer dépendances Python
poetry install
```

### 4. Configurer

```bash
# Créer .env
cd ~/telegram-bot/claude-code-telegram-gcp/bot
cp .env.example .env
nano .env
```

**Remplissez** :
```bash
TELEGRAM_BOT_TOKEN=votre_token_botfather
TELEGRAM_BOT_USERNAME=votre_bot_username
ALLOWED_USERS=[votre_telegram_id]
APPROVED_DIRECTORY=/home/votre_user/telegram-bot/votre_repo
```

**Authentifier Claude** :
```bash
claude auth login
# Suivez le lien dans votre navigateur
```

### 5. Lancer

```bash
# Créer script de démarrage
cat > ~/telegram-bot/start-bot.sh << 'EOF'
#!/bin/bash
tmux kill-session -t telegram-bot 2>/dev/null
tmux new-session -d -s telegram-bot
tmux send-keys -t telegram-bot "cd ~/telegram-bot/claude-code-telegram-gcp/bot" C-m
tmux send-keys -t telegram-bot 'export PATH="/home/$USER/.local/bin:$PATH"' C-m
tmux send-keys -t telegram-bot 'echo "🤖 Démarrage Telegram Bot..."' C-m
tmux send-keys -t telegram-bot "poetry run python -m src.main" C-m
echo "✅ Bot démarré dans tmux session 'telegram-bot'"
echo "Pour voir les logs: tmux attach -t telegram-bot"
echo "Pour détacher: Ctrl+B puis D"
EOF

chmod +x ~/telegram-bot/start-bot.sh

# Démarrer le bot
~/telegram-bot/start-bot.sh
```

### 6. Tester

1. Ouvrez Telegram
2. Cherchez votre bot
3. Envoyez `/start`
4. Testez : "Liste tous les fichiers Python du projet"

✅ **C'est tout !** Le bot est opérationnel.

## 📊 Fonctionnalités

### Outils Disponibles

- 📖 **Read** - Lit n'importe quel fichier
- ✍️ **Write** - Crée de nouveaux fichiers
- ✏️ **Edit** - Modifie du code existant
- 🔧 **Bash** - Exécute des commandes shell
- 🔍 **Glob** - Trouve des fichiers par pattern
- 🔎 **Grep** - Cherche dans le code
- 🌐 **WebSearch** - Recherche web
- 📋 **TodoWrite** - Gère des listes de tâches
- 🎯 **Task** - Lance des tâches multi-étapes
- 💬 **AskUserQuestion** - Pose des questions
- ⚡ **Skill** - Exécute des skills personnalisés
- 🔨 **SlashCommand** - Commandes custom

### Streaming en Temps Réel

Le bot affiche :
- ✅ Animation "typing" (●●●) pendant le traitement
- 🔧 Outils utilisés en temps réel
- 🤖 Réflexions de Claude
- ✨ Résultats au fur et à mesure

### Exemple d'Utilisation

```
Vous: "Ajoute une fonction de login avec JWT"

Bot: 🔧 Read
     📖 Lecture de auth/

Bot: 🔧 Write
     ✍️ Création de auth/jwt_handler.py

Bot: 🔧 Edit
     ✏️ Mise à jour de main.py

Bot: 🔧 Bash
     🧪 pytest tests/test_auth.py -v
     ✅ Tests OK

Bot: 🔧 Bash
     📤 git commit -m "feat: Add JWT auth"
     🚀 git push origin main

✅ Feature complète et déployée !
```

## 🛠️ Gestion

### Voir les logs

```bash
# Attacher à tmux
tmux attach -t telegram-bot
# Détacher: Ctrl+B puis D

# Ou depuis votre machine locale
gcloud compute ssh telegram-bot-vm --zone=us-central1-a \
  --command="tmux capture-pane -t telegram-bot -p | tail -50"
```

### Redémarrer

```bash
ssh telegram-bot-vm
~/telegram-bot/start-bot.sh
```

### Mettre à jour le code

```bash
ssh telegram-bot-vm
cd ~/telegram-bot/claude-code-telegram-gcp
git pull
poetry install
~/telegram-bot/start-bot.sh
```

### Arrêter la VM (économie)

```bash
# Arrêter
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a

# Redémarrer
gcloud compute instances start telegram-bot-vm --zone=us-central1-a
gcloud compute ssh telegram-bot-vm --zone=us-central1-a \
  --command="~/telegram-bot/start-bot.sh"
```

## 💰 Coût

- **VM e2-small** : ~$12/mois (2GB RAM, recommandé)
- **Disk 30GB** : ~$1/mois
- **Claude API** : Variable selon usage
- **Total** : ~$15-20/mois

## 🔒 Sécurité

- ✅ **Sandbox** : Accès limité à `APPROVED_DIRECTORY`
- ✅ **Whitelist** : Seuls les users dans `ALLOWED_USERS`
- ✅ **Rate limiting** : Protection DoS
- ✅ **Commandes bloquées** : `rm -rf /`, `sudo`, etc.

## 📝 Configuration Avancée

### .env Complet

```bash
# Telegram
TELEGRAM_BOT_TOKEN=123456:ABC-DEF
TELEGRAM_BOT_USERNAME=my_bot

# Sécurité
ALLOWED_USERS=[1136600499]
APPROVED_DIRECTORY=/home/user/telegram-bot/repo

# Claude
USE_SDK=false
CLAUDE_MAX_TURNS=10
CLAUDE_MAX_COST_PER_USER=10.0
CLAUDE_TIMEOUT_SECONDS=900
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Features
ENABLE_FILE_UPLOADS=true
DEBUG=false
LOG_LEVEL=INFO
```

### VSCode Remote SSH

Ajoutez à `~/.ssh/config` :

```ssh
Host telegram-bot-vm
    HostName YOUR_VM_IP
    User YOUR_USERNAME
    IdentityFile ~/.ssh/google_compute_engine
    ServerAliveInterval 60
    TCPKeepAlive yes
```

Puis dans VSCode :
1. Installer extension "Remote - SSH"
2. F1 → "Remote-SSH: Connect to Host"
3. Sélectionner `telegram-bot-vm`

## 🐛 Dépannage

### Bot ne répond pas

```bash
# Vérifier si le bot tourne
ssh telegram-bot-vm
tmux attach -t telegram-bot

# Vérifier Claude auth
claude auth status

# Vérifier .env
cat ~/telegram-bot/claude-code-telegram-gcp/bot/.env
```

### Erreur "Settings object has no attribute"

Votre `.env` est mal formaté. Utilisez des **JSON arrays** :

❌ Incorrect :
```bash
ALLOWED_USERS=123456
CLAUDE_ALLOWED_TOOLS=Read,Write
```

✅ Correct :
```bash
ALLOWED_USERS=[123456]
CLAUDE_ALLOWED_TOOLS=["Read","Write"]
```

### VM out of memory

Upgradez vers e2-medium (4GB RAM) :

```bash
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a
gcloud compute instances set-machine-type telegram-bot-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium
gcloud compute instances start telegram-bot-vm --zone=us-central1-a
```

## 🙏 Remerciements

Architecture basée sur [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram).

Améliorations :
- ✅ CLI subprocess au lieu de SDK
- ✅ Streaming complet des outils
- ✅ Animation typing indicator (●●●)
- ✅ Fix throttling sur 2nd+ messages
- ✅ Parsing stream-json corrigé
- ✅ Configuration Pydantic
- ✅ Documentation GCP complète

## 📄 Licence

MIT License

## 📞 Support

- **GitHub** : [Issues](https://github.com/stebou/claude-code-telegram-gcp/issues)
- **Repo Original** : [richardatct](https://github.com/RichardAtCT/claude-code-telegram)

---

**⚡ Déployé en < 5 min | 💰 ~$15/mois | 🚀 Production-ready**
