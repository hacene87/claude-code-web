"""
Application Configuration
=========================

Loads configuration from YAML file and environment variables.
Implements FR-MON-003: Configuration Management
"""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class RepositoryConfig(BaseModel):
    """Configuration for a single Git repository to monitor."""
    path: str = Field(..., description="Local path to repository")
    remote: str = Field(default="origin", description="Remote name")
    branch: str = Field(default="main", description="Branch to monitor")
    enabled: bool = Field(default=True, description="Whether monitoring is active")
    modules_whitelist: List[str] = Field(default_factory=list, description="Only monitor these modules")
    modules_blacklist: List[str] = Field(default_factory=list, description="Ignore these modules")


class GitHubConfig(BaseModel):
    """GitHub/Git configuration."""
    repositories: List[RepositoryConfig] = Field(default_factory=list)
    polling_interval: int = Field(default=60, ge=1, le=300, description="Polling interval in seconds")
    max_concurrent_pulls: int = Field(default=3, ge=1, le=10)


class OdooConfig(BaseModel):
    """Odoo instance configuration."""
    config_path: str = Field(default="/etc/odoo/odoo.conf", description="Path to odoo.conf")
    database: str = Field(..., description="Database name")
    addons_paths: List[str] = Field(default_factory=list, description="Paths to custom addons")
    log_file: str = Field(default="/var/log/odoo/odoo.log", description="Odoo log file path")
    service_name: str = Field(default="odoo", description="Systemd service name")
    bin_path: str = Field(default="/usr/bin/odoo", description="Path to odoo-bin")


class BackupConfig(BaseModel):
    """Backup configuration for safety mechanisms."""
    enabled: bool = Field(default=True)
    retention_days: int = Field(default=7, ge=1, le=90)
    compression: bool = Field(default=True, description="Use gzip compression")
    include_filestore: bool = Field(default=True)
    backup_path: str = Field(default="/var/backups/odoo")


class ClaudeConfig(BaseModel):
    """Claude Code CLI configuration."""
    enabled: bool = Field(default=True)
    timeout_seconds: int = Field(default=300, ge=60, le=600, description="Max time per fix attempt")
    max_turns: int = Field(default=10, ge=1, le=50)
    allowed_tools: List[str] = Field(default=["Edit", "Read", "Bash", "Write"])


class RetryConfig(BaseModel):
    """Retry mechanism configuration (FR-FIX-002)."""
    max_attempts: int = Field(default=5, ge=1, le=10)
    base_delay_seconds: int = Field(default=60, ge=10, le=300)
    multiplier: float = Field(default=2.0, ge=1.0, le=5.0)
    max_delay_seconds: int = Field(default=960, ge=60, le=3600)

    def get_delay(self, attempt: int) -> int:
        """Calculate delay for given attempt number (1-indexed)."""
        delay = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(int(delay), self.max_delay_seconds)


class APIConfig(BaseModel):
    """API server configuration."""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    cors_origins: List[str] = Field(default=["*"])
    rate_limit_per_minute: int = Field(default=100)


class AuthConfig(BaseModel):
    """Authentication configuration."""
    secret_key: str = Field(default="change-me-in-production")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)
    refresh_token_expire_days: int = Field(default=7)


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    file_path: Optional[str] = Field(default="/var/log/oas/oas.log")
    rotation_size_mb: int = Field(default=100)
    retention_days: int = Field(default=30)


class Settings(BaseSettings):
    """Main application settings."""

    # Core settings
    app_name: str = "Odoo Automation Service"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database
    database_url: str = Field(default="sqlite:///./oas.db")

    # Component configurations
    github: GitHubConfig = Field(default_factory=GitHubConfig)
    odoo: OdooConfig = Field(default_factory=lambda: OdooConfig(database="odoo"))
    backup: BackupConfig = Field(default_factory=BackupConfig)
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    class Config:
        env_prefix = "OAS_"
        env_nested_delimiter = "__"


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    Load configuration from YAML file and environment variables.

    Priority (highest to lowest):
    1. Environment variables (OAS_*)
    2. YAML config file
    3. Default values
    """
    config_data = {}

    # Try to load from YAML file
    if config_path:
        path = Path(config_path)
    else:
        # Default config locations
        for default_path in [
            Path("config.yaml"),
            Path("/etc/oas/config.yaml"),
            Path.home() / ".config" / "oas" / "config.yaml",
        ]:
            if default_path.exists():
                path = default_path
                break
        else:
            path = None

    if path and path.exists():
        with open(path) as f:
            config_data = yaml.safe_load(f) or {}

    # Create settings (env vars override YAML)
    return Settings(**config_data)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def reload_settings(config_path: Optional[str] = None) -> Settings:
    """Reload settings from config file (supports runtime reload)."""
    global _settings
    _settings = load_config(config_path)
    return _settings
