# 🤖 Claude Code Telegram Bot on GCP VM

A production-ready solution to run Claude Code CLI as a persistent Telegram bot on Google Cloud Platform. This implementation provides a reliable, cost-effective alternative to serverless architectures with permanent availability.

## 🎯 Why This Solution?

This architecture solves common pain points with AI assistants on Telegram:

- ✅ **Permanent availability** - VM runs 24/7 (no cold starts)
- ✅ **Low cost** - $12.23/month with GCP e2-small
- ✅ **Direct Claude integration** - No third-party AI services required
- ✅ **Git workflow** - Automatic commits and push to your repository
- ✅ **Session persistence** - Uses tmux to survive SSH disconnects
- ✅ **VSCode remote access** - Full IDE support for VM files
- ✅ **Secure** - Sandboxed execution, rate limiting, input validation

## 🏗️ Architecture

```
┌─────────────┐
│   Telegram  │
│    Users    │
└──────┬──────┘
       │ Polling (or HTTPS webhook)
       ↓
┌─────────────────────────────────┐
│  GCP e2-small VM (2GB RAM)      │
│  ┌───────────────────────────┐  │
│  │  Python Telegram Bot      │  │
│  │  (RichardAtCT repo)       │  │
│  └───────┬───────────────────┘  │
│          │ subprocess           │
│  ┌───────▼───────────────────┐  │
│  │  Claude Code CLI          │  │
│  │  (@anthropic-ai/claude)   │  │
│  └───────┬───────────────────┘  │
│          │ tools (Read, Write,  │
│          │ Edit, Bash, Git)     │
│  ┌───────▼───────────────────┐  │
│  │  Your Git Repository      │  │
│  │  (e.g., studia2)          │  │
│  └───────┬───────────────────┘  │
└──────────┼───────────────────────┘
           │ git push
           ↓
    ┌─────────────┐
    │   GitHub    │
    └─────────────┘
```

## 📋 Prerequisites

