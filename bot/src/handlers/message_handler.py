"""Telegram message handlers."""
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.claude.executor import ClaudeExecutor
from src.security.validator import security_validator

logger = logging.getLogger(__name__)

# Global executor
claude_executor = ClaudeExecutor()

# Store pending actions for confirmation
pending_actions = {}


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


def detect_action_in_response(response: str) -> bool:
    """Detect if Claude is proposing an action that needs confirmation."""
    action_keywords = [
        r"shall i",
        r"should i",
        r"would you like me to",
        r"do you want me to",
        r"can i",
        r"i can create",
        r"i can modify",
        r"i can delete",
        r"i can update",
        r"i'll create",
        r"i'll modify",
        r"i'll delete",
        r"i'll update",
        r"ready to commit",
        r"ready to push",
    ]

    response_lower = response.lower()
    return any(re.search(pattern, response_lower) for pattern in action_keywords)


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

        # Check if response contains an action that needs confirmation
        needs_confirmation = detect_action_in_response(response)

        # Send response (split if too long)
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            await thinking_msg.delete()
            for i, chunk in enumerate(chunks):
                # Add confirmation buttons only to the last chunk if needed
                if needs_confirmation and i == len(chunks) - 1:
                    keyboard = [
                        [
                            InlineKeyboardButton("✅ Proceed", callback_data=f"proceed:{user_id}:{len(pending_actions)}"),
                            InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{user_id}:{len(pending_actions)}")
                        ]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)

                    # Store the pending action
                    action_id = len(pending_actions)
                    pending_actions[f"{user_id}:{action_id}"] = {
                        "message": message_text,
                        "response": response
                    }

                    await update.message.reply_text(chunk, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(chunk)
        else:
            if needs_confirmation:
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Proceed", callback_data=f"proceed:{user_id}:{len(pending_actions)}"),
                        InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{user_id}:{len(pending_actions)}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Store the pending action
                action_id = len(pending_actions)
                pending_actions[f"{user_id}:{action_id}"] = {
                    "message": message_text,
                    "response": response
                }

                await thinking_msg.edit_text(response, reply_markup=reply_markup)
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


async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks (proceed/cancel actions)."""
    query = update.callback_query
    await query.answer()

    # Parse callback data: "proceed:123456:0" or "cancel:123456:0"
    data_parts = query.data.split(":")
    action_type = data_parts[0]  # "proceed" or "cancel"
    user_id = int(data_parts[1])
    action_id = data_parts[2]

    # Verify user authorization
    if user_id != update.effective_user.id:
        await query.edit_message_text(
            text="⛔ You are not authorized to confirm this action."
        )
        return

    # Get the pending action
    action_key = f"{user_id}:{action_id}"
    if action_key not in pending_actions:
        await query.edit_message_text(
            text="❌ This action has expired or was already processed."
        )
        return

    pending_action = pending_actions.pop(action_key)

    if action_type == "cancel":
        # User cancelled the action
        await query.edit_message_text(
            text=f"{pending_action['response']}\n\n❌ **Action cancelled by user.**"
        )
        logger.info(f"User {user_id} cancelled action: {pending_action['message'][:50]}")
        return

    # User confirmed - proceed with action
    try:
        await query.edit_message_text(
            text=f"{pending_action['response']}\n\n✅ **Proceeding with action...**"
        )

        # Send confirmation message to Claude to execute the action
        confirmation_message = "yes, proceed"

        # Check security again
        if not security_validator.check_rate_limit(user_id):
            await query.message.reply_text("⏱️ Rate limit exceeded. Please wait.")
            return

        if not await claude_executor.is_within_budget(user_id):
            await query.message.reply_text("💰 Budget limit exceeded.")
            return

        # Execute the confirmed action
        thinking_msg = await query.message.reply_text("🔄 Executing action...")
        response = await claude_executor.execute(confirmation_message, user_id)

        # Send final response
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            await thinking_msg.delete()
            for chunk in chunks:
                await query.message.reply_text(chunk)
        else:
            await thinking_msg.edit_text(response)

        logger.info(f"User {user_id} confirmed and executed action: {pending_action['message'][:50]}")

    except TimeoutError:
        await query.message.reply_text(
            "⏱️ Action execution timed out. Please try again."
        )
    except Exception as e:
        logger.error(f"Error executing confirmed action: {e}")
        await query.message.reply_text(
            f"❌ Error executing action: {str(e)[:200]}"
        )
