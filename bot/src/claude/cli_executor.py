"""
Claude Code CLI executor (subprocess approach like richardatct).
Executes the claude CLI command and parses stream-json output.
"""
import asyncio
import json
import logging
import uuid
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamUpdate:
    """Enhanced streaming update from Claude CLI."""
    type: str  # 'assistant', 'user', 'system', 'result', 'tool_result', 'error', 'progress'
    content: Optional[str] = None
    tool_calls: Optional[List[Dict]] = None
    metadata: Optional[Dict] = None

    # Enhanced fields
    timestamp: Optional[str] = None
    progress: Optional[Dict] = None
    error_info: Optional[Dict] = None
    execution_id: Optional[str] = None

    def is_error(self) -> bool:
        """Check if this update represents an error."""
        return self.type == "error" or (
            self.metadata and self.metadata.get("is_error", False)
        )

    def get_tool_names(self) -> List[str]:
        """Extract tool names from tool calls."""
        if not self.tool_calls:
            return []
        return [call.get("name") for call in self.tool_calls if call.get("name")]

    def get_progress_percentage(self) -> Optional[int]:
        """Get progress percentage if available."""
        if self.progress:
            return self.progress.get("percentage")
        return None

    def get_error_message(self) -> Optional[str]:
        """Get error message if this is an error update."""
        if self.error_info:
            return self.error_info.get("message")
        elif self.is_error() and self.content:
            return self.content
        return None


@dataclass
class ClaudeResponse:
    """Response from Claude Code CLI."""
    content: str
    session_id: str
    cost: float = 0.0
    duration_ms: int = 0
    num_turns: int = 0
    is_error: bool = False
    error_type: Optional[str] = None
    tools_used: List[Dict[str, Any]] = field(default_factory=list)


