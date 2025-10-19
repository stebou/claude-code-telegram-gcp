#!/bin/bash
# ============================================================================
# Claude Telegram Bot - One-Line Installer
# ============================================================================
# Usage:
#   curl -sSL https://raw.githubusercontent.com/stebou/claude-code-telegram-gcp/main/install.sh | bash
#
# Or with parameters:
#   curl -sSL https://... | bash -s -- --token XXX --username YYY --user-id ZZZ
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}━━━${NC} $1"; }

# ============================================================================
# Banner
# ============================================================================
clear
cat << "EOF"
  ______ _                 _        ______        _
 / _____) |               | |      (____  \      | |
| /     | | ____  _   _ _ | | ___   ____)  )___ _| |_
| |     | |/ _  || | | | || |/ _ \ |  __  (/ _ (_   _)
| \_____| ( ( | || |_| | || | |_| || |__)  ) |_| || |_
 \______)_|\_||_| \____| \_)_)___/ |______/ \___/  \__)

 🤖 Telegram Bot with Claude Code CLI
 📦 One-Line Installer

EOF

log_step "Starting installation..."

# ============================================================================
# Parse Arguments
# ============================================================================
TELEGRAM_BOT_TOKEN=""
TELEGRAM_BOT_USERNAME=""
ALLOWED_USERS=""
WORK_DIR="$HOME/claude-telegram-bot"

while [[ $# -gt 0 ]]; do
  case $1 in
    --token) TELEGRAM_BOT_TOKEN="$2"; shift 2 ;;
    --username) TELEGRAM_BOT_USERNAME="$2"; shift 2 ;;
    --user-id) ALLOWED_USERS="[$2]"; shift 2 ;;
    --work-dir) WORK_DIR="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# ============================================================================
# Interactive Input if not provided
# ============================================================================
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo ""
  log_step "📱 Configuration Telegram Bot"
  echo ""
  echo "Créez votre bot via @BotFather sur Telegram :"
  echo "  1. Ouvrir Telegram et chercher @BotFather"
  echo "  2. Envoyer /newbot"
  echo "  3. Suivre les instructions"
  echo ""
  read -p "🔑 Telegram Bot Token (123456:ABC-DEF...): " TELEGRAM_BOT_TOKEN
fi

if [ -z "$TELEGRAM_BOT_USERNAME" ]; then
  read -p "🤖 Bot Username (sans @): " TELEGRAM_BOT_USERNAME
fi

if [ -z "$ALLOWED_USERS" ]; then
  echo ""
  echo "Obtenez votre Telegram User ID via @userinfobot :"
  echo "  1. Chercher @userinfobot sur Telegram"
  echo "  2. Envoyer /start"
  echo "  3. Copier votre ID"
  echo ""
  read -p "👤 Votre Telegram User ID: " USER_ID
  ALLOWED_USERS="[$USER_ID]"
fi

# Validate inputs
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_BOT_USERNAME" ] || [ -z "$ALLOWED_USERS" ]; then
  log_error "Missing required parameters"
  exit 1
fi

log_info "✅ Configuration received"
echo "   Token: ${TELEGRAM_BOT_TOKEN:0:10}..."
echo "   Username: @$TELEGRAM_BOT_USERNAME"
echo "   Allowed users: $ALLOWED_USERS"
echo ""

# ============================================================================
# Install Docker if needed
# ============================================================================
log_step "🐳 Checking Docker..."

if ! command -v docker &> /dev/null; then
  log_warn "Docker not installed - Installing..."

  # Detect OS
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
  else
    log_error "Cannot detect OS"
    exit 1
  fi

  case $OS in
    ubuntu|debian)
      log_info "Installing Docker on Ubuntu/Debian..."
      sudo apt-get update -qq
      sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release

      # Add Docker GPG key
      sudo mkdir -p /etc/apt/keyrings
      curl -fsSL https://download.docker.com/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

      # Add Docker repo
      echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
        $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

      # Install Docker
      sudo apt-get update -qq
      sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

      # Add current user to docker group
      sudo usermod -aG docker $USER
      log_warn "⚠️  You've been added to docker group - You may need to re-login"
      ;;

    centos|rhel|fedora)
      log_info "Installing Docker on CentOS/RHEL/Fedora..."
      sudo yum install -y yum-utils
      sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
      sudo yum install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
      sudo systemctl start docker
      sudo systemctl enable docker
      sudo usermod -aG docker $USER
      ;;

    *)
      log_error "Unsupported OS: $OS"
      echo "Please install Docker manually: https://docs.docker.com/get-docker/"
      exit 1
      ;;
  esac

  log_info "✅ Docker installed"
else
  log_info "✅ Docker already installed: $(docker --version)"
fi

# Start Docker if not running
if ! sudo systemctl is-active --quiet docker 2>/dev/null; then
  log_info "Starting Docker service..."
  sudo systemctl start docker || true
fi

# ============================================================================
# Clone Repository
# ============================================================================
log_step "📥 Downloading bot code..."

