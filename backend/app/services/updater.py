"""
Updater Service
===============

Handles Odoo module updates with backup and rollback capabilities.
Implements FR-UPD-001, FR-UPD-002.
"""

import asyncio
import gzip
import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, BackupConfig
from app.core.database import get_session
from app.models.module_update import ModuleUpdate, UpdateStatus
from app.services.event_bus import EventBus, EventType, get_event_bus

logger = structlog.get_logger()


@dataclass
class UpdateRequest:
    """Request to update Odoo modules."""
    modules: List[str]
    database: str
    force_restart: bool = False
    backup_before: bool = True
    correlation_id: Optional[str] = None


@dataclass
class ModuleFailure:
    """Details of a failed module update."""
    module_name: str
    error_message: str
    exit_code: Optional[int] = None


@dataclass
class UpdateResult:
    """Result of an update operation."""
    status: UpdateStatus
    modules_updated: List[str] = field(default_factory=list)
    modules_failed: List[ModuleFailure] = field(default_factory=list)
    backup_path: Optional[str] = None
    duration_seconds: float = 0.0
    odoo_log_excerpt: str = ""
    error_message: Optional[str] = None


@dataclass
class BackupManifest:
    """Metadata about a backup."""
    timestamp: str
    database: str
    modules: List[str]
    backup_path: str
    filestore_included: bool
    compressed: bool


