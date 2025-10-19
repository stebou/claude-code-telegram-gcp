# Google Cloud Platform Deployment Guide

Guide complet pour déployer un bot Telegram avec Claude Code CLI sur GCP.

## 📋 Prérequis

### 1. Compte GCP

1. Créer un compte sur [Google Cloud Console](https://console.cloud.google.com/)
2. Activer la facturation (carte bancaire requise même pour le free tier)
3. Créer un nouveau projet ou utiliser un existant

### 2. Google Cloud SDK (gcloud CLI)

**MacOS**:
```bash
brew install --cask google-cloud-sdk
```

**Linux**:
```bash
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
```

**Windows**:
Télécharger l'installateur depuis [cloud.google.com/sdk](https://cloud.google.com/sdk)

**Initialisation**:
```bash
gcloud init
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

### 3. APIs Activées

Activer les APIs nécessaires:
```bash
gcloud services enable compute.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

## 🚀 Déploiement Étape par Étape

### Étape 1: Cloner ce Repository

```bash
git clone https://github.com/YOUR_USERNAME/claude-telegram-gcp.git
cd claude-telegram-gcp
```

### Étape 2: Créer la VM GCP

Exécuter le script de création:

```bash
bash scripts/create-vm.sh
```

Le script va demander:
- **GCP Project ID**: Votre ID de projet (trouvable dans GCP Console)
- **VM Name**: Nom de la VM (défaut: telegram-bot-vm)
- **Zone**: Zone GCP (défaut: us-central1-a)
- **Machine Type**: Type de machine (défaut: e2-small)

**Recommandé**: e2-small (2GB RAM, $12.23/mois)

**Ce qui sera créé**:
- 1 VM instance e2-small (Ubuntu 22.04 LTS)
- 1 boot disk 30GB (pd-standard)
- 1 règle firewall (port 8443 pour webhooks)
- Startup script avec toutes les dépendances

**Temps estimé**: 3-5 minutes

**Vérification**:
```bash
gcloud compute instances list

# Devrait afficher:
# NAME              ZONE            MACHINE_TYPE  INTERNAL_IP  EXTERNAL_IP     STATUS
# telegram-bot-vm   us-central1-a   e2-small      10.x.x.x     XX.XX.XX.XX     RUNNING
```

### Étape 3: Configurer SSH (optionnel mais recommandé)

Ajouter à `~/.ssh/config` sur votre machine locale:

```ssh
Host telegram-bot-vm
    HostName XX.XX.XX.XX  # Remplacer par l'IP externe de votre VM
    User YOUR_USERNAME
    IdentityFile ~/.ssh/google_compute_engine
    Port 22
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
    ServerAliveInterval 60
    ServerAliveCountMax 3
    TCPKeepAlive yes
    Compression yes
```

**Tester la connexion**:
```bash
ssh telegram-bot-vm
# ou
gcloud compute ssh telegram-bot-vm --zone=us-central1-a
```

### Étape 4: Attendre l'Installation des Dépendances

Le startup script s'exécute automatiquement au démarrage de la VM.

**Vérifier le statut** (depuis la VM):
```bash
# Se connecter
ssh telegram-bot-vm

# Vérifier l'installation
claude --version    # @anthropic-ai/claude-code
poetry --version    # Poetry 1.7+
node --version      # Node.js 20.x
python3.11 --version
```

Si les commandes échouent, attendre 1-2 minutes que le startup script se termine.

**Consulter les logs du startup script**:
```bash
sudo journalctl -u google-startup-scripts.service
```

### Étape 5: Exécuter le Setup Bot

Depuis la VM, télécharger et exécuter le script de setup:

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-telegram-gcp/main/scripts/setup-bot.sh | bash
```

**Le script va demander**:
1. **Telegram Bot Token**: Obtenu depuis [@BotFather](https://t.me/botfather)
2. **Bot Username**: Le nom de votre bot (sans @)
3. **Telegram User ID**: Votre ID depuis [@userinfobot](https://t.me/userinfobot)
4. **Project Git Repository URL**: URL de votre projet (ex: https://github.com/username/my-project.git)
5. **Project Directory Name**: Nom du dossier (ex: my-project)
6. **Git User Name**: Pour les commits
7. **Git User Email**: Pour les commits

**Ce qui sera créé**:
- `/home/$USER/telegram-bot/` - Dossier de travail
- `/home/$USER/telegram-bot/claude-code-telegram/` - Bot Python
- `/home/$USER/telegram-bot/YOUR_PROJECT/` - Votre projet
- `/home/$USER/telegram-bot/claude-code-telegram/.env` - Configuration
- `/home/$USER/telegram-bot/start-bot.sh` - Script de lancement
- `/home/$USER/telegram-bot/start-tmux.sh` - Script tmux

**Temps estimé**: 5-10 minutes

### Étape 6: Authentifier Claude CLI

```bash
claude auth login
```

**Processus**:
1. Une URL s'affiche dans le terminal
2. Copier l'URL et l'ouvrir dans un navigateur
3. Se connecter avec votre compte Anthropic
4. Revenir au terminal, l'authentification devrait être validée

**Note**: Si vous n'avez pas de navigateur sur la VM, utilisez port forwarding:

```bash
# Sur votre machine locale
ssh -L 8080:localhost:8080 telegram-bot-vm
```

Puis ouvrir `http://localhost:8080` dans votre navigateur local.

### Étape 7: Démarrer le Bot

```bash
~/telegram-bot/start-tmux.sh
```

**Output attendu**:
```
✅ Bot démarré dans tmux session: telegram-bot

📋 Commandes utiles:
  • Attacher à la session: tmux attach -t telegram-bot
  • Détacher: Ctrl+B puis D
  • Voir logs en temps réel: tmux attach -t telegram-bot
```

**Vérifier les logs**:
```bash
tmux attach -t telegram-bot
# Vous devriez voir:
# 🤖 Démarrage Telegram Bot...
# INFO: Bot started successfully
# INFO: Polling for new messages...
```

Pour détacher: **Ctrl+B** puis **D**

### Étape 8: Tester le Bot

1. Ouvrir Telegram
2. Chercher votre bot (@votre_bot_username)
3. Envoyer `/start`
4. Poser une question: "List all Python files in the project"

Le bot devrait répondre avec une liste des fichiers Python.

## 🛠️ Configuration Avancée

### Modifier les Outils Autorisés

Éditer `/home/$USER/telegram-bot/claude-code-telegram/.env`:

```bash
# Ajouter/retirer des outils
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]
```

**Outils disponibles**:
- **Read**: Lire des fichiers
- **Write**: Créer/écraser des fichiers
- **Edit**: Modifier des fichiers existants
- **Bash**: Exécuter des commandes shell
- **Glob**: Rechercher des fichiers par pattern
- **Grep**: Rechercher dans des fichiers
- **Task**: Lancer des sous-tâches
- **WebFetch**: Récupérer du contenu web
- **WebSearch**: Recherche web
- **TodoWrite**: Gérer une todo list
- **Skill**: Exécuter des skills personnalisés
- **SlashCommand**: Exécuter des commandes personnalisées
- **AskUserQuestion**: Poser des questions à l'utilisateur

Redémarrer le bot après modification:
```bash
~/telegram-bot/start-tmux.sh
```

### Ajuster les Limites de Coût

Dans `.env`:
```bash
# Coût maximum par utilisateur (USD)
CLAUDE_MAX_COST_PER_USER=10.0

# Timeout pour les commandes Claude (secondes)
CLAUDE_TIMEOUT_SECONDS=300
```

### Configurer le Rate Limiting

Dans `.env`:
```bash
# Max 10 requêtes par fenêtre de 60 secondes
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

### Mode Webhook (Alternative au Polling)

**Avantages**: Latence plus faible, moins de requêtes API

**Configuration**:

1. Obtenir un certificat SSL (requis par Telegram):
```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d your-domain.com
```

2. Modifier le code du bot pour utiliser webhooks (voir RichardAtCT/claude-code-telegram README)

3. Configurer le webhook via l'API Telegram:
```bash
curl "https://api.telegram.org/bot<YOUR_TOKEN>/setWebhook?url=https://your-domain.com:8443/telegram"
```

## 🔒 Sécurité

### Firewall Rules

La règle `telegram-webhook-allow` ouvre le port 8443 pour tous (`0.0.0.0/0`).

**Restreindre aux IP Telegram** (recommandé):
```bash
gcloud compute firewall-rules update telegram-webhook-allow \
  --source-ranges=149.154.160.0/20,91.108.4.0/22
```

### SSH Hardening

Désactiver l'authentification par mot de passe (utiliser uniquement SSH keys):
```bash
sudo nano /etc/ssh/sshd_config
# PasswordAuthentication no
sudo systemctl restart sshd
```

### Monitoring des Logs

Configurer des alertes pour détecter les tentatives d'intrusion:

```bash
# Installer fail2ban
sudo apt-get install fail2ban

# Créer une config pour SSH
sudo nano /etc/fail2ban/jail.local
```

Contenu:
```ini
[DEFAULT]
ban time = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
```

Redémarrer:
```bash
sudo systemctl restart fail2ban
```

## 💰 Optimisation des Coûts

### Arrêter la VM Quand Non Utilisée

```bash
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a
```

**Coûts arrêtés**:
- Compute: $0/mois (pas de facturation quand arrêté)
- Disk: $1.20/mois (30GB × $0.04/GB)

**Redémarrer**:
```bash
gcloud compute instances start telegram-bot-vm --zone=us-central1-a

# Relancer le bot
gcloud compute ssh telegram-bot-vm --zone=us-central1-a
~/telegram-bot/start-tmux.sh
```

### Snapshot pour Backup

Créer un snapshot avant modifications importantes:

```bash
gcloud compute disks snapshot telegram-bot-vm \
  --zone=us-central1-a \
  --snapshot-names=telegram-bot-backup-$(date +%Y%m%d)
```

**Coût**: $0.026/GB/mois pour les snapshots

### Scheduled Shutdown

Arrêter automatiquement la VM chaque nuit (23h UTC):

```bash
# Créer un script cron sur la VM
crontab -e
```

Ajouter:
```cron
0 23 * * * sudo shutdown -h now
```

**Redémarrer manuellement le matin**:
```bash
gcloud compute instances start telegram-bot-vm --zone=us-central1-a
```

## 🐛 Dépannage

### Bot Ne Répond Pas

**1. Vérifier que le bot tourne**:
```bash
ssh telegram-bot-vm
tmux attach -t telegram-bot
```

**2. Vérifier Claude CLI**:
```bash
claude --version
# Si erreur: réinstaller
sudo npm install -g @anthropic-ai/claude-code
```

**3. Vérifier authentication**:
```bash
claude auth login
```

### Erreurs Pydantic Validation

**Symptôme**: `validation error for Settings`

**Solution**: Format JSON array requis dans `.env`

**Mauvais**:
```bash
ALLOWED_USERS=1136600499
CLAUDE_ALLOWED_TOOLS=Read,Write
```

**Bon**:
```bash
ALLOWED_USERS=[1136600499]
CLAUDE_ALLOWED_TOOLS=["Read","Write"]
```

### VM Manque de Mémoire

**Symptôme**: Lenteur, freeze, OOM errors

**Vérifier l'utilisation**:
```bash
free -h
```

**Upgrade vers e2-medium**:
```bash
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a
gcloud compute instances set-machine-type telegram-bot-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium
gcloud compute instances start telegram-bot-vm --zone=us-central1-a
```

**Coût**: $24.46/mois (vs $12.23 pour e2-small)

### SSH Timeout

**Symptôme**: `Connection timed out`

**Solutions**:

1. Vérifier que la VM est démarrée:
```bash
gcloud compute instances list
```

2. Vérifier les règles firewall:
```bash
gcloud compute firewall-rules list | grep ssh
```

3. Augmenter le timeout SSH (dans `~/.ssh/config`):
```ssh
Host telegram-bot-vm
    ConnectTimeout 60
```

## 📊 Monitoring

### Logs VM

Consulter les logs Cloud Logging:
```bash
gcloud logging read "resource.type=gce_instance AND resource.labels.instance_id=YOUR_INSTANCE_ID" \
  --limit 50 \
  --format json
```

### Métriques CPU/RAM

Voir l'utilisation en temps réel:
```bash
gcloud compute instances get-serial-port-output telegram-bot-vm \
  --zone=us-central1-a
```

Ou via GCP Console: Compute Engine → VM instances → telegram-bot-vm → Monitoring

### Alertes

Créer une alerte si CPU > 80%:

1. Aller dans GCP Console → Monitoring → Alerting
2. Create Policy
3. Condition: VM Instance → CPU utilization > 80%
4. Notification Channel: Email

## 🎯 Prochaines Étapes

- [ ] Configurer des backups automatiques (snapshots quotidiens)
- [ ] Implémenter monitoring avancé (Grafana/Prometheus)
- [ ] Ajouter multi-user support
- [ ] Créer un dashboard web pour gérer le bot
- [ ] Automatiser déploiement avec Terraform

## 📚 Ressources

- [GCP Free Tier](https://cloud.google.com/free)
- [Compute Engine Pricing](https://cloud.google.com/compute/pricing)
- [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)
- [Claude Code Documentation](https://docs.claude.com/claude-code)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

**Problèmes ?** Ouvrir une [issue sur GitHub](https://github.com/YOUR_USERNAME/claude-telegram-gcp/issues)