# Install git if needed
if ! command -v git &> /dev/null; then
  log_warn "Git not installed - Installing..."
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    case $ID in
      ubuntu|debian) sudo apt-get install -y -qq git ;;
      centos|rhel|fedora) sudo yum install -y git ;;
    esac
  fi
fi

# Remove old installation
if [ -d "$WORK_DIR" ]; then
  log_warn "Existing installation found - Removing..."
  rm -rf "$WORK_DIR"
fi

# Clone
mkdir -p "$(dirname "$WORK_DIR")"
git clone -q https://github.com/stebou/claude-code-telegram-gcp.git "$WORK_DIR"
cd "$WORK_DIR"

log_info "✅ Code downloaded to $WORK_DIR"

# ============================================================================
# Build Docker Image
# ============================================================================
log_step "🔨 Building Docker image (this may take 3-5 minutes)..."

docker build -t telegram-bot:latest -f Dockerfile . 2>&1 | grep -E "^Step|^Successfully|ERROR" || true

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  log_error "Docker build failed"
  exit 1
fi

log_info "✅ Docker image built"

# ============================================================================
# Create Working Directory
# ============================================================================
log_step "📁 Creating working directory..."

mkdir -p "$WORK_DIR/work"
chmod 755 "$WORK_DIR/work"

log_info "✅ Working directory: $WORK_DIR/work"

# ============================================================================
# Authenticate Claude CLI
# ============================================================================
log_step "🔑 Claude CLI Authentication"
echo ""
log_warn "You need to authenticate with your Claude account"
echo ""
echo "In a moment, you will:"
echo "  1. See an authentication URL"
echo "  2. Visit that URL in your browser"
echo "  3. Login with your Claude account"
echo "  4. Authorize the CLI"
echo ""
read -p "Press ENTER to start authentication..."

# Run interactive Claude auth
docker run -it --rm \
  -v telegram-bot_claude-auth:/home/appuser/.claude \
  telegram-bot:latest \
  bash -c "
    echo '🔐 Starting Claude CLI authentication...'
    echo ''
    claude auth login

    if [ \$? -eq 0 ]; then
      echo ''
      echo '✅ Authentication successful!'
      echo ''
      echo 'Verifying...'
      claude auth status
    else
      echo '❌ Authentication failed'
      exit 1
    fi
  "

if [ $? -ne 0 ]; then
  log_error "Claude authentication failed"
  exit 1
fi

log_info "✅ Claude authenticated"

# ============================================================================
# Start Bot with Docker Run
# ============================================================================
log_step "🚀 Starting bot..."

# Stop existing container
docker stop telegram-bot 2>/dev/null || true
docker rm telegram-bot 2>/dev/null || true

# Start new container
docker run -d \
  --name telegram-bot \
  --restart unless-stopped \
  -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
  -e TELEGRAM_BOT_USERNAME="$TELEGRAM_BOT_USERNAME" \
  -e ALLOWED_USERS="$ALLOWED_USERS" \
  -e APPROVED_DIRECTORY=/approved-directory \
  -v telegram-bot_claude-auth:/home/appuser/.claude \
  -v telegram-bot_bot-data:/app/data \
  -v "$WORK_DIR/work":/approved-directory \
  telegram-bot:latest

# Wait for health check
log_info "⏳ Waiting for bot to start (max 60s)..."

TIMEOUT=60
ELAPSED=0
echo -n "Checking: "

while [ $ELAPSED -lt $TIMEOUT ]; do
  HEALTH=$(docker inspect --format='{{.State.Health.Status}}' telegram-bot 2>/dev/null || echo "starting")

  if [ "$HEALTH" = "healthy" ]; then
    echo ""
    log_info "✅ Bot is healthy!"
    break
  elif [ "$HEALTH" = "unhealthy" ]; then
    echo ""
    log_error "Bot health check failed!"
    docker logs telegram-bot --tail=50
    exit 1
  fi

  echo -n "."
  sleep 2
  ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  echo ""
  log_warn "Health check timeout - Bot may still be starting"
fi

# ============================================================================
# Success!
# ============================================================================
echo ""
log_step "✅ Installation Complete!"
echo ""
cat << EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🎉 Your Telegram Bot is Running!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Bot: @$TELEGRAM_BOT_USERNAME
👤 Authorized: $ALLOWED_USERS
📁 Working directory: $WORK_DIR/work

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 🧪 Test Your Bot
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Open Telegram
2. Search for @$TELEGRAM_BOT_USERNAME
3. Send /start
4. Try: "List all files in the working directory"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 📝 Useful Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View logs:
  docker logs -f telegram-bot

Restart bot:
  docker restart telegram-bot

Stop bot:
  docker stop telegram-bot

Start bot:
  docker start telegram-bot

Remove completely:
  docker stop telegram-bot && docker rm telegram-bot

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Happy coding! 🚀

EOF

# Show recent logs
log_info "📋 Recent logs:"
docker logs telegram-bot --tail=20