- **GCP Account** with billing enabled ([free tier available](https://cloud.google.com/free))
- **Telegram Bot Token** (create via [@BotFather](https://t.me/botfather))
- **Claude Account** with API access ([Anthropic Console](https://console.anthropic.com/))
- **Git Repository** (GitHub, GitLab, etc.) for the bot to work with
- **Your Telegram User ID** (get from [@userinfobot](https://t.me/userinfobot))

## 🚀 Quick Start

### 1. Create GCP VM

```bash
# Clone this repository
git clone https://github.com/YOUR_USERNAME/claude-telegram-gcp.git
cd claude-telegram-gcp

# Run VM creation script
bash scripts/create-vm.sh
```

This will create:
- **VM**: e2-small (2 vCPU, 2GB RAM, 30GB disk) in us-central1-a
- **Firewall rule**: Port 8443 for Telegram webhooks (optional)
- **Startup script**: Installs Python 3.11, Poetry, Node.js, Git, tmux, Claude CLI

**Estimated time**: 3-5 minutes

### 2. Setup Bot on VM

SSH into your VM:

```bash
gcloud compute ssh telegram-bot-vm --zone=us-central1-a
```

Run the setup script:

```bash
curl -sSL https://raw.githubusercontent.com/YOUR_USERNAME/claude-telegram-gcp/main/scripts/setup-bot.sh | bash
```

This will:
- Clone RichardAtCT/claude-code-telegram repository
- Install Python dependencies with Poetry
- Clone your target repository (e.g., studia2)
- Create `.env` configuration file
- Create startup scripts

**Estimated time**: 5-10 minutes

### 3. Configure Environment Variables

Edit the `.env` file to add your credentials:

```bash
cd ~/telegram-bot/claude-code-telegram
nano .env
```

**Required changes**:
- `TELEGRAM_BOT_TOKEN` - Your bot token from @BotFather
- `ALLOWED_USERS` - Your Telegram user ID (from @userinfobot)
- `APPROVED_DIRECTORY` - Path to your git repository

See [Configuration Guide](#-configuration) for detailed explanations.

### 4. Authenticate Claude CLI

```bash
claude auth login
```

This will:
1. Display a URL to open in your browser
2. Ask you to sign in with your Anthropic account
3. Save authentication token locally

**Note**: You need a browser for this step (run on your local machine, or use port forwarding).

### 5. Start the Bot

Launch in tmux session (persistent):

```bash
~/telegram-bot/start-tmux.sh
```

Verify logs:

```bash
tmux attach -t telegram-bot
# Press Ctrl+B then D to detach
```

### 6. Test Your Bot

1. Open Telegram
2. Search for your bot (username from .env)
3. Send `/start`
4. Try a question: "List all Python files in the project"

The bot should respond with Claude-generated answers!

## ⚙️ Configuration

### Environment Variables (.env)

Located at `~/telegram-bot/claude-code-telegram/.env` on VM.

**Telegram Settings**:
```bash
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_BOT_USERNAME=your_bot_username
```

**Security**:
```bash
# Restrict bot to your user ID only
ALLOWED_USERS=[1136600499]

# Sandbox directory (bot can only access files here)
APPROVED_DIRECTORY=/home/YOUR_USERNAME/telegram-bot/YOUR_REPO
```

**Claude Settings**:
```bash
# Use CLI subprocess (not SDK)
USE_SDK=false

# Cost limits per user
CLAUDE_MAX_COST_PER_USER=10.0

# Timeout for Claude commands
CLAUDE_TIMEOUT_SECONDS=300

# Tools Claude can use
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]
```

**Rate Limiting**:
```bash
# Max requests per window
RATE_LIMIT_REQUESTS=10

# Window in seconds
RATE_LIMIT_WINDOW=60
```

**Features**:
```bash
# Allow file uploads via Telegram
ENABLE_FILE_UPLOADS=true

# Logging
DEBUG=false
LOG_LEVEL=INFO
```

### SSH Configuration (Local Machine)

Add to `~/.ssh/config` for easy access:

```ssh
Host telegram-bot-vm
    HostName YOUR_VM_IP
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

Now you can connect with just:

```bash
ssh telegram-bot-vm
```

### VSCode Remote Access

1. Install **Remote - SSH** extension in VSCode
2. Press `F1` → "Remote-SSH: Connect to Host"
3. Select `telegram-bot-vm`
4. Open folder: `/home/YOUR_USERNAME/telegram-bot`

You can now edit files directly on the VM with full IDE support!

## 🛠️ Management Commands

### View Logs

```bash
# Attach to tmux session
tmux attach -t telegram-bot

# Or view last 50 lines without attaching
gcloud compute ssh telegram-bot-vm --zone=us-central1-a \
  --command="tmux capture-pane -t telegram-bot -p | tail -50"
```

### Restart Bot

```bash
ssh telegram-bot-vm
~/telegram-bot/start-tmux.sh
```

This will:
1. Kill existing tmux session
2. Create new session
3. Launch bot with latest code

### Update Bot Code

```bash
ssh telegram-bot-vm
cd ~/telegram-bot/claude-code-telegram
git pull
poetry install  # Install new dependencies if any
~/telegram-bot/start-tmux.sh  # Restart
```

### Update Your Repository

```bash
ssh telegram-bot-vm
cd ~/telegram-bot/YOUR_REPO
git pull
```

### Stop VM (to save costs)

```bash
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a
```

**Note**: You'll be charged only for disk storage (~$1/month) when stopped.

### Start VM

```bash
gcloud compute instances start telegram-bot-vm --zone=us-central1-a

# Re-launch bot
gcloud compute ssh telegram-bot-vm --zone=us-central1-a \
  --command="~/telegram-bot/start-tmux.sh"
```

## 💰 Cost Breakdown

**GCP VM e2-small** (recommended):
- **Compute**: $12.23/month (730 hours × $0.0168/hour)
- **Disk**: 30GB × $0.04/GB = $1.20/month
- **Total**: **~$13.43/month**

**Alternatives**:

| Instance Type | RAM | vCPU | Monthly Cost | Status |
|---------------|-----|------|--------------|--------|
| e2-micro | 1GB | 0.25-2 | **FREE** | ⚠️ Too small (OOM errors) |
| e2-small | 2GB | 0.5-2 | $12.23 | ✅ Recommended |
| e2-medium | 4GB | 0.5-2 | $24.46 | 💰 Overkill for this use case |

**Claude API Costs** (separate):
- Depends on usage
- Set `CLAUDE_MAX_COST_PER_USER` to control

**Total estimated cost**: **$15-20/month** (VM + moderate Claude usage)

## 🔒 Security Features

### Sandboxing

Bot can only access files within `APPROVED_DIRECTORY`:

```python
# In monitor.py
def validate_path(file_path, working_directory):
    resolved = Path(file_path).resolve()
    if not resolved.is_relative_to(working_directory):
        return False, "Access denied: outside approved directory"
```

### Command Filtering

Dangerous shell commands are blocked:

```python
dangerous_patterns = [
    "rm -rf /",      # Recursive delete of root
    "sudo ",         # Privilege escalation
    "chmod 777",     # Overly permissive permissions
    "mkfs",          # Filesystem formatting
    "dd if=",        # Disk writing
    ":/bin/sh",      # Reverse shells
    "bash -i",       # Interactive bash spawning
]
```

Safe operations allowed: pipes (`|`), redirections (`>`), sequences (`&&`), etc.

### User Whitelisting

Only Telegram user IDs in `ALLOWED_USERS` can interact:

```python
@SecurityMiddleware.require_auth
def handle_message(update, context):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        return "Unauthorized"
```

### Rate Limiting

Prevent abuse with configurable limits:

```bash
RATE_LIMIT_REQUESTS=10  # Max 10 requests
RATE_LIMIT_WINDOW=60    # Per 60 seconds
```

## 🐛 Troubleshooting

### Bot doesn't respond

**Check if bot is running**:
```bash
ssh telegram-bot-vm
tmux attach -t telegram-bot
```

Look for errors in logs.

**Common issues**:
- Claude CLI not authenticated → Run `claude auth login`
- .env configuration errors → Check Pydantic validation messages
- Git authentication failed → Configure SSH keys or Personal Access Token

### "Tool Validation Failed" errors

Your command contains a dangerous pattern. Check logs for details:

```bash
tmux attach -t telegram-bot
```

**Solution**: Modify `monitor.py` if you need to allow specific patterns (use caution!).

### VSCode connection timeout

**Increase timeout** in VSCode settings:
- File → Preferences → Settings
- Search "remote.SSH.connectTimeout"
- Set to 60 (seconds)

**Verify SSH config** has KeepAlive:
```ssh
ServerAliveInterval 60
ServerAliveCountMax 3
TCPKeepAlive yes
```

### VM running out of memory

**Check memory usage**:
```bash
ssh telegram-bot-vm
free -h
```

If "available" is < 200MB, upgrade to e2-medium:

```bash
gcloud compute instances stop telegram-bot-vm --zone=us-central1-a
gcloud compute instances set-machine-type telegram-bot-vm \
  --zone=us-central1-a \
  --machine-type=e2-medium
gcloud compute instances start telegram-bot-vm --zone=us-central1-a
```

### Pydantic validation errors

Your `.env` format is incorrect. Pydantic expects JSON arrays:

**Wrong**:
```bash
ALLOWED_USERS=1136600499
CLAUDE_ALLOWED_TOOLS=Read,Write,Edit
```

**Correct**:
```bash
ALLOWED_USERS=[1136600499]
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit"]
```

## 📚 Advanced Usage

### Git Workflow

The bot can commit and push changes:

```
User: "Add a README.md file explaining the project"
Bot: *creates README.md using Write tool*
Bot: *commits with message: "docs: Add project README"*
Bot: *pushes to GitHub*
```

**Prerequisites**:
- Git configured on VM: `git config --global user.name "Bot Name"`
- SSH keys or PAT for authentication

### Custom Tools

Add more tools to `CLAUDE_ALLOWED_TOOLS`:

```bash
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]
```

See [Claude Code documentation](https://docs.claude.com/claude-code) for available tools.

### Webhook Mode (Optional)

By default, the bot uses **polling** (pulls for new messages). For lower latency, configure webhooks:

1. **Generate SSL certificate** (required for Telegram webhooks):
```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d your-domain.com
```

2. **Configure webhook URL** in bot code:
```python
updater.start_webhook(
    listen="0.0.0.0",
    port=8443,
    url_path="telegram",
    webhook_url=f"https://your-domain.com:8443/telegram"
)
```

3. **Set webhook via Telegram API**:
```bash
curl "https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://your-domain.com:8443/telegram"
```

**Note**: Polling is simpler and works fine for most use cases.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork this repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m "feat: Add my feature"`
4. Push to branch: `git push origin feature/my-feature`
5. Open a Pull Request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram) - Python Telegram bot implementation
- [Anthropic Claude](https://claude.ai) - AI assistant
- [Google Cloud Platform](https://cloud.google.com) - Infrastructure

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/claude-telegram-gcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/claude-telegram-gcp/discussions)
- **Telegram**: [@YOUR_SUPPORT_GROUP](https://t.me/YOUR_SUPPORT_GROUP)

## 🗺️ Roadmap

- [ ] Docker container support
- [ ] Multi-user support with per-user quotas
- [ ] Web dashboard for monitoring
- [ ] Automatic backups to GCS
- [ ] Kubernetes deployment option
- [ ] CI/CD integration examples

---

**Built with ❤️ by the community**
