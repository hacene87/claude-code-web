"""
Unit Tests for Monitor Service
==============================

Tests for FR-MON-001, FR-MON-002.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.services.monitor import (
    MonitorService,
    ChangeType,
    ModuleChangeInfo,
    ChangeEvent,
)


class TestChangeDetection:
    """Tests for FR-MON-002: Module Change Detection."""

    def setup_method(self):
        """Setup for each test."""
        self.service = MonitorService()

    @pytest.mark.parametrize("file_path,expected_module", [
        ("sale_custom/models/sale.py", "sale_custom"),
        ("hr_extension/__manifest__.py", "hr_extension"),
        ("stock_mod/static/src/js/widget.js", "stock_mod"),
        ("purchase_ext/views/purchase_view.xml", "purchase_ext"),
    ])
    def test_extract_module_from_path(self, file_path, expected_module):
        """Correctly extracts module name from file path."""
        result = self.service._extract_module_name(file_path)
        assert result == expected_module

    def test_extract_module_invalid_path(self):
        """Returns None for invalid path."""
        result = self.service._extract_module_name("single_file.py")
        assert result is None

    @pytest.mark.parametrize("file_path,expected_type", [
        ("sale_custom/models/sale.py", ChangeType.PYTHON),
        ("sale_custom/views/sale_view.xml", ChangeType.XML),
        ("sale_custom/static/src/js/widget.js", ChangeType.ASSET),
        ("sale_custom/static/src/css/style.css", ChangeType.ASSET),
        ("sale_custom/static/src/scss/style.scss", ChangeType.ASSET),
        ("sale_custom/__manifest__.py", ChangeType.MANIFEST),
        ("sale_custom/README.md", ChangeType.OTHER),
    ])
    def test_classify_change_type(self, file_path, expected_type):
        """Correctly classifies file change type."""
        result = self.service._classify_change_type(file_path)
        assert result == expected_type


class TestRepositoryPolling:
    """Tests for FR-MON-001: Git Repository Polling."""

    @pytest.fixture
    def mock_repo(self, mocker):
        """Mock git repository."""
        mock = mocker.MagicMock()
        mock.head.commit.hexsha = "new_commit_hash"
        mock.remotes = {"origin": mocker.MagicMock()}
        return mock

    def test_get_changed_files(self, mock_repo):
        """Test getting changed files between commits."""
        mock_repo.git.diff.return_value = "file1.py\nfile2.xml\nfile3.js"

        service = MonitorService()
        result = service._get_changed_files(mock_repo, "old_hash", "new_hash")

        assert len(result) == 3
        assert "file1.py" in result
        assert "file2.xml" in result
        assert "file3.js" in result


class TestModuleChangeInfo:
    """Tests for ModuleChangeInfo dataclass."""

    def test_module_change_info_defaults(self):
        """Test default values."""
        info = ModuleChangeInfo(
            module_name="test_module",
            module_path="/path/to/module"
        )
        assert info.requires_restart is False
        assert info.requires_asset_rebuild is False
        assert len(info.files_changed) == 0

    def test_module_change_info_with_changes(self):
        """Test with changes."""
        info = ModuleChangeInfo(
            module_name="test_module",
            module_path="/path/to/module",
            change_types={ChangeType.PYTHON},
            requires_restart=True,
            files_changed=["models/test.py"]
        )
        assert info.requires_restart is True
        assert ChangeType.PYTHON in info.change_types
