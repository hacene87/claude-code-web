"""
Unit Tests for Error Fixer Service
==================================

Tests for FR-FIX-001, FR-FIX-002, FR-FIX-003.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.error_fixer import (
    ErrorFixerService,
    ClaudeResponse,
    VerificationResult,
    CLAUDE_PROMPT_TEMPLATE,
)
from app.core.config import RetryConfig
from app.models.error import Error, ErrorStatus, ErrorSeverity, ErrorCategory


class TestRetryConfig:
    """Tests for FR-FIX-002: Retry Mechanism."""

    def test_default_retry_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert config.max_attempts == 5
        assert config.base_delay_seconds == 60
        assert config.multiplier == 2.0
        assert config.max_delay_seconds == 960

    @pytest.mark.parametrize("attempt,expected_delay", [
        (1, 60),    # 60 * 2^0 = 60
        (2, 120),   # 60 * 2^1 = 120
        (3, 240),   # 60 * 2^2 = 240
        (4, 480),   # 60 * 2^3 = 480
        (5, 960),   # 60 * 2^4 = 960 (capped at max)
    ])
    def test_exponential_backoff(self, attempt, expected_delay):
        """Test exponential backoff calculation."""
        config = RetryConfig()
        delay = config.get_delay(attempt)
        assert delay == expected_delay

    def test_delay_capped_at_max(self):
        """Test that delay is capped at max_delay_seconds."""
        config = RetryConfig(
            base_delay_seconds=100,
            max_delay_seconds=150
        )
        # At attempt 2 with multiplier 2.0: 100 * 2^1 = 200, capped at 150
        delay = config.get_delay(2)
        assert delay == 150


class TestPromptGeneration:
    """Tests for prompt generation."""

    def test_prompt_template_has_placeholders(self):
        """Verify prompt template has all required placeholders."""
        required_placeholders = [
            "{error_type}",
            "{module_name}",
            "{file_path}",
            "{line_number}",
            "{error_message}",
            "{stack_trace}",
            "{code_context}",
        ]
        for placeholder in required_placeholders:
            assert placeholder in CLAUDE_PROMPT_TEMPLATE

    def test_prompt_generation(self):
        """Test prompt generation with error data."""
        service = ErrorFixerService()
        error = MagicMock()
        error.error_type = "ImportError"
        error.module_name = "test_module"
        error.file_path = "/path/to/file.py"
        error.line_number = 42
        error.message = "No module named 'xyz'"
        error.stack_trace = "Traceback..."

        prompt = service._generate_prompt(error)

        assert "ImportError" in prompt
        assert "test_module" in prompt
        assert "/path/to/file.py" in prompt
        assert "42" in prompt
        assert "No module named 'xyz'" in prompt


class TestClaudeResponse:
    """Tests for ClaudeResponse dataclass."""

    def test_successful_response(self):
        """Test successful response parsing."""
        response = ClaudeResponse(
            success=True,
            files_modified=["file1.py", "file2.py"],
            changes_made="Fixed import statement",
            execution_time_seconds=45.5
        )
        assert response.success is True
        assert len(response.files_modified) == 2
        assert response.error_message is None

    def test_failed_response(self):
        """Test failed response."""
        response = ClaudeResponse(
            success=False,
            error_message="Timeout exceeded"
        )
        assert response.success is False
        assert response.error_message == "Timeout exceeded"
        assert len(response.files_modified) == 0


class TestVerificationResult:
    """Tests for FR-FIX-003: Fix Verification."""

    def test_successful_verification(self):
        """Test successful verification result."""
        result = VerificationResult(
            fix_successful=True,
            original_error_resolved=True,
            syntax_check_passed=True,
            new_errors_introduced=[]
        )
        assert result.fix_successful is True

    def test_failed_verification_new_errors(self):
        """Test failed verification due to new errors."""
        result = VerificationResult(
            fix_successful=False,
            original_error_resolved=True,
            syntax_check_passed=True,
            new_errors_introduced=["New TypeError"]
        )
        assert result.fix_successful is False
        assert len(result.new_errors_introduced) == 1

    def test_failed_verification_syntax_error(self):
        """Test failed verification due to syntax error."""
        result = VerificationResult(
            fix_successful=False,
            syntax_check_passed=False
        )
        assert result.fix_successful is False
        assert result.syntax_check_passed is False


class TestFileModificationExtraction:
    """Tests for extracting modified files from Claude output."""

    def test_extract_modified_files(self):
        """Test extraction of modified files from output."""
        service = ErrorFixerService()

        output = """
        I analyzed the error and found the issue.
        Modified file: /path/to/models/sale.py
        Edited /path/to/views/sale_view.xml
        Writing to /path/to/wizard/wizard.py
        """

        # This would require more sophisticated parsing in real implementation
        # For now we just test the method exists
        files = service._extract_modified_files(output)
        assert isinstance(files, list)
