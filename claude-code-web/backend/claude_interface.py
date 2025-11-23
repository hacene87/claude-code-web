"""
Interface to Claude Code CLI.
Handles subprocess management and output parsing.
"""
import asyncio
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any, Callable
from pathlib import Path


class ClaudeCodeInterface:
    """Interface for interacting with Claude Code CLI."""

    def __init__(self):
        self.claude_path = self._find_claude_executable()
        self.active_processes: Dict[str, asyncio.subprocess.Process] = {}

    def _find_claude_executable(self) -> Optional[str]:
        """Find the Claude Code CLI executable."""
        # Check common locations
        possible_paths = [
            "claude",  # In PATH
            "/usr/local/bin/claude",
            "/usr/bin/claude",
            os.path.expanduser("~/.local/bin/claude"),
            os.path.expanduser("~/.npm-global/bin/claude"),
            # For npm global installs
            shutil.which("claude"),
        ]

        for path in possible_paths:
            if path and (Path(path).exists() or shutil.which(path)):
                return path

        return None

    def is_installed(self) -> bool:
        """Check if Claude Code CLI is installed."""
        return self.claude_path is not None

    def get_version(self) -> Optional[str]:
        """Get Claude Code CLI version."""
        if not self.is_installed():
            return None
        try:
            result = subprocess.run(
                [self.claude_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip() or result.stderr.strip()
        except Exception:
            return None

    async def chat_stream(
        self,
        message: str,
        workspace: str = ".",
        conversation_id: Optional[str] = None,
        on_chunk: Optional[Callable[[str, str, Dict], None]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Send a message to Claude Code and stream the response.

        Args:
            message: The message to send
            workspace: Working directory
            conversation_id: Optional conversation ID for continuation
            on_chunk: Optional callback for each chunk

        Yields:
            Dict with type, content, and metadata
        """
        if not self.is_installed():
            yield {
                "type": "error",
                "content": "Claude Code CLI is not installed. Please install it first.",
                "metadata": {}
            }
            return

        # Build command
        cmd = [
            self.claude_path,
            "-p",  # Print mode (non-interactive)
            "--output-format", "stream-json",
            "--verbose",  # Required for stream-json
        ]

        # Add conversation continuation if provided
        if conversation_id:
            cmd.extend(["--resume", conversation_id])

        # Add the message as positional argument
        cmd.append(message)

        # Expand workspace path
        workspace_path = os.path.abspath(os.path.expanduser(workspace))

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace_path
            )

            # Store process for potential cancellation
            proc_id = conversation_id or datetime.now().isoformat()
            self.active_processes[proc_id] = process

            buffer = ""

            # Read stdout line by line
            while True:
                line = await process.stdout.readline()
                if not line:
                    break

                text = line.decode('utf-8', errors='replace').strip()
                if not text:
                    continue

                # Try to parse as JSON
                try:
                    data = json.loads(text)
                    chunk = self._parse_stream_json(data)
                    if chunk:
                        if on_chunk:
                            on_chunk(chunk["type"], chunk["content"], chunk.get("metadata", {}))
                        yield chunk
                except json.JSONDecodeError:
                    # Plain text output
                    yield {
                        "type": "text",
                        "content": text,
                        "metadata": {}
                    }

            # Wait for process to complete
            await process.wait()

            # Check for errors
            if process.returncode != 0:
                stderr = await process.stderr.read()
                error_text = stderr.decode('utf-8', errors='replace')
                yield {
                    "type": "error",
                    "content": f"Process exited with code {process.returncode}: {error_text}",
                    "metadata": {"return_code": process.returncode}
                }

            yield {
                "type": "done",
                "content": "",
                "metadata": {"conversation_id": proc_id}
            }

        except asyncio.CancelledError:
            yield {
                "type": "status",
                "content": "Request cancelled",
                "metadata": {}
            }
        except Exception as e:
            yield {
                "type": "error",
                "content": str(e),
                "metadata": {"error_type": type(e).__name__}
            }
        finally:
            # Cleanup
            if proc_id in self.active_processes:
                del self.active_processes[proc_id]

    def _parse_stream_json(self, data: Dict) -> Optional[Dict[str, Any]]:
        """Parse a JSON chunk from Claude Code stream output."""
        msg_type = data.get("type", "")

        if msg_type == "assistant":
            # Assistant message content
            message = data.get("message", {})
            content_blocks = message.get("content", [])

            text_parts = []
            for block in content_blocks:
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    return {
                        "type": "tool_use",
                        "content": json.dumps(block, indent=2),
                        "metadata": {
                            "tool_name": block.get("name"),
                            "tool_id": block.get("id")
                        }
                    }

            if text_parts:
                return {
                    "type": "text",
                    "content": "\n".join(text_parts),
                    "metadata": {}
                }

        elif msg_type == "content_block_delta":
            delta = data.get("delta", {})
            if delta.get("type") == "text_delta":
                return {
                    "type": "text",
                    "content": delta.get("text", ""),
                    "metadata": {"streaming": True}
                }

        elif msg_type == "result":
            # Final result - also extract the result text if available
            result_text = data.get("result", "")
            if result_text:
                return {
                    "type": "text",
                    "content": result_text,
                    "metadata": {"final": True}
                }
            return {
                "type": "done",
                "content": "",
                "metadata": data
            }

        elif msg_type == "system":
            # Skip system init messages, only return actual system messages
            if data.get("subtype") == "init":
                return None
            return {
                "type": "status",
                "content": data.get("message", ""),
                "metadata": data
            }

        return None

    async def cancel(self, conversation_id: str) -> bool:
        """Cancel an active conversation."""
        if conversation_id in self.active_processes:
            process = self.active_processes[conversation_id]
            process.terminate()
            await process.wait()
            del self.active_processes[conversation_id]
            return True
        return False

    async def execute_command(
        self,
        command: str,
        workspace: str = "."
    ) -> Dict[str, Any]:
        """
        Execute a single command through Claude Code.
        Non-streaming version for simple operations.
        """
        if not self.is_installed():
            return {
                "success": False,
                "error": "Claude Code CLI is not installed"
            }

        workspace_path = os.path.abspath(os.path.expanduser(workspace))

        cmd = [
            self.claude_path,
            "-p",  # Print mode (non-interactive)
            "--output-format", "json",
            command  # Message as positional argument
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=workspace_path,
                timeout=300  # 5 minute timeout
            )

            try:
                output = json.loads(result.stdout)
            except json.JSONDecodeError:
                output = {"raw_output": result.stdout}

            return {
                "success": result.returncode == 0,
                "output": output,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Command timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class ConversationManager:
    """Manage conversation sessions."""

    def __init__(self, storage_path: str = ".claude-web-sessions"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        self.conversations: Dict[str, Dict] = {}
        self._load_conversations()

    def _load_conversations(self):
        """Load existing conversations from storage."""
        for file in self.storage_path.glob("*.json"):
            try:
                with open(file) as f:
                    conv = json.load(f)
                    self.conversations[conv["id"]] = conv
            except Exception:
                pass

    def create_conversation(self, workspace: str) -> str:
        """Create a new conversation."""
        conv_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        self.conversations[conv_id] = {
            "id": conv_id,
            "workspace": workspace,
            "messages": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self._save_conversation(conv_id)
        return conv_id

    def add_message(self, conv_id: str, role: str, content: str, metadata: Dict = None):
        """Add a message to a conversation."""
        if conv_id not in self.conversations:
            raise ValueError(f"Conversation {conv_id} not found")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        self.conversations[conv_id]["messages"].append(message)
        self.conversations[conv_id]["updated_at"] = datetime.now().isoformat()
        self._save_conversation(conv_id)

    def get_conversation(self, conv_id: str) -> Optional[Dict]:
        """Get a conversation by ID."""
        return self.conversations.get(conv_id)

    def list_conversations(self) -> list:
        """List all conversations."""
        return sorted(
            self.conversations.values(),
            key=lambda x: x["updated_at"],
            reverse=True
        )

    def delete_conversation(self, conv_id: str) -> bool:
        """Delete a conversation."""
        if conv_id in self.conversations:
            del self.conversations[conv_id]
            file_path = self.storage_path / f"{conv_id}.json"
            if file_path.exists():
                file_path.unlink()
            return True
        return False

    def _save_conversation(self, conv_id: str):
        """Save a conversation to disk."""
        file_path = self.storage_path / f"{conv_id}.json"
        with open(file_path, "w") as f:
            json.dump(self.conversations[conv_id], f, indent=2)
