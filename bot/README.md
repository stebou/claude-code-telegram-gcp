# Claude Code Telegram Bot

Python Telegram bot that provides full access to Claude Code CLI with all tools enabled.

## Features

- ✅ Full Claude Code CLI integration
- ✅ All tools enabled (Read, Write, Edit, Bash, Git, WebSearch, etc.)
- ✅ Security validation (user whitelist, rate limiting)
- ✅ Cost tracking and budget limits
- ✅ Timeout protection
- ✅ Async/await architecture
- ✅ **Action confirmation buttons** - When Claude proposes an action, you get Proceed/Cancel buttons for safety

## Installation

### Prerequisites

- Python 3.11+
- Poetry (Python dependency manager)
- Claude Code CLI (`@anthropic-ai/claude-code`)

### Local Setup

1. **Install dependencies:**
```bash
cd bot
poetry install
```

2. **Configure environment:**
```bash
cp ../config/.env.example .env
# Edit .env with your values
```

3. **Run the bot:**
```bash
poetry run python -m src.main
```

## Configuration

All configuration is done via environment variables in `.env`:

```bash
# Telegram Bot Token from @BotFather
TELEGRAM_BOT_TOKEN=your_token_here

# Your Telegram username
TELEGRAM_BOT_USERNAME=your_bot_username

# Base directory (bot can only access files here)
APPROVED_DIRECTORY=/path/to/your/project

# Allowed user IDs (JSON array format required)
ALLOWED_USERS=[123456789]

# Claude settings
CLAUDE_MAX_COST_PER_USER=10.0
CLAUDE_TIMEOUT_SECONDS=300

# Tools Claude can use (JSON array format required)
CLAUDE_ALLOWED_TOOLS=["Read","Write","Edit","Bash","Glob","Grep","Task","WebFetch","WebSearch","TodoWrite","Skill","SlashCommand","AskUserQuestion"]

# Rate limiting (10 requests per 60 seconds)
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW=60
```

## Project Structure

```
bot/
├── src/
│   ├── config/
│   │   └── settings.py          # Configuration management
│   ├── claude/
│   │   └── executor.py          # Claude CLI subprocess executor
│   ├── security/
│   │   └── validator.py         # User auth & rate limiting
│   ├── handlers/
│   │   └── message_handler.py   # Telegram message handlers
│   └── main.py                  # Application entry point
├── pyproject.toml               # Poetry dependencies
└── README.md
```

## Usage

Send messages to your bot on Telegram:

```
You: "List all Python files in the project"
Bot: *uses Glob tool*
Bot: "Here are the Python files..."

You: "Add a new feature for user authentication"
Bot: *uses Read, Write, Edit tools*
Bot: *creates auth.py*
Bot: *updates main.py*
Bot: "Feature added! Ready to commit?"
     [✅ Proceed] [❌ Cancel]

You: *clicks Proceed*
Bot: "✅ Proceeding with action..."
Bot: *creates files and updates code*
Bot: "Files created successfully!"

You: "Now commit and push to GitHub"
Bot: "I can commit these changes. Proceed?"
     [✅ Proceed] [❌ Cancel]

You: *clicks Proceed*
Bot: *git add, commit, push*
Bot: "Pushed to GitHub successfully!"
```

### Action Confirmation Buttons

When Claude proposes to perform an action (create, modify, delete, commit, etc.), the bot automatically detects this and adds confirmation buttons:

- **✅ Proceed** - Execute the proposed action
- **❌ Cancel** - Cancel the action

This provides an extra safety layer, especially for destructive operations like file deletion or git pushes.

## Security

- **User Whitelist**: Only allowed Telegram user IDs can use the bot
- **Rate Limiting**: 10 requests per 60 seconds per user (configurable)
- **Budget Limits**: Maximum cost per user ($10/user by default)
- **Timeout Protection**: Commands timeout after 300 seconds
- **Directory Restriction**: Bot can only access files within `APPROVED_DIRECTORY`

## Development

### Run tests:
```bash
poetry run pytest
```

### Code formatting:
```bash
poetry run black src/
```

### Linting:
```bash
poetry run flake8 src/
```

## Troubleshooting

### Bot doesn't respond
1. Check if Claude CLI is authenticated: `claude auth login`
2. Check logs for errors
3. Verify your user ID is in ALLOWED_USERS

### Pydantic validation errors
Make sure JSON arrays are properly formatted:
```bash
# ❌ WRONG
ALLOWED_USERS=123456789

# ✅ CORRECT
ALLOWED_USERS=[123456789]
```

### Timeout errors
Increase timeout in `.env`:
```bash
CLAUDE_TIMEOUT_SECONDS=600  # 10 minutes
```

## License

MIT License - See LICENSE file for details

## Credits

Inspired by [RichardAtCT/claude-code-telegram](https://github.com/RichardAtCT/claude-code-telegram)
