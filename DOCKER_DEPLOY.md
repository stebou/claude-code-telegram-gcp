# 🐳 Docker One-Command Deployment

**Déployez votre bot Telegram avec Claude Code CLI en une seule commande sur n'importe quelle VM**

---

## ✨ Ce Que Ça Fait

- 🚀 **Déploiement en une commande** - Aucune configuration manuelle
- 🔐 **Authentification Claude intégrée** - Setup guidé pendant le déploiement
- 📦 **Isolation complète** - Container Docker avec toutes les dépendances
- 🔄 **Auto-restart** - Redémarre automatiquement en cas de crash
- 💾 **Persistance des données** - Volumes Docker pour Claude auth + données bot
- 🛡️ **Sécurité** - Secrets management + user non-root

---

## 📋 Prérequis

### Sur votre VM (n'importe quel provider):

```bash
# 1. Docker installé
docker --version
# Docker version 24.0+ requis

# 2. Docker Compose installé
docker compose version
# Docker Compose version 2.0+ requis

# 3. Git installé (pour cloner le repo)
git --version
```

### Avant de déployer:

1. **Bot Telegram créé** → Talk to [@BotFather](https://t.me/botfather)
   - `/newbot` pour créer un bot
   - Récupérer le **token** (ex: `123456:ABC-DEF...`)
   - Récupérer le **username** (ex: `my_bot`)

2. **Votre Telegram User ID** → Talk to [@userinfobot](https://t.me/userinfobot)
   - Envoyer `/start`
   - Récupérer votre **ID** (ex: `1136600499`)

3. **Compte Claude** → [console.anthropic.com](https://console.anthropic.com/)
   - Compte gratuit ou payant
   - Aucune clé API nécessaire (OAuth durant le setup)

---

## 🚀 Installation en 3 Étapes

### Étape 1: Cloner le Repo

```bash
# SSH dans votre VM
ssh user@your-vm-ip

# Cloner le repository
git clone https://github.com/stebou/claude-code-telegram-gcp.git
cd claude-code-telegram-gcp

# Rendre le script exécutable
chmod +x deploy.sh
```

### Étape 2: Lancer le Déploiement

```bash
./deploy.sh \
  --token YOUR_TELEGRAM_BOT_TOKEN \
  --username your_bot_username \
  --user-id YOUR_TELEGRAM_USER_ID
```

**Exemple concret**:

```bash
./deploy.sh \
  --token 123456789:ABCdefGHIjklMNOpqrsTUVwxyz12345678 \
  --username studia_assistant_bot \
  --user-id 1136600499
```

**Optionnel** - Spécifier le répertoire de travail:

```bash
./deploy.sh \
  --token YOUR_TOKEN \
  --username YOUR_BOT \
  --user-id YOUR_ID \
  --work-dir /path/to/work/directory  # Par défaut: ~/telegram-bot/work
```

### Étape 3: Authentifier Claude CLI

**Pendant le déploiement**, le script va:

1. ✅ Valider les prérequis (Docker, Compose)
2. ✅ Créer les secrets de manière sécurisée
3. ✅ Construire l'image Docker (multi-stage build)
4. ✅ Lancer un container interactif pour l'authentification Claude

**Vous verrez**:

```
🔑 Initializing Claude CLI authentication...

You need to authenticate Claude CLI manually

In a moment, a Docker container will start and prompt you to:
  1. Visit an Anthropic authentication URL
  2. Login with your Claude account
  3. Authorize the CLI

Press ENTER to continue with Claude authentication...
```

**Appuyez sur ENTER**, puis:

```bash
# À l'intérieur du container, Claude CLI va démarrer
🔐 Starting Claude CLI authentication...

Please visit this URL to authenticate:
https://claude.com/auth/xxxxx-xxxxx-xxxxx

✅ Authentication successful!
```

1. **Copiez l'URL** dans votre navigateur
2. **Connectez-vous** à votre compte Claude
3. **Autorisez** l'application CLI
4. **Retournez au terminal** - Le script continue automatiquement

**Ensuite**:

5. ✅ Docker Compose démarre les services
6. ✅ Health checks vérifient que tout fonctionne
7. ✅ Bot prêt et opérationnel!

---

## 📊 Ce Qui Se Passe Pendant le Déploiement

```
🔍 Pre-flight checks...
   ✅ Docker installed
   ✅ Docker Compose installed
   ✅ Files present

🔐 Creating secrets...
   ✅ Token stored securely
   ✅ Username stored
   ✅ User ID stored

📁 Creating working directory...
   ✅ ~/telegram-bot/work created

🔨 Building Docker image...
   ✅ Stage 1: Builder (Poetry dependencies)
   ✅ Stage 2: Claude CLI installer
   ✅ Stage 3: Runtime (slim production image)

🏥 Running health check...
   ✅ Python dependencies OK
   ✅ Claude CLI available

🛑 Stopping existing containers...
   ✅ Clean shutdown

🧹 Cleaning up old images...
   ✅ Disk space freed

🔑 Initializing Claude CLI authentication...
   [Interactive authentication flow]
   ✅ Claude credentials stored

🚀 Starting services...
   ✅ Container started

⏳ Waiting for health check...
   ✅ Service is healthy!

✅ Deployment complete!
```

---

## 🧪 Tester Votre Bot

### 1. Vérifier le statut

```bash
# Voir les containers en cours
docker compose ps

# Exemple de sortie:
NAME            IMAGE              STATUS              PORTS
telegram-bot    telegram-bot:latest  Up 2 minutes (healthy)
```

### 2. Voir les logs

```bash
# Suivre les logs en temps réel
docker compose logs -f

# Voir les 50 dernières lignes
docker compose logs --tail=50
```

### 3. Tester avec Telegram

1. **Ouvrir Telegram**
2. **Chercher votre bot**: `@your_bot_username`
3. **Envoyer** `/start`
4. **Tester une commande**:

```
Vous: List all files in the working directory
Bot: [Exécute la commande via Claude Code CLI et retourne les résultats]
```

**Exemples de commandes**:

```
"What files are in this directory?"
"Create a file hello.txt with 'Hello World'"
"Show me the content of hello.txt"
"Write a Python script to calculate fibonacci numbers"
"Run the Python script and show me the output"
```

---

## 🔧 Gestion du Bot

### Commandes Utiles

```bash
# Suivre les logs
docker compose logs -f

# Redémarrer le bot
docker compose restart

# Arrêter le bot
docker compose down

# Entrer dans le container
docker compose exec telegram-bot bash

# Exécuter Claude CLI directement
docker compose exec telegram-bot claude --help

# Voir l'utilisation des ressources
docker stats telegram-bot

# Inspecter la configuration
docker inspect telegram-bot
```

### Mise à Jour du Bot

```bash
# Arrêter le bot
docker compose down

# Pull derniers changements
git pull origin main

# Redéployer
./deploy.sh \
  --token YOUR_TOKEN \
  --username YOUR_BOT \
  --user-id YOUR_ID
```

### Backup des Données

```bash
# Backup de l'authentification Claude
docker run --rm \
  -v telegram-bot_claude-auth:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/claude-auth-$(date +%Y%m%d).tar.gz -C /source .

# Backup des données du bot
docker run --rm \
  -v telegram-bot_bot-data:/source:ro \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/bot-data-$(date +%Y%m%d).tar.gz -C /source .
```

### Restaurer des Backups

```bash
# Restaurer l'authentification Claude
docker run --rm \
  -v telegram-bot_claude-auth:/target \
  -v $(pwd)/backups:/backup \
  alpine sh -c "cd /target && tar xzf /backup/claude-auth-YYYYMMDD.tar.gz"
```

---

## 🛡️ Sécurité

### ✅ Mesures de Sécurité Implémentées

1. **Docker Secrets** - Tokens jamais en variables d'environnement
2. **Non-root User** - Container tourne avec user `appuser`
3. **Volume Isolation** - Données persistées dans volumes Docker
4. **Resource Limits** - 1.5G RAM max, CPU throttling
5. **Health Checks** - Détection automatique des problèmes
6. **Secrets Directory** - Permissions 600 (lecture propriétaire uniquement)

### 🔐 Fichiers Secrets

Les secrets sont stockés dans `./secrets/` (jamais commités):

```
secrets/
├── telegram_bot_token.txt     # Token Telegram
├── telegram_bot_username.txt  # Username du bot
└── allowed_users.txt           # [123456] format JSON array
```

**Permissions automatiques**: `chmod 600 secrets/*.txt`

---

## 📦 Architecture Docker

### Image Multi-Stage

```
Stage 1: Builder (python:3.11-bookworm)
   └─ Install Poetry + dependencies
   └─ Create .venv with production packages

Stage 2: Claude Installer (node:20-bookworm-slim)
   └─ Install Claude CLI (@anthropic-ai/claude)

Stage 3: Runtime (python:3.11-slim-bookworm)
   └─ Copy .venv from Builder
   └─ Copy Claude CLI from Claude Installer
   └─ Copy application code
   └─ Run as non-root user
```

**Taille finale**: ~600MB (vs ~1.5GB sans multi-stage)

### Volumes Docker

```
telegram-bot_claude-auth:/home/appuser/.claude
   └─ OAuth tokens, session data

telegram-bot_bot-data:/app/data
   └─ Bot logs, cache, temporary files

telegram-bot_approved-directory:/approved-directory
   └─ Working directory pour les commandes Claude
```

### Health Checks

**Check toutes les 30s**:

```python
python -c "
import requests
requests.get('https://api.telegram.org', timeout=5).raise_for_status()
"
```

**Redémarre automatiquement** si unhealthy après 3 checks consécutifs

---

## 🐛 Dépannage

### Bot ne démarre pas

```bash
# Voir les logs détaillés
docker compose logs --tail=100

# Vérifier les secrets
ls -la secrets/
# Doit afficher: -rw------- (600 permissions)

# Vérifier le contenu des secrets
cat secrets/telegram_bot_token.txt
# Doit contenir votre token sans espaces
```

### Authentification Claude échoue

```bash
# Relancer uniquement l'authentification
docker run -it --rm \
  -v telegram-bot_claude-auth:/home/appuser/.claude \
  telegram-bot:latest \
  claude auth login

# Vérifier le statut
docker run --rm \
  -v telegram-bot_claude-auth:/home/appuser/.claude \
  telegram-bot:latest \
  claude auth status
```

### Health check timeout

```bash
# Augmenter le délai de démarrage
# Éditer docker-compose.yml:
healthcheck:
  start_period: 120s  # Au lieu de 60s
```

### Out of memory

```bash
# Vérifier l'utilisation
docker stats telegram-bot

# Augmenter la limite dans docker-compose.yml:
deploy:
  resources:
    limits:
      memory: 2G  # Au lieu de 1.5G
```

### Docker build échoue

```bash
# Nettoyer le cache Docker
docker system prune -a

# Rebuild depuis zéro
docker compose build --no-cache
```

---

## ⚡ Performance & Coûts

### VM Recommandée

| Provider | Type | Specs | Coût/mois | Performance |
|----------|------|-------|-----------|-------------|
| **GCP** | e2-small | 2 vCPU, 2GB RAM | ~$12 | ⭐⭐⭐ |
| **AWS** | t3.small | 2 vCPU, 2GB RAM | ~$15 | ⭐⭐⭐ |
| **Azure** | B1s | 1 vCPU, 1GB RAM | ~$8 | ⭐⭐ (swap requis) |
| **DigitalOcean** | Basic Droplet | 1 vCPU, 2GB RAM | ~$12 | ⭐⭐⭐ |
| **Hetzner** | CX11 | 1 vCPU, 2GB RAM | ~€4 | ⭐⭐⭐ Meilleur rapport qualité/prix |

### Utilisation Ressources

```
Mémoire: ~200-400 MB (base) + pic lors des commandes Claude
CPU: <5% idle, 20-40% durant exécution
Disk: ~1.5GB (image) + ~500MB (volumes)
Network: Minimal (quelques MB/jour)
```

### Coût Total Estimé

```
VM (e2-small GCP): $12/mois
Claude API: Variable selon usage
  - Gratuit: Usage limité
  - Pro ($20/mois): Usage illimité
Total: $12-32/mois
```

---

## 📚 Structure du Projet

```
claude-code-telegram-gcp/
├── bot/                        # Code Python du bot
│   ├── src/
│   │   ├── main.py            # Entry point
│   │   ├── handlers/          # Message handlers
│   │   ├── claude/            # Claude CLI executor
│   │   ├── security/          # Security validators
│   │   └── config/            # Pydantic settings
│   ├── pyproject.toml         # Poetry dependencies
│   └── poetry.lock
│
├── Dockerfile                  # Multi-stage Docker build
├── docker-compose.yml          # Service orchestration
├── deploy.sh                   # 🚀 ONE-COMMAND DEPLOYMENT
├── .dockerignore              # Files excluded from image
├── .gitignore                 # Git exclusions
│
├── secrets/                   # ⚠️ NEVER COMMIT (auto-created)
│   ├── telegram_bot_token.txt
│   ├── telegram_bot_username.txt
│   └── allowed_users.txt
│
└── DOCKER_DEPLOY.md           # 📖 This file
```

---

## 🎯 Cas d'Usage

### 1. Bot d'Assistance Coding Personnel

```
Vous: "Create a REST API with Flask for user management"
Bot: [Claude génère le code, crée les fichiers, lance les tests]
```

### 2. Automatisation DevOps

```
Vous: "Check the status of all Docker containers"
Bot: [Exécute docker ps, analyse l'output, propose des actions]
```

### 3. Analyse de Logs

```
Vous: "Find all ERROR lines in /var/log/app.log from the last hour"
Bot: [Parse les logs, extrait les erreurs, résume les problèmes]
```

### 4. Code Review Automatisé

```
Vous: "Review the changes in commit abc123"
Bot: [Analyse le diff, identifie les bugs potentiels, suggère des améliorations]
```

---

## 🔄 Comparaison: Docker vs Installation Manuelle

| Aspect | Docker (Ce Guide) | Installation Manuelle |
|--------|-------------------|----------------------|
| **Setup Time** | ~10 minutes | ~30-60 minutes |
| **Complexité** | Une commande | 10+ commandes manuelles |
| **Portabilité** | N'importe quelle VM | Dépend de l'OS |
| **Isolation** | ✅ Complète | ❌ Partage système |
| **Updates** | `git pull && ./deploy.sh` | Multiples étapes |
| **Rollback** | `docker tag` + redeploy | Complexe |
| **Backup** | Volumes Docker | Fichiers manuels |
| **Resource Usage** | +50MB overhead | Natif |

**Verdict**: Docker recommandé pour 99% des cas

---

## 💡 Tips & Best Practices

### ✅ Do

- **Sauvegarder régulièrement** les volumes Claude auth
- **Monitorer** l'utilisation des ressources avec `docker stats`
- **Garder à jour** l'image Docker (`git pull` régulièrement)
- **Tester** le bot après chaque update majeur
- **Limiter** les users autorisés (ALLOWED_USERS)

### ❌ Don't

- **Ne JAMAIS commit** `secrets/` dans Git
- **Ne pas** run en tant que root sur la VM
- **Ne pas** exposer** ports Docker publiquement
- **Ne pas** partager votre token Telegram
- **Ne pas** mettre de données sensibles dans le working directory

---

## 🚀 Prochaines Étapes

Une fois votre bot déployé:

1. **Configurer systemd** pour auto-start de Docker au boot VM
2. **Setup monitoring** (Prometheus + Grafana)
3. **Ajouter plus d'users** en éditant `ALLOWED_USERS`
4. **Customiser** les prompts Claude dans le code
5. **Intégrer** avec CI/CD pour auto-deploy

---

## 📞 Support

- **GitHub Issues**: [github.com/stebou/claude-code-telegram-gcp/issues](https://github.com/stebou/claude-code-telegram-gcp/issues)
- **Original Repo**: [github.com/RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)
- **Claude Docs**: [docs.anthropic.com](https://docs.anthropic.com/)
- **Docker Docs**: [docs.docker.com](https://docs.docker.com/)

---

## 📄 Licence

MIT License - Voir LICENSE file

---

**⚡ Déployé en < 10 min | 🐳 Fonctionne partout | 🔐 Sécurisé par design**
