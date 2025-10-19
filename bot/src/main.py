"""
Main entry point for the Telegram bot.
"""
import logging
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from src.config.settings import settings
from src.handlers.message_handler import start_command, handle_message, handle_callback_query

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.log_level.upper()),
)
logger = logging.getLogger(__name__)


def main():
    """Start the bot."""
    logger.info("Starting Telegram Bot...")
    logger.info(f"Approved directory: {settings.approved_directory}")
    logger.info(f"Allowed users: {settings.allowed_users}")
    logger.info(f"Allowed tools: {settings.claude_allowed_tools}")

    # Create application
    application = Application.builder().token(settings.telegram_bot_token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # Start polling
    logger.info("Bot started successfully. Polling for messages...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
