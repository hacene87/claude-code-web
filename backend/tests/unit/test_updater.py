"""
Unit Tests for Updater Service
==============================

Tests for FR-UPD-001, FR-UPD-002.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.updater import (
    UpdaterService,
    UpdateRequest,
    UpdateResult,
    BackupManifest,
)
from app.models.module_update import UpdateStatus


class TestUpdateRequest:
    """Tests for UpdateRequest dataclass."""

    def test_default_values(self):
        """Test default values."""
        request = UpdateRequest(
            modules=["test_module"],
            database="test_db"
        )
        assert request.backup_before is True
        assert request.force_restart is False
        assert request.correlation_id is None

    def test_custom_values(self):
        """Test custom values."""
        request = UpdateRequest(
            modules=["mod1", "mod2"],
            database="prod_db",
            force_restart=True,
            backup_before=False,
            correlation_id="test-123"
        )
        assert len(request.modules) == 2
        assert request.force_restart is True
        assert request.backup_before is False


class TestUpdateResult:
    """Tests for UpdateResult dataclass."""

    def test_successful_result(self):
        """Test successful update result."""
        result = UpdateResult(
            status=UpdateStatus.SUCCESS,
            modules_updated=["mod1", "mod2"],
            backup_path="/var/backups/odoo/2024-11-23",
            duration_seconds=45.5
        )
        assert result.status == UpdateStatus.SUCCESS
        assert len(result.modules_updated) == 2
        assert len(result.modules_failed) == 0

    def test_failed_result(self):
        """Test failed update result."""
        from app.services.updater import ModuleFailure
        result = UpdateResult(
            status=UpdateStatus.FAILED,
            modules_failed=[
                ModuleFailure(
                    module_name="broken_mod",
                    error_message="Syntax error"
                )
            ],
            error_message="Update failed"
        )
        assert result.status == UpdateStatus.FAILED
        assert len(result.modules_failed) == 1


class TestBackupManifest:
    """Tests for backup manifest."""

    def test_backup_manifest(self):
        """Test backup manifest creation."""
        manifest = BackupManifest(
            timestamp="2024-11-23_10-30-45",
            database="odoo",
            modules=["sale_custom", "hr_ext"],
            backup_path="/var/backups/odoo/2024-11-23_10-30-45",
            filestore_included=True,
            compressed=True
        )
        assert manifest.database == "odoo"
        assert len(manifest.modules) == 2
        assert manifest.compressed is True


class TestUpdaterService:
    """Tests for UpdaterService."""

    def test_is_updating_default(self):
        """Test default is_updating state."""
        service = UpdaterService()
        assert service.is_updating is False

    @pytest.mark.asyncio
    async def test_update_while_updating(self):
        """Test that concurrent updates are rejected."""
        service = UpdaterService()
        service._updating = True

        request = UpdateRequest(
            modules=["test"],
            database="test_db"
        )
        result = await service.update_modules(request)

        assert result.status == UpdateStatus.FAILED
        assert "in progress" in result.error_message
