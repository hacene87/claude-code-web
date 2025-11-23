"""
Error Fixer Service
===================

AI-powered error resolution using Claude Code CLI.
Implements FR-FIX-001, FR-FIX-002, FR-FIX-003.
"""

import asyncio
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, RetryConfig
from app.core.database import get_session
from app.models.error import Error, ErrorStatus, FixAttempt, FixAttemptStatus
from app.services.event_bus import EventBus, EventType, get_event_bus

logger = structlog.get_logger()


# Claude prompt template (FR-FIX-001)
CLAUDE_PROMPT_TEMPLATE = """
You are an expert Odoo 19 developer fixing an error in a custom module.

## ERROR INFORMATION
- **Type**: {error_type}
- **Module**: {module_name}
- **File**: {file_path}
- **Line**: {line_number}

## ERROR MESSAGE
```
{error_message}
```

## STACK TRACE
```
{stack_trace}
```

## CONTEXT (surrounding code)
```python
{code_context}
```

## INSTRUCTIONS
1. Analyze the root cause of this error
2. Make the MINIMUM changes necessary to fix the error
3. Follow Odoo 19 best practices and conventions
4. Do NOT modify unrelated code
5. Do NOT add unnecessary comments or documentation
6. Verify the fix does not introduce new errors

Apply the fix directly to the source file.
"""


@dataclass
class ClaudeResponse:
    """Response from Claude Code CLI."""
    success: bool
    files_modified: List[str] = field(default_factory=list)
    changes_made: str = ""
    reasoning: str = ""
    execution_time_seconds: float = 0.0
    tokens_used: int = 0
    raw_output: str = ""
    error_message: Optional[str] = None


@dataclass
class VerificationResult:
    """Result of fix verification."""
    fix_successful: bool
    original_error_resolved: bool = False
    new_errors_introduced: List[str] = field(default_factory=list)
    syntax_check_passed: bool = True
    tests_passed: Optional[bool] = None
    verification_duration_seconds: float = 0.0


