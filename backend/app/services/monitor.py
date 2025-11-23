"""
Monitor Service
===============

Handles Git repository polling and change detection.
Implements FR-MON-001, FR-MON-002, FR-MON-003.
"""

import asyncio
import enum
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

import structlog
from git import Repo, GitCommandError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings, RepositoryConfig
from app.core.database import get_session
from app.models.repository import Repository
from app.models.module_update import ModuleUpdate, UpdateStatus
from app.services.event_bus import EventBus, EventType, get_event_bus

logger = structlog.get_logger()


class ChangeType(str, enum.Enum):
    """Type of file change detected."""
    PYTHON = "python"
    XML = "xml"
    ASSET = "asset"  # JS, CSS, SCSS
    MANIFEST = "manifest"
    OTHER = "other"


@dataclass
class ModuleChangeInfo:
    """Information about changes to a single Odoo module."""
    module_name: str
    module_path: str
    change_types: Set[ChangeType] = field(default_factory=set)
    requires_restart: bool = False
    requires_asset_rebuild: bool = False
    files_changed: List[str] = field(default_factory=list)


@dataclass
class ChangeEvent:
    """Event representing detected changes in a repository."""
    repository_path: str
    branch: str
    previous_commit: str
    current_commit: str
    changed_files: List[str]
    changed_modules: List[ModuleChangeInfo]
    detected_at: datetime = field(default_factory=datetime.utcnow)


