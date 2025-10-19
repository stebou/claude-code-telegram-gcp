"""Telegram message handlers."""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.claude.executor import ClaudeExecutor
from src.security.validator import security_validator

logger = logging.getLogger(__name__)

# Global executor
claude_executor = ClaudeExecutor()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id

    if not security_validator.is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return

    welcome_msg = (
        "🤖 **Claude Code Bot**\n\n"
        "I have access to the full Claude Code CLI.\n\n"
        "**Available tools:**\n"
        "📖 Read, ✍️ Write, ✏️ Edit\n"
        "🔧 Bash, 🔍 Glob, 🔎 Grep\n"
        "🌐 WebSearch, 📋 TodoWrite\n"
        "🎯 Task, ⚡ Skill, 🔨 SlashCommand\n\n"
        "Just send me a message!"
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages."""
    user_id = update.effective_user.id
    message_text = update.message.text

    # Security checks
    if not security_validator.is_authorized(user_id):
        await update.message.reply_text("⛔ Unauthorized access.")
        return

    if not security_validator.check_rate_limit(user_id):
        await update.message.reply_text("⏱️ Rate limit exceeded. Please wait.")
        return

    # Check budget
    if not await claude_executor.is_within_budget(user_id):
        await update.message.reply_text("💰 Budget limit exceeded.")
        return

    try:
        # Send "thinking" message
        thinking_msg = await update.message.reply_text("🤔 Processing...")

        # Execute Claude CLI
        response = await claude_executor.execute(message_text, user_id)

        # Send response (split if too long)
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            await thinking_msg.delete()
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await thinking_msg.edit_text(response)

    except TimeoutError:
        await update.message.reply_text(
            "⏱️ Request timed out. Please try a simpler request."
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)[:200]}"
        )