class UpdaterService:
    """
    Service for updating Odoo modules.

    Handles:
    - Database backup before updates
    - Odoo service management
    - Module update execution
    - Rollback on failure
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.settings = get_settings()
        self.event_bus = event_bus or get_event_bus()
        self._updating = False

    async def update_modules(self, request: UpdateRequest) -> UpdateResult:
        """
        Update one or more Odoo modules.

        Implements FR-UPD-001: Automated Module Updates.
        """
        if self._updating:
            return UpdateResult(
                status=UpdateStatus.FAILED,
                error_message="Another update is in progress"
            )

        self._updating = True
        start_time = datetime.utcnow()
        result = UpdateResult(status=UpdateStatus.IN_PROGRESS)

        try:
            # Emit start event
            await self.event_bus.emit(
                EventType.UPDATE_STARTED,
                {
                    "modules": request.modules,
                    "database": request.database,
                    "backup_enabled": request.backup_before,
                },
                source="updater"
            )

            logger.info(
                "update_started",
                modules=request.modules,
                database=request.database
            )

            # Step 1: Create backup if requested
            if request.backup_before:
                backup_path = await self._create_backup(request.database, request.modules)
                result.backup_path = backup_path
                logger.info("backup_created", path=backup_path)

            # Step 2: Stop Odoo service
            await self._stop_odoo()

            # Step 3: Update each module
            for module in request.modules:
                try:
                    await self._update_single_module(
                        module,
                        request.database
                    )
                    result.modules_updated.append(module)
                    logger.info("module_updated", module=module)
                except Exception as e:
                    result.modules_failed.append(ModuleFailure(
                        module_name=module,
                        error_message=str(e)
                    ))
                    logger.error("module_update_failed", module=module, error=str(e))

            # Step 4: Start Odoo service
            await self._start_odoo()

            # Step 5: Wait for Odoo to be ready
            await self._wait_for_odoo_ready()

            # Step 6: Get log excerpt
            result.odoo_log_excerpt = await self._get_log_excerpt()

            # Step 7: Handle failures
            if result.modules_failed:
                if len(result.modules_failed) == len(request.modules):
                    result.status = UpdateStatus.FAILED
                    # Rollback if all modules failed
                    if result.backup_path:
                        await self._rollback(result.backup_path, request.database)
                        result.status = UpdateStatus.ROLLED_BACK

                    await self.event_bus.emit(
                        EventType.UPDATE_FAILED,
                        {
                            "modules": request.modules,
                            "failed": [f.module_name for f in result.modules_failed],
                            "error": result.modules_failed[0].error_message,
                        },
                        source="updater"
                    )
                else:
                    result.status = UpdateStatus.SUCCESS  # Partial success
            else:
                result.status = UpdateStatus.SUCCESS

            # Calculate duration
            result.duration_seconds = (datetime.utcnow() - start_time).total_seconds()

            # Emit completion event
            if result.status == UpdateStatus.SUCCESS:
                await self.event_bus.emit(
                    EventType.UPDATE_COMPLETED,
                    {
                        "modules": result.modules_updated,
                        "duration": result.duration_seconds,
                    },
                    source="updater"
                )

            logger.info(
                "update_completed",
                status=result.status.value,
                modules_updated=result.modules_updated,
                modules_failed=[f.module_name for f in result.modules_failed],
                duration=result.duration_seconds
            )

        except Exception as e:
            result.status = UpdateStatus.FAILED
            result.error_message = str(e)
            logger.error("update_error", error=str(e))

            await self.event_bus.emit(
                EventType.UPDATE_FAILED,
                {"error": str(e)},
                source="updater"
            )

        finally:
            self._updating = False

        return result

    async def _create_backup(
        self,
        database: str,
        modules: List[str]
    ) -> str:
        """
        Create a database backup.

        Implements FR-UPD-002: Update Safety Mechanisms.
        """
        backup_config = self.settings.backup
        timestamp = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = Path(backup_config.backup_path) / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create database dump
        dump_file = backup_dir / "database.sql"
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._pg_dump,
            database,
            str(dump_file)
        )

        # Compress if configured
        if backup_config.compression:
            compressed_file = f"{dump_file}.gz"
            with open(dump_file, "rb") as f_in:
                with gzip.open(compressed_file, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            dump_file.unlink()

        # Backup filestore if configured
        if backup_config.include_filestore:
            filestore_path = Path(f"/var/lib/odoo/filestore/{database}")
            if filestore_path.exists():
                filestore_backup = backup_dir / "filestore.tar.gz"
                await loop.run_in_executor(
                    None,
                    self._create_tarball,
                    str(filestore_path),
                    str(filestore_backup)
                )

        # Create manifest
        manifest = BackupManifest(
            timestamp=timestamp,
            database=database,
            modules=modules,
            backup_path=str(backup_dir),
            filestore_included=backup_config.include_filestore,
            compressed=backup_config.compression
        )
        manifest_file = backup_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest.__dict__, f, indent=2)

        # Clean old backups
        await self._cleanup_old_backups()

        return str(backup_dir)

    def _pg_dump(self, database: str, output_path: str) -> None:
        """Execute pg_dump (runs in thread pool)."""
        result = subprocess.run(
            ["pg_dump", "-Fp", "-f", output_path, database],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"pg_dump failed: {result.stderr}")

    def _create_tarball(self, source_dir: str, output_path: str) -> None:
        """Create a compressed tarball (runs in thread pool)."""
        subprocess.run(
            ["tar", "-czf", output_path, "-C", str(Path(source_dir).parent), Path(source_dir).name],
            check=True
        )

    async def _stop_odoo(self) -> None:
        """Stop the Odoo service."""
        service_name = self.settings.odoo.service_name
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._run_systemctl,
            "stop",
            service_name
        )
        logger.info("odoo_stopped")

    async def _start_odoo(self) -> None:
        """Start the Odoo service."""
        service_name = self.settings.odoo.service_name
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._run_systemctl,
            "start",
            service_name
        )
        logger.info("odoo_started")

    def _run_systemctl(self, action: str, service: str) -> None:
        """Run systemctl command (runs in thread pool)."""
        result = subprocess.run(
            ["systemctl", action, service],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"systemctl {action} {service} failed: {result.stderr}")

    async def _update_single_module(
        self,
        module: str,
        database: str
    ) -> None:
        """Update a single Odoo module."""
        odoo_config = self.settings.odoo
        loop = asyncio.get_event_loop()

        cmd = [
            odoo_config.bin_path,
            "-c", odoo_config.config_path,
            "-d", database,
            "-u", module,
            "--stop-after-init",
            "--no-http"
        ]

        await loop.run_in_executor(
            None,
            self._run_update_command,
            cmd
        )

    def _run_update_command(self, cmd: List[str]) -> None:
        """Run Odoo update command (runs in thread pool)."""
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if result.returncode != 0:
            raise RuntimeError(f"Module update failed: {result.stderr or result.stdout}")

    async def _wait_for_odoo_ready(self, timeout: int = 60) -> None:
        """Wait for Odoo to be responsive."""
        import httpx

        start_time = datetime.utcnow()
        while (datetime.utcnow() - start_time).total_seconds() < timeout:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        "http://localhost:8069/web/health",
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return
            except Exception:
                pass
            await asyncio.sleep(2)

        logger.warning("odoo_health_check_timeout", timeout=timeout)

    async def _get_log_excerpt(self, lines: int = 100) -> str:
        """Get the last N lines from Odoo log."""
        log_path = Path(self.settings.odoo.log_file)
        if not log_path.exists():
            return ""

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._tail_file,
            str(log_path),
            lines
        )

    def _tail_file(self, path: str, lines: int) -> str:
        """Get last N lines of a file (runs in thread pool)."""
        result = subprocess.run(
            ["tail", "-n", str(lines), path],
            capture_output=True,
            text=True
        )
        return result.stdout

    async def _rollback(self, backup_path: str, database: str) -> None:
        """
        Rollback database to backup state.

        Implements rollback procedure from FR-UPD-002.
        """
        logger.info("rollback_started", backup_path=backup_path)

        # Stop Odoo
        await self._stop_odoo()

        backup_dir = Path(backup_path)
        loop = asyncio.get_event_loop()

        # Find database dump
        dump_file = backup_dir / "database.sql"
        if not dump_file.exists():
            dump_file = backup_dir / "database.sql.gz"
            if dump_file.exists():
                # Decompress
                await loop.run_in_executor(
                    None,
                    self._gunzip,
                    str(dump_file)
                )
                dump_file = backup_dir / "database.sql"

        if not dump_file.exists():
            raise RuntimeError("Backup dump file not found")

        # Restore database
        await loop.run_in_executor(
            None,
            self._pg_restore,
            database,
            str(dump_file)
        )

        # Restore filestore if present
        filestore_backup = backup_dir / "filestore.tar.gz"
        if filestore_backup.exists():
            filestore_path = Path(f"/var/lib/odoo/filestore/{database}")
            if filestore_path.exists():
                shutil.rmtree(filestore_path)
            await loop.run_in_executor(
                None,
                self._extract_tarball,
                str(filestore_backup),
                str(filestore_path.parent)
            )

        # Start Odoo
        await self._start_odoo()

        await self.event_bus.emit(
            EventType.UPDATE_ROLLED_BACK,
            {"backup_path": backup_path, "database": database},
            source="updater"
        )

        logger.info("rollback_completed", backup_path=backup_path)

    def _gunzip(self, path: str) -> None:
        """Decompress gzip file (runs in thread pool)."""
        subprocess.run(["gunzip", path], check=True)

    def _pg_restore(self, database: str, dump_path: str) -> None:
        """Restore database from dump (runs in thread pool)."""
        # Drop and recreate database
        subprocess.run(["dropdb", "--if-exists", database], check=True)
        subprocess.run(["createdb", database], check=True)
        subprocess.run(["psql", "-d", database, "-f", dump_path], check=True)

    def _extract_tarball(self, tarball_path: str, dest_dir: str) -> None:
        """Extract tarball (runs in thread pool)."""
        subprocess.run(
            ["tar", "-xzf", tarball_path, "-C", dest_dir],
            check=True
        )

    async def _cleanup_old_backups(self) -> None:
        """Remove backups older than retention period."""
        backup_config = self.settings.backup
        backup_dir = Path(backup_config.backup_path)

        if not backup_dir.exists():
            return

        cutoff = datetime.utcnow()
        for item in backup_dir.iterdir():
            if not item.is_dir():
                continue

            manifest_file = item / "manifest.json"
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file) as f:
                    manifest = json.load(f)
                backup_time = datetime.strptime(
                    manifest["timestamp"],
                    "%Y-%m-%d_%H-%M-%S"
                )
                age_days = (cutoff - backup_time).days
                if age_days > backup_config.retention_days:
                    shutil.rmtree(item)
                    logger.info("old_backup_removed", path=str(item))
            except Exception as e:
                logger.warning("backup_cleanup_error", path=str(item), error=str(e))

    async def trigger_update(
        self,
        update_id: int
    ) -> UpdateResult:
        """Trigger update for a pending ModuleUpdate record."""
        async with get_session() as session:
            result = await session.execute(
                select(ModuleUpdate).where(ModuleUpdate.id == update_id)
            )
            update = result.scalar_one_or_none()

            if not update:
                return UpdateResult(
                    status=UpdateStatus.FAILED,
                    error_message=f"Update {update_id} not found"
                )

            if update.status != UpdateStatus.PENDING:
                return UpdateResult(
                    status=UpdateStatus.FAILED,
                    error_message=f"Update {update_id} is not pending"
                )

            # Mark as in progress
            update.status = UpdateStatus.IN_PROGRESS
            update.started_at = datetime.utcnow()
            await session.commit()

            # Execute update
            request = UpdateRequest(
                modules=[update.module_name],
                database=self.settings.odoo.database
            )
            result = await self.update_modules(request)

            # Update record
            update.status = result.status
            update.completed_at = datetime.utcnow()
            update.duration_seconds = int(result.duration_seconds)
            if result.error_message:
                update.error_message = result.error_message
            if result.backup_path:
                update.backup_path = result.backup_path
            await session.commit()

            return result

    @property
    def is_updating(self) -> bool:
        """Check if an update is in progress."""
        return self._updating