class MonitorService:
    """
    Service for monitoring Git repositories for changes.

    Polls configured repositories and detects changes to Odoo modules.
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        polling_interval: Optional[int] = None
    ):
        self.settings = get_settings()
        self.event_bus = event_bus or get_event_bus()
        self.polling_interval = polling_interval or self.settings.github.polling_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the monitoring loop."""
        if self._running:
            logger.warning("monitor_already_running")
            return

        self._running = True
        self._task = asyncio.create_task(self._polling_loop())
        logger.info("monitor_started", polling_interval=self.polling_interval)

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "monitor", "status": "running"},
            source="monitor"
        )

    async def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("monitor_stopped")

        await self.event_bus.emit(
            EventType.STATUS_CHANGE,
            {"component": "monitor", "status": "stopped"},
            source="monitor"
        )

    async def _polling_loop(self) -> None:
        """Main polling loop."""
        while self._running:
            try:
                await self._poll_all_repositories()
            except Exception as e:
                logger.error("polling_loop_error", error=str(e))

            await asyncio.sleep(self.polling_interval)

    async def _poll_all_repositories(self) -> None:
        """Poll all configured repositories."""
        async with get_session() as session:
            # Get enabled repositories from database
            result = await session.execute(
                select(Repository).where(Repository.enabled == True)
            )
            repositories = result.scalars().all()

            # Also check configured repositories
            for repo_config in self.settings.github.repositories:
                if repo_config.enabled:
                    await self._ensure_repository_exists(session, repo_config)

            # Poll each repository
            for repo in repositories:
                try:
                    await self._poll_repository(session, repo)
                except Exception as e:
                    logger.error(
                        "repository_poll_error",
                        repository=repo.path,
                        error=str(e)
                    )
                    repo.last_error = str(e)
                    await self.event_bus.emit(
                        EventType.REPO_POLL_ERROR,
                        {"repository": repo.path, "error": str(e)},
                        source="monitor"
                    )

            await session.commit()

    async def _ensure_repository_exists(
        self,
        session: AsyncSession,
        config: RepositoryConfig
    ) -> Repository:
        """Ensure a repository record exists in the database."""
        result = await session.execute(
            select(Repository).where(Repository.path == config.path)
        )
        repo = result.scalar_one_or_none()

        if not repo:
            repo = Repository(
                path=config.path,
                remote=config.remote,
                branch=config.branch,
                enabled=config.enabled
            )
            session.add(repo)
            await session.flush()

        return repo

    async def _poll_repository(
        self,
        session: AsyncSession,
        repo: Repository
    ) -> Optional[ChangeEvent]:
        """
        Poll a single repository for changes.

        Returns ChangeEvent if changes detected, None otherwise.
        """
        repo_path = Path(repo.path)
        if not repo_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {repo.path}")

        # Run git operations in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        change_event = await loop.run_in_executor(
            None,
            self._check_for_changes,
            repo
        )

        if change_event:
            # Update repository state
            repo.last_commit_hash = change_event.current_commit
            repo.last_checked_at = datetime.utcnow()
            repo.last_error = None

            # Create update records for changed modules
            for module_info in change_event.changed_modules:
                update = ModuleUpdate(
                    repository_id=repo.id,
                    module_name=module_info.module_name,
                    previous_commit=change_event.previous_commit,
                    current_commit=change_event.current_commit,
                    files_changed=module_info.files_changed,
                    status=UpdateStatus.PENDING
                )
                session.add(update)

            # Emit event
            await self.event_bus.emit(
                EventType.REPO_CHANGE_DETECTED,
                {
                    "repository": repo.path,
                    "branch": repo.branch,
                    "previous_commit": change_event.previous_commit,
                    "current_commit": change_event.current_commit,
                    "modules": [m.module_name for m in change_event.changed_modules],
                },
                source="monitor"
            )

            logger.info(
                "changes_detected",
                repository=repo.path,
                modules=[m.module_name for m in change_event.changed_modules]
            )
        else:
            repo.last_checked_at = datetime.utcnow()
            repo.last_error = None

        return change_event

    def _check_for_changes(self, repo: Repository) -> Optional[ChangeEvent]:
        """
        Check a repository for changes (runs in thread pool).

        Implements the polling logic from FR-MON-001.
        """
        git_repo = Repo(repo.path)

        # Fetch from remote
        try:
            git_repo.remotes[repo.remote].fetch()
        except GitCommandError as e:
            raise RuntimeError(f"Failed to fetch from remote: {e}")

        # Get current and remote HEAD
        local_head = git_repo.head.commit.hexsha
        remote_ref = f"{repo.remote}/{repo.branch}"

        try:
            remote_head = git_repo.commit(remote_ref).hexsha
        except Exception:
            raise RuntimeError(f"Remote ref not found: {remote_ref}")

        # Check if there are new commits
        if local_head == remote_head:
            return None

        # Get previous commit (what we had before)
        previous_commit = repo.last_commit_hash or local_head

        # Pull changes
        try:
            git_repo.remotes[repo.remote].pull(repo.branch)
        except GitCommandError as e:
            raise RuntimeError(f"Failed to pull changes: {e}")

        # Get new HEAD after pull
        new_head = git_repo.head.commit.hexsha

        # Get changed files
        changed_files = self._get_changed_files(git_repo, previous_commit, new_head)

        # Detect affected modules
        changed_modules = self._detect_module_changes(repo.path, changed_files)

        return ChangeEvent(
            repository_path=repo.path,
            branch=repo.branch,
            previous_commit=previous_commit,
            current_commit=new_head,
            changed_files=changed_files,
            changed_modules=changed_modules
        )

    def _get_changed_files(
        self,
        git_repo: Repo,
        old_commit: str,
        new_commit: str
    ) -> List[str]:
        """Get list of files changed between two commits."""
        try:
            diff = git_repo.git.diff("--name-only", old_commit, new_commit)
            return [f for f in diff.split("\n") if f.strip()]
        except GitCommandError:
            return []

    def _detect_module_changes(
        self,
        repo_path: str,
        changed_files: List[str]
    ) -> List[ModuleChangeInfo]:
        """
        Detect which Odoo modules are affected by file changes.

        Implements FR-MON-002: Module Change Detection.
        """
        modules: dict[str, ModuleChangeInfo] = {}

        for file_path in changed_files:
            module_name = self._extract_module_name(file_path)
            if not module_name:
                continue

            # Check if it's a valid Odoo module
            module_path = Path(repo_path) / module_name
            manifest_path = module_path / "__manifest__.py"
            if not manifest_path.exists():
                continue

            # Get or create module info
            if module_name not in modules:
                modules[module_name] = ModuleChangeInfo(
                    module_name=module_name,
                    module_path=str(module_path)
                )

            module_info = modules[module_name]
            module_info.files_changed.append(file_path)

            # Classify change type
            change_type = self._classify_change_type(file_path)
            module_info.change_types.add(change_type)

            # Determine restart requirements
            if change_type in (ChangeType.PYTHON, ChangeType.MANIFEST):
                module_info.requires_restart = True
            if change_type == ChangeType.ASSET:
                module_info.requires_asset_rebuild = True

        return list(modules.values())

    def _extract_module_name(self, file_path: str) -> Optional[str]:
        """Extract Odoo module name from file path."""
        parts = file_path.split("/")
        if len(parts) < 2:
            return None
        return parts[0]

    def _classify_change_type(self, file_path: str) -> ChangeType:
        """Classify the type of change based on file extension."""
        if file_path.endswith(".py"):
            if "__manifest__.py" in file_path:
                return ChangeType.MANIFEST
            return ChangeType.PYTHON
        elif file_path.endswith(".xml"):
            return ChangeType.XML
        elif file_path.endswith((".js", ".css", ".scss", ".less")):
            return ChangeType.ASSET
        return ChangeType.OTHER

    async def poll_now(self, repository_path: Optional[str] = None) -> List[ChangeEvent]:
        """
        Trigger an immediate poll of repositories.

        Args:
            repository_path: Optional specific repository to poll

        Returns:
            List of change events detected
        """
        changes = []
        async with get_session() as session:
            if repository_path:
                result = await session.execute(
                    select(Repository).where(Repository.path == repository_path)
                )
                repositories = [result.scalar_one_or_none()]
                repositories = [r for r in repositories if r]
            else:
                result = await session.execute(
                    select(Repository).where(Repository.enabled == True)
                )
                repositories = result.scalars().all()

            for repo in repositories:
                try:
                    change_event = await self._poll_repository(session, repo)
                    if change_event:
                        changes.append(change_event)
                except Exception as e:
                    logger.error(
                        "manual_poll_error",
                        repository=repo.path,
                        error=str(e)
                    )

            await session.commit()

        return changes

    @property
    def is_running(self) -> bool:
        """Check if the monitor is currently running."""
        return self._running
