"""
Claude Code CLI executor.
Handles subprocess execution of claude commands.
"""
import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Optional

from src.config.settings import settings

logger = logging.getLogger(__name__)


class ClaudeExecutor:
    """Executes Claude Code CLI commands via subprocess."""

    def __init__(self):
        self.approved_directory = settings.approved_directory
        self.timeout = settings.claude_timeout_seconds
        self.allowed_tools = settings.claude_allowed_tools

    async def execute(self, message: str, user_id: int) -> str:
        """
        Execute a Claude Code CLI command.

        Args:
            message: User message to send to Claude
            user_id: Telegram user ID

        Returns:
            Claude's response as a string
        """
        try:
            # Prepare the command
            cmd = self._build_command(message)

            logger.info(f"Executing Claude CLI for user {user_id}")
            logger.debug(f"Command: {cmd[:100]}...")  # Log first 100 chars

            # Run claude command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.approved_directory),
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(
                    f"Claude command timed out after {self.timeout} seconds"
                )

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace")
                logger.error(f"Claude command failed: {error_msg}")
                raise RuntimeError(f"Claude command failed: {error_msg}")

            response = stdout.decode("utf-8", errors="replace")
            logger.info(f"Claude command completed successfully ({len(response)} chars)")
            return response

        except Exception as e:
            logger.error(f"Error executing Claude command: {e}")
            raise

    def _build_command(self, message: str) -> list:
        """
        Build the Claude CLI command with proper arguments.

        Args:
            message: User message

        Returns:
            List of command arguments
        """
        # Base command - claude accepts message directly
        # Note: Tools are configured in Claude's config file, not via CLI args
        cmd = ["claude", message]

        return cmd

    async def check_cost(self, user_id: int) -> float:
        """
        Check the current cost for a user.

        Args:
            user_id: Telegram user ID

        Returns:
            Current cost in USD
        """
        # TODO: Implement cost tracking
        # For now, return 0.0
        return 0.0

    async def is_within_budget(self, user_id: int) -> bool:
        """
        Check if user is within their budget.

        Args:
            user_id: Telegram user ID

        Returns:
            True if within budget, False otherwise
        """
        current_cost = await self.check_cost(user_id)
        max_cost = settings.claude_max_cost_per_user
        return current_cost < max_cost