class ErrorFixerService:
    """
    Service for automatically fixing errors using Claude Code CLI.

    Implements:
    - Claude Code CLI invocation with error context
    - 5-attempt retry mechanism with exponential backoff
    - Fix verification
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.settings = get_settings()
        self.event_bus = event_bus or get_event_bus()
        self.retry_config = self.settings.retry
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._current_fix: Optional[str] = None

    async def start(self) -> None:
        """Start the error fixing service."""
        if self._running:
            logger.warning("error_fixer_already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._fixing_loop())
        logger.info("error_fixer_started")

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "error_fixer", "status": "running"},
            source="error_fixer"
        )

    async def stop(self) -> None:
        """Stop the error fixing service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("error_fixer_stopped")

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "error_fixer", "status": "stopped"},
            source="error_fixer"
        )

    async def _fixing_loop(self) -> None:
        """Main loop for processing queued errors."""
        while self._running:
            try:
                # Find next error to fix
                error = await self._get_next_error()
                if error:
                    await self._process_error(error)
                else:
                    # No errors to fix, wait before checking again
                    await asyncio.sleep(10)
            except Exception as e:
                logger.error("fixing_loop_error", error=str(e))
                await asyncio.sleep(30)

    async def _get_next_error(self) -> Optional[Error]:
        """Get the next error to process."""
        async with get_session() as session:
            # First, check for errors that need retry (after backoff delay)
            result = await session.execute(
                select(Error)
                .where(
                    and_(
                        Error.status == ErrorStatus.QUEUED,
                        Error.auto_fixable == True
                    )
                )
                .order_by(Error.detected_at)
                .limit(1)
            )
            error = result.scalar_one_or_none()

            if not error:
                # Check for newly detected errors
                result = await session.execute(
                    select(Error)
                    .where(
                        and_(
                            Error.status == ErrorStatus.DETECTED,
                            Error.auto_fixable == True
                        )
                    )
                    .order_by(Error.detected_at)
                    .limit(1)
                )
                error = result.scalar_one_or_none()

                if error:
                    # Queue it for fixing
                    error.status = ErrorStatus.QUEUED
                    await session.commit()

            return error

    async def _process_error(self, error: Error) -> None:
        """Process a single error through the fix pipeline."""
        async with get_session() as session:
            # Refresh error from database
            result = await session.execute(
                select(Error).where(Error.id == error.id)
            )
            error = result.scalar_one()

            # Check attempt count
            attempt_count = len(error.fix_attempts)
            if attempt_count >= self.retry_config.max_attempts:
                # Escalate error
                error.status = ErrorStatus.FAILED
                await session.commit()

                await self.event_bus.emit(
                    EventType.FIX_ESCALATED,
                    {
                        "error_id": error.id,
                        "error_type": error.error_type,
                        "attempts": attempt_count,
                    },
                    source="error_fixer"
                )
                logger.warning(
                    "error_escalated",
                    error_id=error.id,
                    attempts=attempt_count
                )
                return

            # Calculate backoff delay
            if attempt_count > 0:
                delay = self.retry_config.get_delay(attempt_count)
                last_attempt = error.fix_attempts[-1]
                if last_attempt.completed_at:
                    time_since_last = (datetime.utcnow() - last_attempt.completed_at).total_seconds()
                    if time_since_last < delay:
                        # Not ready for retry yet
                        return

            # Start fixing
            error.status = ErrorStatus.FIXING
            self._current_fix = error.id

            # Create fix attempt record
            fix_attempt = FixAttempt(
                error_id=error.id,
                attempt_number=attempt_count + 1,
                status=FixAttemptStatus.IN_PROGRESS,
                started_at=datetime.utcnow()
            )
            session.add(fix_attempt)
            await session.commit()

            await self.event_bus.emit(
                EventType.FIX_STARTED,
                {
                    "error_id": error.id,
                    "attempt": fix_attempt.attempt_number,
                    "max_attempts": self.retry_config.max_attempts,
                },
                source="error_fixer"
            )

            logger.info(
                "fix_attempt_started",
                error_id=error.id,
                attempt=fix_attempt.attempt_number
            )

            try:
                # Invoke Claude Code CLI
                claude_response = await self._invoke_claude_code(error)

                # Update fix attempt with response
                fix_attempt.claude_prompt = self._generate_prompt(error)
                fix_attempt.claude_response = claude_response.raw_output[:50000]
                fix_attempt.files_modified = claude_response.files_modified
                fix_attempt.execution_time_seconds = claude_response.execution_time_seconds

                if claude_response.success:
                    # Verify the fix
                    verification = await self._verify_fix(error, claude_response)

                    if verification.fix_successful:
                        fix_attempt.status = FixAttemptStatus.SUCCESS
                        error.status = ErrorStatus.RESOLVED
                        error.resolved_at = datetime.utcnow()

                        await self.event_bus.emit(
                            EventType.FIX_COMPLETED,
                            {
                                "error_id": error.id,
                                "attempt": fix_attempt.attempt_number,
                                "files_modified": claude_response.files_modified,
                            },
                            source="error_fixer"
                        )

                        logger.info(
                            "fix_successful",
                            error_id=error.id,
                            attempt=fix_attempt.attempt_number
                        )
                    else:
                        fix_attempt.status = FixAttemptStatus.FAILED
                        fix_attempt.error_after_fix = "\n".join(verification.new_errors_introduced)
                        error.status = ErrorStatus.QUEUED  # Queue for retry

                        await self.event_bus.emit(
                            EventType.FIX_FAILED,
                            {
                                "error_id": error.id,
                                "attempt": fix_attempt.attempt_number,
                                "reason": "verification_failed",
                                "new_errors": verification.new_errors_introduced,
                            },
                            source="error_fixer"
                        )

                        logger.warning(
                            "fix_verification_failed",
                            error_id=error.id,
                            attempt=fix_attempt.attempt_number
                        )
                else:
                    fix_attempt.status = FixAttemptStatus.FAILED
                    error.status = ErrorStatus.QUEUED

                    await self.event_bus.emit(
                        EventType.FIX_FAILED,
                        {
                            "error_id": error.id,
                            "attempt": fix_attempt.attempt_number,
                            "reason": claude_response.error_message or "claude_invocation_failed",
                        },
                        source="error_fixer"
                    )

                    logger.warning(
                        "claude_invocation_failed",
                        error_id=error.id,
                        attempt=fix_attempt.attempt_number,
                        error=claude_response.error_message
                    )

            except asyncio.TimeoutError:
                fix_attempt.status = FixAttemptStatus.TIMEOUT
                error.status = ErrorStatus.QUEUED

                await self.event_bus.emit(
                    EventType.FIX_FAILED,
                    {
                        "error_id": error.id,
                        "attempt": fix_attempt.attempt_number,
                        "reason": "timeout",
                    },
                    source="error_fixer"
                )

                logger.warning(
                    "fix_timeout",
                    error_id=error.id,
                    attempt=fix_attempt.attempt_number
                )

            except Exception as e:
                fix_attempt.status = FixAttemptStatus.FAILED
                error.status = ErrorStatus.QUEUED

                logger.error(
                    "fix_error",
                    error_id=error.id,
                    attempt=fix_attempt.attempt_number,
                    error=str(e)
                )

            finally:
                fix_attempt.completed_at = datetime.utcnow()
                self._current_fix = None
                await session.commit()

    async def _invoke_claude_code(self, error: Error) -> ClaudeResponse:
        """
        Invoke Claude Code CLI to fix an error.

        Implements FR-FIX-001: Claude Code CLI Integration.
        """
        if not self.settings.claude.enabled:
            return ClaudeResponse(
                success=False,
                error_message="Claude Code CLI is disabled"
            )

        # Generate prompt
        prompt = self._generate_prompt(error)

        # Determine workspace path
        workspace_path = self._get_workspace_path(error)

        # Build command
        cmd = [
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--allowedTools", ",".join(self.settings.claude.allowed_tools),
            "--max-turns", str(self.settings.claude.max_turns),
            "-p", prompt
        ]

        start_time = time.time()

        loop = asyncio.get_event_loop()
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._run_claude_command,
                    cmd,
                    workspace_path
                ),
                timeout=self.settings.claude.timeout_seconds
            )
            execution_time = time.time() - start_time

            # Parse response
            return ClaudeResponse(
                success=result.returncode == 0,
                raw_output=result.stdout or result.stderr or "",
                execution_time_seconds=execution_time,
                files_modified=self._extract_modified_files(result.stdout or ""),
                error_message=result.stderr if result.returncode != 0 else None
            )

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            return ClaudeResponse(
                success=False,
                error_message=str(e),
                execution_time_seconds=time.time() - start_time
            )

    def _run_claude_command(
        self,
        cmd: List[str],
        cwd: str
    ) -> subprocess.CompletedProcess:
        """Run Claude Code CLI command (runs in thread pool)."""
        return subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=self.settings.claude.timeout_seconds
        )

    def _generate_prompt(self, error: Error) -> str:
        """Generate Claude prompt from error context."""
        # Get code context if file path is known
        code_context = ""
        if error.file_path and error.line_number:
            code_context = self._get_code_context(
                error.file_path,
                error.line_number
            )

        return CLAUDE_PROMPT_TEMPLATE.format(
            error_type=error.error_type,
            module_name=error.module_name or "unknown",
            file_path=error.file_path or "unknown",
            line_number=error.line_number or "unknown",
            error_message=error.message,
            stack_trace=error.stack_trace or "Not available",
            code_context=code_context or "Not available"
        )

    def _get_code_context(
        self,
        file_path: str,
        line_number: int,
        context_lines: int = 10
    ) -> str:
        """Get code context around the error line."""
        try:
            path = Path(file_path)
            if not path.exists():
                return ""

            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            start = max(0, line_number - context_lines - 1)
            end = min(len(lines), line_number + context_lines)

            context_lines = []
            for i, line in enumerate(lines[start:end], start=start + 1):
                marker = ">>>" if i == line_number else "   "
                context_lines.append(f"{marker} {i:4d}: {line.rstrip()}")

            return "\n".join(context_lines)
        except Exception:
            return ""

    def _get_workspace_path(self, error: Error) -> str:
        """Determine the workspace path for Claude."""
        if error.file_path:
            # Find the addons directory
            path = Path(error.file_path)
            for parent in path.parents:
                if parent.name in ("addons", "custom_addons") or (parent / "__manifest__.py").exists():
                    return str(parent.parent)
        # Default to first configured addons path
        if self.settings.odoo.addons_paths:
            return self.settings.odoo.addons_paths[0]
        return "/home/odoo/custom_addons"

    def _extract_modified_files(self, output: str) -> List[str]:
        """Extract list of modified files from Claude output."""
        files = []
        # Look for common patterns
        import re
        # Pattern for file paths in output
        patterns = [
            r'(?:Modified|Edited|Updated|Created)\s+[`"]?([^`"\n]+\.py)[`"]?',
            r'Writing to\s+([^\n]+\.py)',
            r'Saving\s+([^\n]+\.py)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, output, re.IGNORECASE)
            files.extend(matches)
        return list(set(files))

    async def _verify_fix(
        self,
        error: Error,
        claude_response: ClaudeResponse
    ) -> VerificationResult:
        """
        Verify that a fix resolved the error.

        Implements FR-FIX-003: Post-Fix Verification.
        """
        start_time = time.time()
        result = VerificationResult(fix_successful=False)

        # Step 1: Syntax check modified files
        for file_path in claude_response.files_modified:
            if file_path.endswith(".py"):
                syntax_ok = await self._check_python_syntax(file_path)
                if not syntax_ok:
                    result.syntax_check_passed = False
                    result.new_errors_introduced.append(f"Syntax error in {file_path}")

        if not result.syntax_check_passed:
            result.verification_duration_seconds = time.time() - start_time
            return result

        # Step 2: Restart Odoo if needed
        from app.services.updater import UpdaterService
        updater = UpdaterService(self.event_bus)

        await updater._stop_odoo()
        await updater._start_odoo()
        await updater._wait_for_odoo_ready(timeout=60)

        # Step 3: Wait for logs to stabilize
        await asyncio.sleep(30)

        # Step 4: Check if original error reappears
        original_error_found = await self._check_for_error_in_logs(
            error.error_type,
            error.message[:100]
        )
        result.original_error_resolved = not original_error_found

        # Step 5: Check for new errors
        new_errors = await self._get_recent_errors(since_seconds=60)
        result.new_errors_introduced = new_errors

        # Determine success
        result.fix_successful = (
            result.syntax_check_passed and
            result.original_error_resolved and
            len(result.new_errors_introduced) == 0
        )

        result.verification_duration_seconds = time.time() - start_time
        return result

    async def _check_python_syntax(self, file_path: str) -> bool:
        """Check Python file syntax."""
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None,
                subprocess.run,
                ["python", "-m", "py_compile", file_path],
            )
            return result.returncode == 0
        except Exception:
            return False

    async def _check_for_error_in_logs(
        self,
        error_type: str,
        error_message: str
    ) -> bool:
        """Check if an error appears in recent logs."""
        log_path = Path(self.settings.odoo.log_file)
        if not log_path.exists():
            return False

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["tail", "-n", "200", str(log_path)],
                capture_output=True,
                text=True
            ).stdout
        )

        return error_type in content and error_message in content

    async def _get_recent_errors(self, since_seconds: int = 60) -> List[str]:
        """Get errors from logs in the last N seconds."""
        log_path = Path(self.settings.odoo.log_file)
        if not log_path.exists():
            return []

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["tail", "-n", "500", str(log_path)],
                capture_output=True,
                text=True
            ).stdout
        )

        errors = []
        for line in content.split("\n"):
            if "ERROR" in line or "CRITICAL" in line:
                errors.append(line[:200])

        return errors[-10:]  # Return last 10 errors

    async def retry_error(self, error_id: str) -> bool:
        """Manually trigger a retry for an error."""
        async with get_session() as session:
            result = await session.execute(
                select(Error).where(Error.id == error_id)
            )
            error = result.scalar_one_or_none()

            if not error:
                return False

            if error.status not in (ErrorStatus.FAILED, ErrorStatus.IGNORED):
                return False

            error.status = ErrorStatus.QUEUED
            await session.commit()

            logger.info("error_retry_queued", error_id=error_id)
            return True

    async def ignore_error(self, error_id: str, ignored_by: str) -> bool:
        """Mark an error as ignored."""
        async with get_session() as session:
            result = await session.execute(
                select(Error).where(Error.id == error_id)
            )
            error = result.scalar_one_or_none()

            if not error:
                return False

            error.status = ErrorStatus.IGNORED
            error.ignored_at = datetime.utcnow()
            error.ignored_by = ignored_by
            await session.commit()

            await self.event_bus.emit(
                EventType.ERROR_IGNORED,
                {"error_id": error_id, "ignored_by": ignored_by},
                source="error_fixer"
            )

            logger.info("error_ignored", error_id=error_id, by=ignored_by)
            return True

    @property
    def is_running(self) -> bool:
        """Check if the fixer is running."""
        return self._running

    @property
    def current_fix(self) -> Optional[str]:
        """Get the error ID currently being fixed."""
        return self._current_fix
