#!/bin/bash
# ============================================================================
# Telegram Bot - One-Command Deployment Script
# ============================================================================
# Usage:
#   ./deploy.sh --token YOUR_BOT_TOKEN --username bot_name --user-id 123456
#
# This script will:
#   1. Validate prerequisites (Docker, secrets)
#   2. Build Docker image
#   3. Initialize Claude CLI authentication
#   4. Deploy bot with Docker Compose
#   5. Run health checks
# ============================================================================

set -e  # Exit on any error

# ============================================================================
# Colors and Formatting
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step() { echo -e "${BLUE}[STEP]${NC} $1"; }

# ============================================================================
# Configuration
# ============================================================================
PROJECT_NAME="telegram-bot"
IMAGE_NAME="telegram-bot"
VERSION=$(git describe --tags --always --dirty 2>/dev/null || echo "latest")
SECRETS_DIR="./secrets"

# ============================================================================
# Parse Command Line Arguments
# ============================================================================
TELEGRAM_BOT_TOKEN=""
TELEGRAM_BOT_USERNAME=""
ALLOWED_USERS=""
APPROVED_DIRECTORY="$HOME/telegram-bot/work"

show_usage() {
  cat << EOF
Usage: $0 [OPTIONS]

One-command deployment for Telegram Bot with Claude Code CLI

Required Options:
  --token TOKEN            Telegram bot token (from @BotFather)
  --username USERNAME      Telegram bot username
  --user-id USER_ID        Your Telegram user ID (from @userinfobot)

Optional:
  --work-dir PATH          Approved working directory (default: ~/telegram-bot/work)
  --help                   Show this help message

Example:
  $0 \\
    --token 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11 \\
    --username my_bot \\
    --user-id 1136600499

Get your credentials:
  1. Bot token: Talk to @BotFather on Telegram
  2. Bot username: Created when you talk to @BotFather
  3. Your user ID: Send /start to @userinfobot

EOF
  exit 1
}

while [[ $# -gt 0 ]]; do
  case $1 in
    --token)
      TELEGRAM_BOT_TOKEN="$2"
      shift 2
      ;;
    --username)
      TELEGRAM_BOT_USERNAME="$2"
      shift 2
      ;;
    --user-id)
      ALLOWED_USERS="[$2]"
      shift 2
      ;;
    --work-dir)
      APPROVED_DIRECTORY="$2"
      shift 2
      ;;
    --help)
      show_usage
      ;;
    *)
      log_error "Unknown option: $1"
      show_usage
      ;;
  esac
done

# ============================================================================
# Pre-flight Checks
# ============================================================================
log_step "🔍 Pre-flight checks..."

# Check required arguments
if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_BOT_USERNAME" ] || [ -z "$ALLOWED_USERS" ]; then
  log_error "Missing required arguments"
  show_usage
fi

# Check Docker installed
if ! command -v docker &> /dev/null; then
  log_error "Docker not installed"
  echo "Install Docker: https://docs.docker.com/get-docker/"
  exit 1
fi

# Check Docker Compose installed
if ! command -v docker compose &> /dev/null; then
  log_error "Docker Compose not installed"
  echo "Install Docker Compose: https://docs.docker.com/compose/install/"
  exit 1
fi

# Check Docker running
if ! docker info &> /dev/null; then
  log_error "Docker daemon not running"
  echo "Start Docker service and try again"
  exit 1
fi

# Check files exist
if [ ! -f "docker-compose.yml" ]; then
  log_error "docker-compose.yml not found"
  exit 1
fi

if [ ! -f "Dockerfile" ]; then
  log_error "Dockerfile not found"
  exit 1
fi

log_info "✅ All pre-flight checks passed"

# ============================================================================
# Create Secrets Directory and Files
# ============================================================================
log_step "🔐 Creating secrets..."

mkdir -p "$SECRETS_DIR"
chmod 700 "$SECRETS_DIR"

# Write secrets to files
echo "$TELEGRAM_BOT_TOKEN" > "$SECRETS_DIR/telegram_bot_token.txt"
echo "$TELEGRAM_BOT_USERNAME" > "$SECRETS_DIR/telegram_bot_username.txt"
echo "$ALLOWED_USERS" > "$SECRETS_DIR/allowed_users.txt"

