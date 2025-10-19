"""Telegram message handlers."""
import asyncio
import io
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.claude.sdk_executor import ClaudeSDKExecutor, StreamUpdate
from src.security.validator import security_validator
from src.utils.diff_image import generate_diff_image

logger = logging.getLogger(__name__)

# Global executor (using SDK)
claude_executor = ClaudeSDKExecutor()

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
        # Question patterns
        r"shall i",
        r"should i",
        r"would you like me to",
        r"do you want me to",
        r"may i",
        r"can i",

        # Action patterns
        r"i can (create|modify|delete|update|write|edit|run)",
        r"i'll (create|modify|delete|update|write|edit|run)",
        r"i'm (going to|about to) (create|modify|delete|update|write|edit|run)",

        # Specific file actions
        r"create (this|the|a) file",
        r"modify (this|the|a) file",
        r"write to",
        r"edit the file",
        r"delete (this|the|a) file",
        r"run (this|the) command",
        r"execute (this|the) command",

        # Git actions
        r"ready to commit",
        r"ready to push",
        r"commit (these|the) changes",

        # Yes/No questions
        r"\?\s*$",  # Ends with a question mark
    ]

    response_lower = response.lower()

    # Check for question mark at the end (strong indicator)
    if response_lower.strip().endswith('?'):
        # Check if it mentions file operations
        file_ops = ['create', 'write', 'edit', 'modify', 'delete', 'remove', 'run', 'execute']
        if any(op in response_lower for op in file_ops):
            return True

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
        last_update_time = asyncio.get_event_loop().time()

        # Streaming callback to show real-time progress
        async def stream_callback(update_obj: StreamUpdate):
            """Update progress message with streaming updates."""
            nonlocal last_update_time
            current_time = asyncio.get_event_loop().time()

            # Handle file edit diff preview (not throttled)
            if update_obj.type == "file_edit":
                try:
                    # Generate diff image
                    diff_image_bytes = generate_diff_image(
                        update_obj.old_content,
                        update_obj.new_content,
                        update_obj.file_path
                    )

                    # Send diff image
                    await update.message.reply_photo(
                        photo=io.BytesIO(diff_image_bytes),
                        caption=f"📝 Proposed changes to `{update_obj.file_path}`",
                        parse_mode="Markdown"
                    )
                    logger.info(f"Sent diff image for {update_obj.file_path}")
                except Exception as e:
                    logger.error(f"Failed to send diff image: {e}")
                return

            # Throttle updates to max 1 per second to avoid Telegram rate limits
            if current_time - last_update_time < 1.0:
                return

            last_update_time = current_time

            # Format the progress message
            progress_text = ""
            if update_obj.type == "tool_use":
                # Show tools being used
                progress_text = f"🔧 **{update_obj.content}**"
            elif update_obj.type == "assistant":
                # Show Claude's thinking/response preview
                content_preview = (
                    update_obj.content[:150] + "..."
                    if len(update_obj.content) > 150
                    else update_obj.content
                )
                progress_text = f"🤖 **Working...**\n\n_{content_preview}_"
            elif update_obj.type == "result":
                # Execution completed
                progress_text = "✅ **Completed!**"

            if progress_text:
                try:
                    await thinking_msg.edit_text(progress_text, parse_mode="Markdown")
                except Exception as e:
                    # Ignore rate limit errors on streaming updates
                    logger.debug(f"Failed to update progress: {e}")

        # Get existing conversation history from context
        conversation_history = context.user_data.get("conversation_history", [])

        # Execute Claude CLI with streaming
        response, updated_history = await claude_executor.execute(
            message_text,
            user_id,
            conversation_history=conversation_history,
            stream_callback=stream_callback
        )

        # Store updated conversation history
        context.user_data["conversation_history"] = updated_history

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

        # Get existing conversation history from context
        conversation_history = context.user_data.get("conversation_history", [])

        # Execute the confirmed action
        thinking_msg = await query.message.reply_text("🔄 Executing action...")
        response, updated_history = await claude_executor.execute(
            confirmation_message,
            user_id,
            conversation_history=conversation_history
        )

        # Store updated conversation history
        context.user_data["conversation_history"] = updated_history

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
