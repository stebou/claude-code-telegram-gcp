"""
Claude Code SDK executor.
Handles Claude execution using the official Python SDK with streaming support.
"""
import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from claude_code_sdk import (
    ClaudeCodeOptions,
    ClaudeSDKError,
    CLIConnectionError,
    CLINotFoundError,
    Message,
    ProcessError,
    query,
)
from claude_code_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    UserMessage,
)

from src.config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class StreamUpdate:
    """Streaming update from Claude SDK."""
    type: str  # 'assistant', 'user', 'tool_use', 'tool_result', 'result'
    content: Optional[str] = None
    tool_name: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None


@dataclass
class ClaudeResponse:
    """Response from Claude Code SDK."""
    content: str
    session_id: str
    cost: float = 0.0
    duration_ms: int = 0
    num_turns: int = 0
    is_error: bool = False
    error_type: Optional[str] = None
    tools_used: List[Dict[str, Any]] = field(default_factory=list)


class ClaudeSDKExecutor:
    """Executes Claude Code commands via Python SDK."""

    def __init__(self):
        self.approved_directory = settings.approved_directory
        self.timeout = settings.claude_timeout_seconds
        self.allowed_tools = settings.claude_allowed_tools
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def execute(
        self,
        message: str,
        user_id: int,
        stream_callback: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> str:
        """
        Execute a Claude Code SDK command.

        Args:
            message: User message to send to Claude
            user_id: Telegram user ID
            stream_callback: Optional callback for streaming updates

        Returns:
            Claude's response as a string
        """
        try:
            logger.info(f"Executing Claude SDK for user {user_id}")

            # Build Claude Code options
            options = ClaudeCodeOptions(
                max_turns=10,
                cwd=str(self.approved_directory),
                allowed_tools=self.allowed_tools,
            )

            # Collect messages
            messages = []
            start_time = asyncio.get_event_loop().time()

            # Execute with streaming and timeout
            await asyncio.wait_for(
                self._execute_query_with_streaming(
                    message, options, messages, stream_callback
                ),
                timeout=self.timeout,
            )

            # Extract content and metadata
            content = self._extract_content_from_messages(messages)
            tools_used = self._extract_tools_from_messages(messages)
            cost = self._extract_cost_from_messages(messages)

            # Calculate duration
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)

            logger.info(
                f"Claude SDK completed successfully ({len(content)} chars, "
                f"{len(tools_used)} tools used, {duration_ms}ms)"
            )

            return content

        except asyncio.TimeoutError:
            logger.error(f"Claude SDK command timed out after {self.timeout} seconds")
            raise TimeoutError(
                f"Claude SDK timed out after {self.timeout} seconds"
            )

        except CLINotFoundError as e:
            logger.error(f"Claude CLI not found: {e}")
            raise RuntimeError(
                "Claude Code not found. Please ensure Claude is installed:\n"
                "  npm install -g @anthropic-ai/claude-code"
            )

        except ProcessError as e:
            logger.error(f"Claude process failed: {e}")
            raise RuntimeError(f"Claude process error: {str(e)}")

        except CLIConnectionError as e:
            logger.error(f"Claude connection error: {e}")
            raise RuntimeError(f"Failed to connect to Claude: {str(e)}")

        except ClaudeSDKError as e:
            logger.error(f"Claude SDK error: {e}")
            raise RuntimeError(f"Claude SDK error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error in Claude SDK: {e}")
            raise

    async def _execute_query_with_streaming(
        self,
        prompt: str,
        options: ClaudeCodeOptions,
        messages: List,
        stream_callback: Optional[Callable],
    ) -> None:
        """Execute query with streaming and collect messages."""
        try:
            async for message in query(prompt=prompt, options=options):
                messages.append(message)

                # Handle streaming callback
                if stream_callback:
                    try:
                        await self._handle_stream_message(message, stream_callback)
                    except Exception as callback_error:
                        logger.warning(
                            f"Stream callback failed: {callback_error}"
                        )
                        # Continue processing even if callback fails

        except Exception as e:
            # Handle ExceptionGroup from TaskGroup operations (Python 3.11+)
            if type(e).__name__ == "ExceptionGroup" or hasattr(e, "exceptions"):
                logger.error(
                    f"TaskGroup error in streaming execution: {e}, "
                    f"exception_count: {len(getattr(e, 'exceptions', []))}"
                )
                # Extract the most relevant exception from the group
                exceptions = getattr(e, "exceptions", [e])
                main_exception = exceptions[0] if exceptions else e
                raise RuntimeError(f"Claude SDK task error: {str(main_exception)}")
            else:
                logger.error(f"Error in streaming execution: {e}")
                raise

    async def _handle_stream_message(
        self, message: Message, stream_callback: Callable[[StreamUpdate], None]
    ) -> None:
        """Handle streaming message from claude-code-sdk."""
        try:
            if isinstance(message, AssistantMessage):
                # Extract content from assistant message
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    # Check for tool calls
                    tool_calls = []
                    text_parts = []

                    for block in content:
                        if isinstance(block, ToolUseBlock):
                            # Tool is being called
                            tool_name = getattr(block, "name", "unknown")
                            tool_input = getattr(block, "input", {})
                            tool_calls.append({
                                "name": tool_name,
                                "input": tool_input,
                            })
                        elif hasattr(block, "text"):
                            # Text content
                            text_parts.append(block.text)

                    if tool_calls:
                        # Send tool usage update
                        tools_str = ", ".join([t["name"] for t in tool_calls])
                        update = StreamUpdate(
                            type="tool_use",
                            content=f"Using tools: {tools_str}",
                            tool_calls=tool_calls,
                        )
                        await stream_callback(update)

                    if text_parts:
                        # Send content update
                        update = StreamUpdate(
                            type="assistant",
                            content="\n".join(text_parts),
                        )
                        await stream_callback(update)

            elif isinstance(message, ResultMessage):
                # Execution result
                update = StreamUpdate(
                    type="result",
                    content="Execution completed",
                    metadata={
                        "cost": getattr(message, "total_cost_usd", 0.0),
                    },
                )
                await stream_callback(update)

        except Exception as e:
            logger.warning(f"Stream callback failed: {e}")

    def _extract_content_from_messages(self, messages: List[Message]) -> str:
        """Extract content from message list."""
        content_parts = []

        for message in messages:
            if isinstance(message, AssistantMessage):
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    # Extract text from TextBlock objects
                    for block in content:
                        if hasattr(block, "text"):
                            content_parts.append(block.text)
                elif content:
                    # Fallback for non-list content
                    content_parts.append(str(content))

        return "\n".join(content_parts)

    def _extract_tools_from_messages(
        self, messages: List[Message]
    ) -> List[Dict[str, Any]]:
        """Extract tools used from message list."""
        tools_used = []
        current_time = asyncio.get_event_loop().time()

        for message in messages:
            if isinstance(message, AssistantMessage):
                content = getattr(message, "content", [])
                if content and isinstance(content, list):
                    for block in content:
                        if isinstance(block, ToolUseBlock):
                            tools_used.append(
                                {
                                    "name": getattr(block, "name", "unknown"),
                                    "timestamp": current_time,
                                    "input": getattr(block, "input", {}),
                                }
                            )

        return tools_used

    def _extract_cost_from_messages(self, messages: List[Message]) -> float:
        """Extract cost from message list."""
        for message in messages:
            if isinstance(message, ResultMessage):
                return getattr(message, "total_cost_usd", 0.0) or 0.0
        return 0.0

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
