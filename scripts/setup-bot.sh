#!/bin/bash
#
# Script de setup complet pour Telegram Bot sur VM
# À exécuter une fois connecté à la VM
#

set -e

echo "🚀 Setup Telegram Bot + Claude Code CLI"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Configuration - Demander à l'utilisateur
read -p "Enter your Telegram Bot Token (from @BotFather): " TELEGRAM_BOT_TOKEN
read -p "Enter your bot username (without @): " BOT_USERNAME
read -p "Enter your Telegram User ID (from @userinfobot): " ALLOWED_USER_ID
read -p "Enter your project Git repository URL: " PROJECT_REPO
read -p "Enter your project directory name (e.g., my-project): " PROJECT_DIR_NAME

BOT_REPO="https://github.com/RichardAtCT/claude-code-telegram.git"
WORK_DIR="/home/$USER/telegram-bot"

echo ""
echo "📋 Configuration:"
echo "  Bot Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "  Bot Username: @$BOT_USERNAME"
echo "  Allowed User ID: $ALLOWED_USER_ID"
echo "  Project Repo: $PROJECT_REPO"
echo "  Project Dir: $PROJECT_DIR_NAME"
echo "  Work Dir: $WORK_DIR"
echo ""

read -p "Confirm configuration? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Setup annulé"
    exit 1
fi

# 1. Vérifier dépendances
echo "📋 Vérification dépendances..."
for cmd in python3.11 poetry git tmux claude npm; do
  if command -v $cmd &> /dev/null; then
    echo "✅ $cmd installé"
  else
    echo "❌ $cmd manquant"
    echo "⚠️  Attendez que le startup script VM se termine (1-2 min après création VM)"
    exit 1
  fi
done
echo ""

# 2. Créer dossier de travail
echo "📁 Création dossier de travail..."
mkdir -p $WORK_DIR
cd $WORK_DIR
echo "✅ Dossier créé: $WORK_DIR"
echo ""

# 3. Cloner repository du bot
echo "📥 Clonage RichardAtCT/claude-code-telegram..."
if [ -d "claude-code-telegram" ]; then
  echo "⚠️  Repository déjà cloné"
  cd claude-code-telegram
  git pull
else
  git clone $BOT_REPO
  cd claude-code-telegram
fi
echo "✅ Repository cloné"
echo ""

# 4. Installer dépendances Python avec Poetry
echo "📦 Installation dépendances Python..."
export PATH="/home/$USER/.local/bin:$PATH"
poetry install
echo "✅ Dépendances installées"
echo ""

# 5. Créer fichier .env
echo "⚙️  Création fichier .env..."
cat > .env << EOF
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_BOT_USERNAME=$BOT_USERNAME

# Security - Base directory for project access
APPROVED_DIRECTORY=/home/$USER/telegram-bot/$PROJECT_DIR_NAME

# User Access Control (JSON array required for Pydantic validation)
ALLOWED_USERS=[$ALLOWED_USER_ID]

# Claude Settings
USE_SDK=false  # Use Claude CLI subprocess
CLAUDE_MAX_COST_PER_USER=10.0
CLAUDE_TIMEOUT_SECONDS=300

# Tools Claude can use (JSON array required for Pydantic validation)
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]

# Rate Limiting
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60

# Features
ENABLE_FILE_UPLOADS=true

# Development
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=sqlite:///telegram_bot.db
EOF

echo "✅ Fichier .env créé"
echo ""

# 6. Cloner project repository
echo "📥 Clonage project repository..."
cd $WORK_DIR

if [ -d "$PROJECT_DIR_NAME" ]; then
  echo "⚠️  Repository $PROJECT_DIR_NAME déjà cloné"
  cd $PROJECT_DIR_NAME
  git pull
else
  git clone $PROJECT_REPO
  cd $PROJECT_DIR_NAME
fi

# Configurer Git
echo "Configurer Git user name: "
read GIT_USER_NAME
echo "Configurer Git user email: "
read GIT_USER_EMAIL

git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"

echo "✅ Repository cloné et configuré"
echo ""

# 7. Créer script de démarrage tmux
echo "📝 Création script de démarrage tmux..."
cat > $WORK_DIR/start-bot.sh << 'SCRIPT_EOF'
#!/bin/bash

WORK_DIR="/home/$USER/telegram-bot"
cd $WORK_DIR/claude-code-telegram

# Charger PATH pour Poetry
export PATH="/home/$USER/.local/bin:$PATH"

# Démarrer le bot avec Poetry
echo "🤖 Démarrage Telegram Bot..."
poetry run python -m src.main --debug
SCRIPT_EOF

chmod +x $WORK_DIR/start-bot.sh
echo "✅ Script créé: $WORK_DIR/start-bot.sh"
echo ""

# 8. Créer script tmux
echo "📝 Création script tmux..."
cat > $WORK_DIR/start-tmux.sh << 'TMUX_EOF'
#!/bin/bash

SESSION_NAME="telegram-bot"

# Tuer session existante si présente
tmux kill-session -t $SESSION_NAME 2>/dev/null || true

# Créer nouvelle session tmux
tmux new-session -d -s $SESSION_NAME

# Lancer le bot dans la session tmux
tmux send-keys -t $SESSION_NAME "/home/$USER/telegram-bot/start-bot.sh" C-m

echo "✅ Bot démarré dans tmux session: $SESSION_NAME"
echo ""
echo "📋 Commandes utiles:"
echo "  • Attacher à la session: tmux attach -t $SESSION_NAME"
echo "  • Détacher: Ctrl+B puis D"
echo "  • Voir logs en temps réel: tmux attach -t $SESSION_NAME"
TMUX_EOF

chmod +x $WORK_DIR/start-tmux.sh
echo "✅ Script créé: $WORK_DIR/start-tmux.sh"
echo ""

# 9. Instructions finales
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SETUP TERMINÉ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "1️⃣  Authentifier Claude CLI:"
echo "   claude auth login"
echo "   (Ouvrez le lien dans un navigateur et connectez-vous)"
echo ""
echo "2️⃣  Démarrer le bot en tmux:"
echo "   $WORK_DIR/start-tmux.sh"
echo ""
echo "3️⃣  Vérifier les logs:"
echo "   tmux attach -t telegram-bot"
echo "   (Détacher: Ctrl+B puis D)"
echo ""
echo "4️⃣  Tester le bot sur Telegram:"
echo "   • Ouvrir Telegram"
echo "   • Chercher @$BOT_USERNAME"
echo "   • Envoyer /start"
echo "   • Poser une question: 'List files in the project'"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📚 Documentation complète:"
echo "   https://github.com/YOUR_USERNAME/claude-telegram-gcp"
echo ""