# Secure permissions
chmod 600 "$SECRETS_DIR"/*.txt

log_info "✅ Secrets created in $SECRETS_DIR"
log_info "   - Token: ${TELEGRAM_BOT_TOKEN:0:10}... (${#TELEGRAM_BOT_TOKEN} chars)"
log_info "   - Username: $TELEGRAM_BOT_USERNAME"
log_info "   - Allowed users: $ALLOWED_USERS"

# ============================================================================
# Create Approved Working Directory
# ============================================================================
log_step "📁 Creating working directory..."

mkdir -p "$APPROVED_DIRECTORY"
chmod 755 "$APPROVED_DIRECTORY"

log_info "✅ Working directory: $APPROVED_DIRECTORY"

# ============================================================================
# Build Docker Image
# ============================================================================
log_step "🔨 Building Docker image (version: $VERSION)..."

docker build \
  --build-arg VERSION=$VERSION \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VCS_REF=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
  --progress=plain \
  -t ${IMAGE_NAME}:${VERSION} \
  -t ${IMAGE_NAME}:latest \
  . 2>&1 | grep -E "^#|^Step|^Successfully|ERROR" || true

if [ ${PIPESTATUS[0]} -ne 0 ]; then
  log_error "Docker build failed"
  exit 1
fi

log_info "✅ Docker image built: ${IMAGE_NAME}:${VERSION}"

# ============================================================================
# Run Health Check on Image
# ============================================================================
log_step "🏥 Running health check on image..."

docker run --rm ${IMAGE_NAME}:${VERSION} python -c "
import sys
try:
    # Check Python imports
    import telegram
    import anthropic
    print('✅ Python dependencies OK')

    # Check Claude CLI
    import subprocess
    result = subprocess.run(['claude', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        print('✅ Claude CLI available')
    else:
        print('❌ Claude CLI not found')
        sys.exit(1)

    sys.exit(0)
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
"

log_info "✅ Image health check passed"

# ============================================================================
# Stop Existing Containers
# ============================================================================
log_step "🛑 Stopping existing containers (if any)..."

docker compose down --timeout 30 2>/dev/null || log_warn "No existing containers to stop"

# ============================================================================
# Clean Up Old Images
# ============================================================================
log_step "🧹 Cleaning up old images..."

docker images ${IMAGE_NAME} --format "{{.ID}} {{.Tag}}" | \
  grep -v latest | \
  tail -n +4 | \
  awk '{print $1}' | \
  xargs -r docker rmi -f 2>/dev/null || log_info "No old images to clean"

# ============================================================================
# Initialize Claude CLI Authentication
# ============================================================================
log_step "🔑 Initializing Claude CLI authentication..."

log_warn "You need to authenticate Claude CLI manually"
echo ""
echo "In a moment, a Docker container will start and prompt you to:"
echo "  1. Visit an Anthropic authentication URL"
echo "  2. Login with your Claude account"
echo "  3. Authorize the CLI"
echo ""
read -p "Press ENTER to continue with Claude authentication..."

# Run interactive Claude login in container
docker run -it --rm \
  -v telegram-bot_claude-auth:/home/appuser/.claude \
  ${IMAGE_NAME}:latest \
  bash -c "
    echo '🔐 Starting Claude CLI authentication...'
    echo ''
    claude auth login

    if [ \$? -eq 0 ]; then
      echo ''
      echo '✅ Authentication successful!'
      echo ''
      echo 'Verifying authentication...'
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

log_info "✅ Claude credentials stored in volume 'telegram-bot_claude-auth'"

# ============================================================================
# Start Services
# ============================================================================
log_step "🚀 Starting services with Docker Compose..."

# Override approved directory in docker-compose
export APPROVED_DIRECTORY

docker compose up -d --remove-orphans

log_info "✅ Services started"

# ============================================================================
# Wait for Health Check
# ============================================================================
log_step "⏳ Waiting for health check (max 90s)..."

TIMEOUT=90
ELAPSED=0
echo -n "Checking: "

while [ $ELAPSED -lt $TIMEOUT ]; do
  HEALTH=$(docker inspect --format='{{.State.Health.Status}}' ${PROJECT_NAME} 2>/dev/null || echo "starting")

  if [ "$HEALTH" = "healthy" ]; then
    echo ""
    log_info "✅ Service is healthy!"
    break
  elif [ "$HEALTH" = "unhealthy" ]; then
    echo ""
    log_error "Service health check failed!"
    log_error "Logs:"
    docker compose logs --tail=50
    exit 1
  fi

  echo -n "."
  sleep 3
  ELAPSED=$((ELAPSED + 3))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  echo ""
  log_warn "Health check timeout - check logs manually with: docker compose logs"
fi

# ============================================================================
# Display Status
# ============================================================================
log_step "📊 Deployment status:"

docker compose ps

echo ""
log_step "📋 Recent logs:"
docker compose logs --tail=30

echo ""
log_info "============================================================"
log_info "✅ Deployment complete!"
log_info "============================================================"
echo ""
echo "📝 Useful commands:"
echo "  docker compose logs -f                     # Follow logs"
echo "  docker compose restart                     # Restart bot"
echo "  docker compose exec telegram-bot bash      # Enter container"
echo "  docker compose exec telegram-bot claude    # Run Claude CLI"
echo "  docker compose down                        # Stop all services"
echo ""
echo "🔍 Monitoring:"
echo "  docker stats telegram-bot                  # Resource usage"
echo "  docker inspect telegram-bot                # Container details"
echo ""
echo "🤖 Bot info:"
echo "  Username: @$TELEGRAM_BOT_USERNAME"
echo "  Allowed users: $ALLOWED_USERS"
echo "  Working directory: $APPROVED_DIRECTORY"
echo ""
echo "🧪 Test your bot:"
echo "  1. Open Telegram"
echo "  2. Search for @$TELEGRAM_BOT_USERNAME"
echo "  3. Send /start"
echo "  4. Try: 'List all files in the working directory'"
echo ""
log_info "Happy coding! 🚀"
