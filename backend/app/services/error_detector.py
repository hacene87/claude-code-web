"""
Error Detector Service
======================

Real-time log monitoring and error detection.
Implements FR-ERR-001, FR-ERR-002.
"""

import asyncio
import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.models.error import Error, ErrorSeverity, ErrorCategory, ErrorStatus
from app.services.event_bus import EventBus, EventType, get_event_bus

logger = structlog.get_logger()


# Error pattern definitions (FR-ERR-001)
ERROR_PATTERNS: Dict[str, Tuple[Pattern, ErrorCategory, ErrorSeverity, bool]] = {
    # Python Errors
    "ImportError": (
        re.compile(r"ImportError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.HIGH,
        True  # auto_fixable
    ),
    "ModuleNotFoundError": (
        re.compile(r"ModuleNotFoundError: No module named '(.*)'"),
        ErrorCategory.DEPENDENCY,
        ErrorSeverity.HIGH,
        True
    ),
    "SyntaxError": (
        re.compile(r"SyntaxError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.CRITICAL,
        True
    ),
    "AttributeError": (
        re.compile(r"AttributeError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.HIGH,
        True
    ),
    "TypeError": (
        re.compile(r"TypeError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.HIGH,
        True
    ),
    "ValueError": (
        re.compile(r"ValueError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.MEDIUM,
        True
    ),
    "KeyError": (
        re.compile(r"KeyError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.MEDIUM,
        True
    ),
    "NameError": (
        re.compile(r"NameError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.HIGH,
        True
    ),
    "IndentationError": (
        re.compile(r"IndentationError: (.*)"),
        ErrorCategory.PYTHON,
        ErrorSeverity.CRITICAL,
        True
    ),

    # Database Errors
    "psycopg2.OperationalError": (
        re.compile(r"psycopg2\.OperationalError: (.*)"),
        ErrorCategory.DATABASE,
        ErrorSeverity.CRITICAL,
        False
    ),
    "psycopg2.IntegrityError": (
        re.compile(r"psycopg2\.IntegrityError: (.*)"),
        ErrorCategory.DATABASE,
        ErrorSeverity.HIGH,
        False
    ),
    "psycopg2.ProgrammingError": (
        re.compile(r"psycopg2\.ProgrammingError: (.*)"),
        ErrorCategory.DATABASE,
        ErrorSeverity.HIGH,
        True
    ),

    # Odoo Errors
    "ValidationError": (
        re.compile(r"odoo\.exceptions\.ValidationError: (.*)"),
        ErrorCategory.ODOO,
        ErrorSeverity.MEDIUM,
        True
    ),
    "UserError": (
        re.compile(r"odoo\.exceptions\.UserError: (.*)"),
        ErrorCategory.ODOO,
        ErrorSeverity.LOW,
        False
    ),
    "AccessError": (
        re.compile(r"odoo\.exceptions\.AccessError: (.*)"),
        ErrorCategory.ODOO,
        ErrorSeverity.MEDIUM,
        False
    ),
    "MissingError": (
        re.compile(r"odoo\.exceptions\.MissingError: (.*)"),
        ErrorCategory.ODOO,
        ErrorSeverity.MEDIUM,
        True
    ),
    "ParseError": (
        re.compile(r"odoo\.tools\.convert\.ParseError: (.*)"),
        ErrorCategory.ODOO,
        ErrorSeverity.HIGH,
        True
    ),

    # Asset Errors
    "JavaScriptError": (
        re.compile(r"Error: (.*\.js:\d+)"),
        ErrorCategory.ASSET,
        ErrorSeverity.MEDIUM,
        True
    ),
    "SCSSCompilation": (
        re.compile(r"Error compiling scss: (.*)"),
        ErrorCategory.ASSET,
        ErrorSeverity.MEDIUM,
        True
    ),
    "AssetError": (
        re.compile(r"AssetError: (.*)"),
        ErrorCategory.ASSET,
        ErrorSeverity.MEDIUM,
        True
    ),
}

# Pattern to extract file path and line number from traceback
TRACEBACK_FILE_PATTERN = re.compile(
    r'File "([^"]+)", line (\d+)'
)

# Pattern to detect Odoo module from path
MODULE_PATH_PATTERN = re.compile(
    r'/(?:custom_)?addons/([^/]+)/'
)

# Pattern to detect error start in log
ERROR_START_PATTERN = re.compile(
    r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3} \d+ (ERROR|CRITICAL|WARNING)'
)


@dataclass
class LogLine:
    """Parsed log line."""
    timestamp: datetime
    level: str
    message: str
    raw: str


class ErrorDetectorService:
    """
    Service for detecting and classifying errors from Odoo logs.

    Continuously monitors log files and emits events when errors are detected.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        poll_interval_ms: int = 500
    ):
        self.settings = get_settings()
        self.event_bus = event_bus or get_event_bus()
        self.poll_interval = poll_interval_ms / 1000.0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_position = 0
        self._context_buffer: List[str] = []
        self._context_size = 10

    async def start(self) -> None:
        """Start the log monitoring loop."""
        if self._running:
            logger.warning("error_detector_already_running")
            return

        self._running = True
        self._last_position = self._get_file_size()
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info(
            "error_detector_started",
            log_file=self.settings.odoo.log_file,
            poll_interval=self.poll_interval
        )

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "error_detector", "status": "running"},
            source="error_detector"
        )

    async def stop(self) -> None:
        """Stop the log monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("error_detector_stopped")

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "error_detector", "status": "stopped"},
            source="error_detector"
        )

    def _get_file_size(self) -> int:
        """Get current log file size."""
        log_path = Path(self.settings.odoo.log_file)
        if log_path.exists():
            return log_path.stat().st_size
        return 0

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_log_file()
            except Exception as e:
                logger.error("log_monitoring_error", error=str(e))

            await asyncio.sleep(self.poll_interval)

    async def _check_log_file(self) -> None:
        """Check for new content in the log file."""
        log_path = Path(self.settings.odoo.log_file)
        if not log_path.exists():
            return

        current_size = log_path.stat().st_size

        # Handle log rotation
        if current_size < self._last_position:
            self._last_position = 0

        if current_size == self._last_position:
            return

        # Read new content
        loop = asyncio.get_event_loop()
        new_content = await loop.run_in_executor(
            None,
            self._read_new_content,
            str(log_path)
        )

        if new_content:
            await self._process_log_content(new_content)

    def _read_new_content(self, log_path: str) -> str:
        """Read new content from log file (runs in thread pool)."""
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(self._last_position)
            content = f.read()
            self._last_position = f.tell()
        return content

    async def _process_log_content(self, content: str) -> None:
        """Process new log content and detect errors."""
        lines = content.split("\n")
        error_block: List[str] = []
        in_error_block = False

        for line in lines:
            if not line.strip():
                continue

            # Update context buffer
            self._context_buffer.append(line)
            if len(self._context_buffer) > self._context_size * 2:
                self._context_buffer.pop(0)

            # Check for error start
            if ERROR_START_PATTERN.match(line):
                if in_error_block and error_block:
                    # Process previous error block
                    await self._process_error_block(error_block)
                error_block = [line]
                in_error_block = True
            elif in_error_block:
                # Continue collecting error block
                if line.startswith(" ") or line.startswith("\t") or "Traceback" in line:
                    error_block.append(line)
                else:
                    # End of error block
                    await self._process_error_block(error_block)
                    error_block = []
                    in_error_block = False

        # Process remaining error block
        if in_error_block and error_block:
            await self._process_error_block(error_block)

    async def _process_error_block(self, lines: List[str]) -> None:
        """Process a block of error log lines."""
        if not lines:
            return

        full_text = "\n".join(lines)

        # Try to match error patterns
        for error_type, (pattern, category, severity, auto_fixable) in ERROR_PATTERNS.items():
            match = pattern.search(full_text)
            if match:
                await self._create_error(
                    error_type=error_type,
                    category=category,
                    severity=severity,
                    auto_fixable=auto_fixable,
                    message=match.group(1) if match.groups() else full_text[:500],
                    raw_log=full_text,
                    context_before=self._context_buffer[-self._context_size:]
                )
                return

        # Check for generic error
        if "ERROR" in lines[0] or "CRITICAL" in lines[0]:
            await self._create_error(
                error_type="UnknownError",
                category=ErrorCategory.PYTHON,
                severity=ErrorSeverity.HIGH,
                auto_fixable=True,
                message=lines[0][:500],
                raw_log=full_text,
                context_before=self._context_buffer[-self._context_size:]
            )

    async def _create_error(
        self,
        error_type: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        auto_fixable: bool,
        message: str,
        raw_log: str,
        context_before: List[str]
    ) -> Error:
        """Create an error record in the database."""
        # Extract file path and line number
        file_path, line_number = self._extract_location(raw_log)

        # Extract module name
        module_name = self._extract_module_name(raw_log)

        # Extract stack trace
        stack_trace = self._extract_stack_trace(raw_log)

        async with get_session() as session:
            # Check for duplicate recent errors
            if await self._is_duplicate_error(session, error_type, message, module_name):
                logger.debug(
                    "duplicate_error_skipped",
                    error_type=error_type,
                    module=module_name
                )
                return None

            error = Error(
                id=str(uuid.uuid4()),
                error_type=error_type,
                severity=severity,
                category=category,
                message=message[:2000],
                stack_trace=stack_trace,
                module_name=module_name,
                file_path=file_path,
                line_number=line_number,
                context_before=context_before,
                raw_log=raw_log[:10000],
                status=ErrorStatus.DETECTED,
                auto_fixable=auto_fixable,
                detected_at=datetime.utcnow()
            )

            session.add(error)
            await session.commit()

            logger.info(
                "error_detected",
                error_id=error.id,
                error_type=error_type,
                severity=severity.value,
                module=module_name
            )

            # Emit event
            await self.event_bus.emit(
                EventType.ERROR_DETECTED,
                {
                    "error_id": error.id,
                    "error_type": error_type,
                    "severity": severity.value,
                    "category": category.value,
                    "module": module_name,
                    "auto_fixable": auto_fixable,
                    "message": message[:200],
                },
                source="error_detector"
            )

            return error

    def _extract_location(self, log_text: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract file path and line number from traceback."""
        matches = TRACEBACK_FILE_PATTERN.findall(log_text)
        if matches:
            # Return the last match (usually the actual error location)
            file_path, line_num = matches[-1]
            return file_path, int(line_num)
        return None, None

    def _extract_module_name(self, log_text: str) -> Optional[str]:
        """Extract Odoo module name from log text."""
        match = MODULE_PATH_PATTERN.search(log_text)
        if match:
            return match.group(1)
        return None

    def _extract_stack_trace(self, log_text: str) -> Optional[str]:
        """Extract stack trace from log text."""
        if "Traceback" in log_text:
            # Find traceback section
            lines = log_text.split("\n")
            trace_lines = []
            in_trace = False
            for line in lines:
                if "Traceback" in line:
                    in_trace = True
                if in_trace:
                    trace_lines.append(line)
            return "\n".join(trace_lines)
        return None

    async def _is_duplicate_error(
        self,
        session: AsyncSession,
        error_type: str,
        message: str,
        module_name: Optional[str]
    ) -> bool:
        """Check if this is a duplicate of a recent error."""
        # Look for similar errors in the last minute
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(minutes=1)

        query = select(Error).where(
            Error.error_type == error_type,
            Error.detected_at > cutoff,
            Error.status.in_([ErrorStatus.DETECTED, ErrorStatus.QUEUED, ErrorStatus.FIXING])
        )

        if module_name:
            query = query.where(Error.module_name == module_name)

        result = await session.execute(query)
        existing = result.scalars().first()

        return existing is not None

    async def scan_log_file(
        self,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Error]:
        """
        Scan the entire log file for errors.

        Useful for initial setup or manual scanning.
        """
        log_path = Path(self.settings.odoo.log_file)
        if not log_path.exists():
            return []

        loop = asyncio.get_event_loop()
        content = await loop.run_in_executor(
            None,
            lambda: log_path.read_text(encoding="utf-8", errors="replace")
        )

        # Process content
        errors = []
        original_running = self._running
        self._running = False  # Disable event emission during scan

        try:
            await self._process_log_content(content)
        finally:
            self._running = original_running

        # Get created errors from database
        async with get_session() as session:
            query = select(Error).order_by(Error.detected_at.desc()).limit(limit)
            if since:
                query = query.where(Error.detected_at >= since)
            result = await session.execute(query)
            errors = list(result.scalars().all())

        return errors

    @property
    def is_running(self) -> bool:
        """Check if the detector is running."""
        return self._running
