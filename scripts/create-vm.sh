#!/bin/bash
#
# Script de création VM GCP pour Telegram Bot + Claude Code CLI
# Recommandé: e2-small (2GB RAM, $12.23/month)
#

set -e

# ==========================================
# Configuration - À personnaliser
# ==========================================

# Prompt user for required variables
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter VM name (default: telegram-bot-vm): " VM_NAME
VM_NAME=${VM_NAME:-telegram-bot-vm}

read -p "Enter GCP Zone (default: us-central1-a): " ZONE
ZONE=${ZONE:-us-central1-a}

read -p "Enter Machine Type (e2-micro/e2-small/e2-medium, default: e2-small): " MACHINE_TYPE
MACHINE_TYPE=${MACHINE_TYPE:-e2-small}

REGION="${ZONE%-*}"  # Extract region from zone
BOOT_DISK_SIZE="30GB"
IMAGE_FAMILY="ubuntu-2204-lts"
IMAGE_PROJECT="ubuntu-os-cloud"

echo ""
echo "🚀 Création VM Telegram Bot sur GCP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Project: $PROJECT_ID"
echo "VM: $VM_NAME"
echo "Type: $MACHINE_TYPE"
echo "Zone: $ZONE"
echo "Disk: $BOOT_DISK_SIZE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Confirm before proceeding
read -p "Continue with VM creation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Création annulée"
    exit 1
fi

# 1. Vérifier que gcloud est configuré
echo "📋 Configuration gcloud..."
gcloud config set project $PROJECT_ID

# 2. Créer firewall rule pour webhook Telegram (port 8443)
echo ""
echo "🔥 Création firewall rule pour webhook Telegram..."
if ! gcloud compute firewall-rules describe telegram-webhook-allow --quiet 2>/dev/null; then
  gcloud compute firewall-rules create telegram-webhook-allow \
    --allow tcp:8443 \
    --source-ranges 0.0.0.0/0 \
    --description "Allow Telegram webhook on port 8443" \
    --target-tags telegram-bot
  echo "✅ Firewall rule créée"
else
  echo "✅ Firewall rule déjà existante"
fi

# 3. Créer startup script pour installer dépendances
echo ""
echo "📝 Création startup script..."
cat > /tmp/vm-startup-script.sh << 'EOF'
#!/bin/bash
# Startup script pour VM Telegram Bot

set -e

echo "🔧 Installation dépendances..."

# Update system
apt-get update
apt-get upgrade -y

# Install essentials
apt-get install -y \
  python3.11 \
  python3.11-venv \
  python3-pip \
  git \
  curl \
  tmux \
  vim \
  jq \
  build-essential

# Install Poetry
curl -sSL https://install.python-poetry.org | python3.11 -

# Add Poetry to PATH for all users
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /etc/profile.d/poetry.sh

# Install Node.js 20.x LTS
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# Install Claude Code CLI (NOT @anthropic-ai/claude)
npm install -g @anthropic-ai/claude-code

echo "✅ Dépendances installées"
echo "📋 Next steps:"
echo "  1. SSH into VM: gcloud compute ssh telegram-bot-vm --zone=YOUR_ZONE"
echo "  2. Authenticate Claude CLI: claude auth login"
echo "  3. Clone bot repository: git clone https://github.com/RichardAtCT/claude-code-telegram.git"
echo "  4. Clone your project repository"
echo "  5. Configure .env file"
echo "  6. Start bot: ~/telegram-bot/start-tmux.sh"
EOF

chmod +x /tmp/vm-startup-script.sh

# 4. Créer la VM
echo ""
echo "🖥️  Création de la VM..."
if gcloud compute instances describe $VM_NAME --zone=$ZONE --quiet 2>/dev/null; then
  echo "⚠️  VM $VM_NAME existe déjà"
  read -p "Supprimer et recréer? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    gcloud compute instances delete $VM_NAME --zone=$ZONE --quiet
  else
    echo "❌ Création annulée"
    exit 1
  fi
fi

gcloud compute instances create $VM_NAME \
  --zone=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --image-family=$IMAGE_FAMILY \
  --image-project=$IMAGE_PROJECT \
  --boot-disk-size=$BOOT_DISK_SIZE \
  --boot-disk-type=pd-standard \
  --tags=telegram-bot \
  --metadata-from-file=startup-script=/tmp/vm-startup-script.sh \
  --scopes=cloud-platform

echo ""
echo "✅ VM créée avec succès!"

# 5. Attendre que la VM soit prête
echo ""
echo "⏳ Attente démarrage VM (45s)..."
sleep 45

# 6. Récupérer IP externe
EXTERNAL_IP=$(gcloud compute instances describe $VM_NAME \
  --zone=$ZONE \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VM CRÉÉE AVEC SUCCÈS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "VM Name: $VM_NAME"
echo "External IP: $EXTERNAL_IP"
echo "Zone: $ZONE"
echo "Type: $MACHINE_TYPE"
echo ""
echo "📋 Prochaines étapes:"
echo ""
echo "1️⃣  Se connecter à la VM:"
echo "   gcloud compute ssh $VM_NAME --zone=$ZONE"
echo ""
echo "2️⃣  Ou configurer SSH dans ~/.ssh/config:"
echo "   Host telegram-bot-vm"
echo "       HostName $EXTERNAL_IP"
echo "       User YOUR_USERNAME"
echo "       IdentityFile ~/.ssh/google_compute_engine"
echo "       ServerAliveInterval 60"
echo "       ServerAliveCountMax 3"
echo "       TCPKeepAlive yes"
echo ""
echo "3️⃣  Vérifier installation (attendez 1-2 min pour startup script):"
echo "   ssh telegram-bot-vm"
echo "   claude --version"
echo "   poetry --version"
echo "   node --version"
echo ""
echo "4️⃣  Télécharger et exécuter setup-bot.sh:"
echo "   curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-telegram-gcp/main/scripts/setup-bot.sh | bash"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Cleanup
rm /tmp/vm-startup-script.sh