class ClaudeProcessManager:
    """Manage Claude Code subprocess execution (richardatct approach)."""

    def __init__(self, config):
        """Initialize process manager with configuration."""
        self.config = config
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}

        # Memory optimization
        self.max_message_buffer = 1000
        self.streaming_buffer_size = 65536  # 64KB

    async def execute_command(
        self,
        prompt: str,
        working_directory: Path,
        session_id: Optional[str] = None,
        continue_session: bool = False,
        stream_callback: Optional[Callable[[StreamUpdate], None]] = None,
    ) -> ClaudeResponse:
        """Execute Claude Code CLI command."""
        # Build command
        cmd = self._build_command(prompt, session_id, continue_session)

        # Create process ID
        process_id = str(uuid.uuid4())

        logger.info(
            f"Starting Claude Code CLI process {process_id} in {working_directory}"
        )

        try:
            # Start subprocess
            process = await self._start_process(cmd, working_directory)
            self.active_processes[process_id] = process

            # Handle output with timeout
            result = await asyncio.wait_for(
                self._handle_process_output(process, stream_callback),
                timeout=self.config.claude_timeout_seconds,
            )

            logger.info(
                f"Claude CLI completed successfully: cost=${result.cost:.4f}, "
                f"duration={result.duration_ms}ms, tools={len(result.tools_used)}"
            )

            return result

        except asyncio.TimeoutError:
            # Kill on timeout
            if process_id in self.active_processes:
                self.active_processes[process_id].kill()
                await self.active_processes[process_id].wait()

            logger.error(
                f"Claude CLI timed out after {self.config.claude_timeout_seconds}s"
            )
            raise TimeoutError(
                f"Claude Code timed out after {self.config.claude_timeout_seconds}s"
            )

        except Exception as e:
            logger.error(f"Claude CLI process failed: {e}")
            raise

        finally:
            # Cleanup
            if process_id in self.active_processes:
                del self.active_processes[process_id]

    def _build_command(
        self, prompt: str, session_id: Optional[str], continue_session: bool
    ) -> List[str]:
        """Build Claude CLI command (richardatct approach)."""
        cmd = ["claude"]  # CLI binary

        if continue_session and not prompt:
            # Continue existing session without new prompt
            cmd.extend(["--continue"])
            if session_id:
                cmd.extend(["--resume", session_id])
        elif session_id and prompt and continue_session:
            # Follow-up message in existing session
            cmd.extend(["--resume", session_id, "-p", prompt])
        elif prompt:
            # New session with prompt
            cmd.extend(["-p", prompt])
        else:
            # Fallback
            cmd.extend(["-p", ""])

        # Always use streaming JSON for real-time updates
        cmd.extend(["--output-format", "stream-json"])
        cmd.extend(["--verbose"])

        # Safety limits
        cmd.extend(["--max-turns", str(self.config.claude_max_turns)])

        # Allowed tools
        if hasattr(self.config, 'claude_allowed_tools') and self.config.claude_allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self.config.claude_allowed_tools)])

        logger.debug(f"Built command: {' '.join(cmd)}")
        return cmd

    async def _start_process(self, cmd: List[str], cwd: Path) -> asyncio.subprocess.Process:
        """Start Claude CLI subprocess."""
        return await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
            limit=1024 * 1024 * 512,  # 512MB memory limit
        )

    async def _handle_process_output(
        self, process: asyncio.subprocess.Process, stream_callback: Optional[Callable]
    ) -> ClaudeResponse:
        """Parse stream-json output from Claude CLI."""
        message_buffer = deque(maxlen=self.max_message_buffer)
        result_data = None
        parsing_errors = []

        # Collect all content and tools
        all_content = []
        all_tools = []

        async for line in self._read_stream_bounded(process.stdout):
            try:
                msg = json.loads(line)

                # Validate message structure
                if not isinstance(msg, dict) or "type" not in msg:
                    parsing_errors.append(f"Invalid message: {line[:100]}")
                    continue

                message_buffer.append(msg)

                # Parse and send stream update
                update = self._parse_stream_message(msg)
                if update and stream_callback:
                    try:
                        await stream_callback(update)
                    except Exception as e:
                        logger.warning(f"Stream callback failed: {e}")

                # Extract content from assistant messages
                if msg.get("type") == "assistant":
                    content_blocks = msg.get("content", [])
                    for block in content_blocks:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                all_content.append(block.get("text", ""))
                            elif block.get("type") == "tool_use":
                                all_tools.append({
                                    "name": block.get("name"),
                                    "input": block.get("input", {}),
                                    "id": block.get("id"),
                                })

                # Check for final result
                if msg.get("type") == "result":
                    result_data = msg

            except json.JSONDecodeError as e:
                parsing_errors.append(f"JSON decode error: {e}")
                logger.warning(f"Failed to parse line: {line[:200]}")
                continue

        # Log parsing errors
        if parsing_errors:
            logger.warning(f"Encountered {len(parsing_errors)} parsing errors")

        # Wait for process completion
        return_code = await process.wait()

        if return_code != 0:
            stderr = await process.stderr.read()
            error_msg = stderr.decode("utf-8", errors="replace")
            logger.error(f"Claude CLI failed with code {return_code}: {error_msg}")

            return ClaudeResponse(
                content=f"Error: {error_msg}",
                session_id="",
                is_error=True,
                error_type="process_error",
            )

        # Extract final response
        content_text = "\n".join(all_content) if all_content else "No response"
        session_id = result_data.get("session_id", "") if result_data else ""
        cost = result_data.get("total_cost_usd", 0.0) if result_data else 0.0

        return ClaudeResponse(
            content=content_text,
            session_id=session_id,
            cost=cost,
            duration_ms=0,  # Not tracked in this simple version
            num_turns=len(message_buffer),
            tools_used=all_tools,
        )

    async def _read_stream_bounded(self, stream):
        """Read stream line by line with memory bounds."""
        buffer = b""
        while True:
            chunk = await stream.read(self.streaming_buffer_size)
            if not chunk:
                break

            buffer += chunk

            # Process complete lines
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                yield line.decode("utf-8", errors="replace")

    def _parse_stream_message(self, msg: dict) -> Optional[StreamUpdate]:
        """Parse stream-json message into StreamUpdate."""
        msg_type = msg.get("type")

        if msg_type == "assistant":
            # Extract tool calls
            tool_calls = []
            text_parts = []
            content = msg.get("content", [])

            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_use":
                        tool_calls.append({
                            "name": block.get("name"),
                            "input": block.get("input", {}),
                        })
                    elif block.get("type") == "text":
                        text_parts.append(block.get("text", ""))

            if tool_calls:
                return StreamUpdate(
                    type="assistant",
                    content="Using tools: " + ", ".join([t["name"] for t in tool_calls]),
                    tool_calls=tool_calls,
                )
            elif text_parts:
                return StreamUpdate(
                    type="assistant",
                    content="\n".join(text_parts),
                )

        elif msg_type == "tool_result":
            return StreamUpdate(
                type="tool_result",
                content=f"Tool completed: {msg.get('tool_use_id', 'unknown')}",
                metadata=msg,
            )

        elif msg_type == "result":
            return StreamUpdate(
                type="result",
                content="Execution completed",
                metadata={
                    "cost": msg.get("total_cost_usd", 0.0),
                    "session_id": msg.get("session_id", ""),
                },
            )

        return None
