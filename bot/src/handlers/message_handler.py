"""Telegram message handlers."""
import asyncio
import io
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from src.claude.cli_executor import ClaudeProcessManager, StreamUpdate
from src.security.validator import security_validator
from src.config.settings import settings

logger = logging.getLogger(__name__)

# Global executor (using CLI subprocess like richardatct)
claude_executor = ClaudeProcessManager(settings)

# Note: No confirmation system - Claude executes actions directly (like richardatct)


async def _send_typing_periodically(context: ContextTypes.DEFAULT_TYPE, update: Update):
    """Send typing indicator every 4 seconds to show bot is working."""
    try:
        while True:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING
            )
            await asyncio.sleep(4)  # Typing lasts 5s, renew every 4s
    except asyncio.CancelledError:
        # Task was cancelled, stop gracefully
        pass
    except Exception as e:
        logger.debug(f"Typing indicator error: {e}")


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


# Note: Removed detect_action_in_response - Claude executes actions directly now


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

    # Budget check removed (CLI doesn't have built-in budget tracking)

    try:
        # Start typing indicator (shows "..." animation in Telegram)
        typing_task = asyncio.create_task(_send_typing_periodically(context, update))

        # Send "thinking" message
        thinking_msg = await update.message.reply_text("🤔 Processing...")

        # Initialize last_update_time for THIS message (must be inside try block)
        last_update_time = 0  # Start at 0 to allow immediate first update

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

        # Get current session ID (if any)
        session_id = context.user_data.get('claude_session_id')

        # Execute Claude CLI with streaming (subprocess approach)
        response_obj = await claude_executor.execute_command(
            prompt=message_text,
            working_directory=claude_executor.config.approved_directory,
            session_id=session_id,
            continue_session=bool(session_id),
            stream_callback=stream_callback
        )

        # Store session ID for next message
        if response_obj.session_id:
            context.user_data['claude_session_id'] = response_obj.session_id

        # Get response text
        response = response_obj.content

        # Stop typing indicator
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

        # Send response (split if too long) - no confirmation needed
        if len(response) > 4096:
            chunks = [response[i:i+4096] for i in range(0, len(response), 4096)]
            await thinking_msg.delete()
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await thinking_msg.edit_text(response)

    except TimeoutError:
        # Stop typing on timeout
        if 'typing_task' in locals():
            typing_task.cancel()
        await update.message.reply_text(
            "⏱️ Request timed out. Please try a simpler request."
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await update.message.reply_text(
            f"❌ Error: {str(e)[:200]}"
        )


# Note: handle_callback_query removed - no confirmation system needed (matches richardatct)
