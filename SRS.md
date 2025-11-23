# Software Requirements Specification (SRS)
## Odoo 19 Automation Service with AI-Powered Error Resolution

| Document Info | Value |
|---------------|-------|
| Version | 2.0 |
| Date | November 2024 |
| Status | Draft |
| Classification | Internal |

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [Functional Requirements](#3-functional-requirements)
4. [Mobile Application Requirements](#4-mobile-application-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [System Architecture](#6-system-architecture)
7. [Data Requirements](#7-data-requirements)
8. [External Interfaces](#8-external-interfaces)
9. [Testing Requirements](#9-testing-requirements)
10. [Implementation Plan](#10-implementation-plan)
11. [Appendices](#11-appendices)

---

## 1. INTRODUCTION

### 1.1 Purpose
This Software Requirements Specification (SRS) document provides a complete description of the Odoo Automation Service (OAS). It defines functional requirements, non-functional requirements, system interfaces, and constraints for implementation by senior developers.

### 1.2 Scope

**Product Name:** Odoo Automation Service (OAS)

**Product Overview:**
The OAS is an automated monitoring and error resolution system for Odoo 19 ERP instances that:
- Monitors GitHub repositories for custom Odoo module changes via polling
- Automatically updates Odoo modules when changes are detected
- Parses and analyzes Odoo logs for errors and warnings in real-time
- Automatically resolves errors using Claude Code CLI with a 5-attempt retry mechanism
- Provides a mobile application for monitoring, control, and notifications

**Out of Scope:**
- Core Odoo source code modifications
- Odoo.sh deployment management
- Multi-tenant Odoo installations
- Third-party module marketplace integration

### 1.3 Definitions, Acronyms, and Abbreviations

| Term | Definition |
|------|------------|
| OAS | Odoo Automation Service - the system being specified |
| CLI | Command Line Interface |
| API | Application Programming Interface |
| REST | Representational State Transfer |
| WebSocket | Full-duplex communication protocol over TCP |
| JWT | JSON Web Token for authentication |
| CRUD | Create, Read, Update, Delete operations |
| E2E | End-to-End testing |
| CI/CD | Continuous Integration / Continuous Deployment |
| RBAC | Role-Based Access Control |
| Claude Code CLI | Anthropic's AI-powered code assistance command-line tool |
| Polling | Periodic checking for changes at fixed intervals |
| Exponential Backoff | Retry strategy where wait time doubles after each failure |

### 1.4 References

| Document | Version | Description |
|----------|---------|-------------|
| Odoo 19.0 Documentation | 19.0 | Official Odoo developer documentation |
| Claude Code CLI Documentation | Latest | Anthropic CLI tool documentation |
| GitHub REST API | v3 | GitHub API reference |
| React Native Documentation | 0.73+ | Mobile framework documentation |
| FastAPI Documentation | 0.100+ | Python web framework documentation |
| PostgreSQL Documentation | 14+ | Database documentation |

### 1.5 Document Conventions

- **SHALL**: Mandatory requirement - must be implemented
- **SHOULD**: Recommended requirement - implement unless valid reason exists
- **MAY**: Optional requirement - implement if time permits
- **MUST NOT**: Prohibited - explicitly forbidden

---

## 2. OVERALL DESCRIPTION

### 2.1 Product Perspective

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SYSTEM CONTEXT                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   ┌──────────────┐        ┌─────────────────────┐        ┌───────────┐ │
│   │   GitHub     │◄──────▶│                     │◄──────▶│  Odoo 19  │ │
│   │ Repositories │ Poll   │   OAS Backend       │ Update │  Instance │ │
│   └──────────────┘        │                     │        └───────────┘ │
│                           │  ┌───────────────┐  │                      │
│   ┌──────────────┐        │  │   Monitor     │  │        ┌───────────┐ │
│   │ Claude Code  │◄──────▶│  │   Updater     │  │◄──────▶│ PostgreSQL│ │
│   │     CLI      │ Invoke │  │   Error Fixer │  │        │  Database │ │
│   └──────────────┘        │  │   API Server  │  │        └───────────┘ │
│                           │  └───────────────┘  │                      │
│   ┌──────────────┐        │                     │                      │
│   │  Mobile App  │◄──────▶│                     │                      │
│   │ (iOS/Android)│ REST/WS└─────────────────────┘                      │
│   └──────────────┘                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Product Functions

| Function ID | Function Name | Description |
|-------------|---------------|-------------|
| F1 | Repository Monitoring | Poll GitHub repositories every 60 seconds for changes |
| F2 | Module Updates | Automatically update Odoo modules when changes detected |
| F3 | Error Detection | Parse Odoo logs and detect errors/warnings in real-time |
| F4 | Error Resolution | Use Claude Code CLI to automatically fix errors |
| F5 | Retry Management | Retry failed fixes up to 5 times with exponential backoff |
| F6 | Mobile Monitoring | Provide real-time status via mobile application |
| F7 | Remote Control | Allow manual triggers and configuration via mobile app |

### 2.3 User Classes and Characteristics

| User Class | Description | Access Level | Technical Expertise |
|------------|-------------|--------------|---------------------|
| Administrator | Full system control, configuration management | Full | High |
| Developer | Monitor updates, view errors, trigger fixes | Read + Execute | Medium-High |
| Viewer | View-only access to dashboards and logs | Read-only | Low-Medium |

### 2.4 Operating Environment

| Component | Minimum Requirement | Recommended |
|-----------|---------------------|-------------|
| Server OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |
| Python | 3.11 | 3.12 |
| Odoo | 19.0 | 19.0 |
| PostgreSQL | 14 | 16 |
| Node.js | 18 LTS | 20 LTS |
| iOS | 14.0 | 17.0 |
| Android | 10 (API 29) | 14 (API 34) |
| RAM | 4 GB | 8 GB |
| Storage | 50 GB | 100 GB SSD |

### 2.5 Design Constraints

| Constraint ID | Description | Rationale |
|---------------|-------------|-----------|
| DC-001 | MUST use Claude Code CLI, not API | User requirement for CLI-based operation |
| DC-002 | MUST use polling (not webhooks) initially | Simplicity, works with any Git setup |
| DC-003 | MUST support local development environment | Primary use case |
| DC-004 | MUST be implemented in Python | Consistency with Odoo ecosystem |
| DC-005 | Mobile app MUST use React Native | Cross-platform support |

### 2.6 Assumptions and Dependencies

| ID | Assumption/Dependency | Impact if Invalid |
|----|----------------------|-------------------|
| A-001 | Odoo 19 instance is installed and running | System cannot function |
| A-002 | GitHub repositories are accessible via SSH/HTTPS | Cannot detect changes |
| A-003 | Claude Code CLI is installed and authenticated | Cannot auto-fix errors |
| A-004 | PostgreSQL database is accessible | Cannot store state |
| A-005 | Network connectivity is available | Degraded functionality |
| A-006 | Sufficient disk space for backups | Update rollback fails |

---

## 3. FUNCTIONAL REQUIREMENTS

### 3.1 Repository Monitoring Module

#### FR-MON-001: Git Repository Polling

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MON-001 |
| **Title** | Git Repository Polling |
| **Priority** | High |
| **Module** | Monitor |

**Description:**
The system SHALL poll configured GitHub repositories at a configurable interval (default: 60 seconds) to detect new commits.

**Input:**
```python
class RepositoryConfig:
    path: str           # Local path to repository (e.g., "/home/odoo/custom_addons")
    remote: str         # Remote name (default: "origin")
    branch: str         # Branch to monitor (e.g., "main")
    enabled: bool       # Whether monitoring is active
```

**Output:**
```python
class ChangeEvent:
    repository_path: str
    branch: str
    previous_commit: str    # SHA-1 hash (40 chars)
    current_commit: str     # SHA-1 hash (40 chars)
    changed_files: List[str]
    changed_modules: List[str]
    detected_at: datetime
```

**Preconditions:**
1. Repository exists at configured path
2. Repository has valid Git configuration
3. Network access to remote (if checking remote)

**Postconditions:**
1. Change event is created if new commits exist
2. Change event is queued for processing
3. State is persisted to database

**Processing Logic:**
```
1. FOR each configured repository:
   a. Execute: git fetch {remote} {branch}
   b. Get current HEAD: git rev-parse HEAD
   c. Get remote HEAD: git rev-parse {remote}/{branch}
   d. IF local HEAD != remote HEAD:
      i.   Execute: git pull {remote} {branch}
      ii.  Get changed files: git diff --name-only {old_head}..{new_head}
      iii. Identify affected Odoo modules from changed files
      iv.  Create ChangeEvent
      v.   Queue for module update
   e. Update last_checked timestamp
2. Sleep for polling_interval seconds
3. GOTO 1
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-001 | System detects new commit within 60 seconds | Integration test |
| AC-002 | System correctly identifies all changed files | Unit test |
| AC-003 | System correctly maps files to Odoo modules | Unit test |
| AC-004 | System handles network failure gracefully | Integration test |
| AC-005 | System logs all polling activities | Log verification |

---

#### FR-MON-002: Change Detection

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MON-002 |
| **Title** | Module Change Detection |
| **Priority** | High |
| **Module** | Monitor |

**Description:**
The system SHALL identify which Odoo modules are affected by file changes and determine if update is required.

**Input:**
```python
changed_files: List[str]  # e.g., ["sale_custom/models/sale.py", "sale_custom/__manifest__.py"]
```

**Output:**
```python
class ModuleChangeInfo:
    module_name: str           # e.g., "sale_custom"
    module_path: str           # e.g., "/home/odoo/custom_addons/sale_custom"
    change_type: ChangeType    # PYTHON, XML, JS, CSS, MANIFEST, OTHER
    requires_restart: bool     # True if Python files changed
    requires_asset_rebuild: bool  # True if JS/CSS changed
    files_changed: List[str]
```

**Processing Logic:**
```python
def detect_module_changes(changed_files: List[str]) -> List[ModuleChangeInfo]:
    modules = {}
    for file_path in changed_files:
        # Extract module name (first directory component)
        parts = file_path.split('/')
        if len(parts) < 2:
            continue
        module_name = parts[0]

        # Determine change type
        if file_path.endswith('.py'):
            change_type = ChangeType.PYTHON
            requires_restart = True
        elif file_path.endswith('.xml'):
            change_type = ChangeType.XML
            requires_restart = False
        elif file_path.endswith(('.js', '.css', '.scss')):
            change_type = ChangeType.ASSET
            requires_restart = False
            requires_asset_rebuild = True
        elif '__manifest__.py' in file_path:
            change_type = ChangeType.MANIFEST
            requires_restart = True

        # Aggregate by module
        if module_name not in modules:
            modules[module_name] = ModuleChangeInfo(...)
        modules[module_name].files_changed.append(file_path)

    return list(modules.values())
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-006 | Correctly identifies module from file path | Unit test |
| AC-007 | Correctly classifies change type | Unit test |
| AC-008 | Sets requires_restart=True for .py changes | Unit test |
| AC-009 | Sets requires_asset_rebuild=True for .js/.css | Unit test |
| AC-010 | Handles nested module directories | Unit test |

---

#### FR-MON-003: Configuration Management

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MON-003 |
| **Title** | Monitoring Configuration |
| **Priority** | Medium |
| **Module** | Monitor |

**Description:**
The system SHALL support runtime configuration of monitored repositories without requiring restart.

**Configuration Schema (config.yaml):**
```yaml
github:
  repositories:
    - path: "/home/odoo/custom_addons"
      remote: "origin"
      branch: "main"
      enabled: true
      modules_whitelist: []    # Empty = all modules
      modules_blacklist: []    # Modules to ignore
    - path: "/home/odoo/client_modules"
      remote: "origin"
      branch: "develop"
      enabled: true
  polling_interval: 60         # Seconds (1-300)
  max_concurrent_pulls: 3      # Parallel git operations
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-011 | Configuration file is validated on load | Unit test |
| AC-012 | Invalid configuration raises clear error | Unit test |
| AC-013 | Configuration can be reloaded at runtime | Integration test |
| AC-014 | Polling interval enforced within bounds | Unit test |

---

### 3.2 Module Update Module

#### FR-UPD-001: Automated Module Updates

| Attribute | Value |
|-----------|-------|
| **ID** | FR-UPD-001 |
| **Title** | Odoo Module Update Execution |
| **Priority** | High |
| **Module** | Updater |

**Description:**
The system SHALL automatically update Odoo modules when changes are detected, using the appropriate update mechanism.

**Input:**
```python
class UpdateRequest:
    modules: List[str]          # Module names to update
    database: str               # Target database name
    force_restart: bool         # Force Odoo restart
    backup_before: bool         # Create backup first (default: True)
    correlation_id: str         # For tracing
```

**Output:**
```python
class UpdateResult:
    status: UpdateStatus        # SUCCESS, PARTIAL, FAILED
    modules_updated: List[str]
    modules_failed: List[ModuleFailure]
    backup_path: Optional[str]
    duration_seconds: float
    odoo_log_excerpt: str       # Last 100 lines of Odoo log
    error_message: Optional[str]
```

**Processing Logic:**
```
1. VALIDATE input parameters
2. IF backup_before:
   a. Create database backup: pg_dump {database} > backup_{timestamp}.sql
   b. Store backup_path
3. STOP Odoo service (systemctl stop odoo OR kill process)
4. FOR each module in modules:
   a. Execute: click-odoo-update -c {odoo_conf} -d {database} --update {module}
   b. OR: ./odoo-bin -c {odoo_conf} -d {database} -u {module} --stop-after-init
   c. Capture stdout/stderr
   d. IF exit_code != 0:
      i.  Log failure
      ii. Add to modules_failed
5. START Odoo service
6. WAIT for Odoo to be responsive (health check)
7. IF any modules_failed AND backup exists:
   a. ROLLBACK: psql {database} < backup_{timestamp}.sql
   b. RESTART Odoo
8. RETURN UpdateResult
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-015 | Database backup created before update | Integration test |
| AC-016 | All specified modules are updated | Integration test |
| AC-017 | Odoo service stopped during update | Integration test |
| AC-018 | Odoo service restarted after update | Integration test |
| AC-019 | Rollback executed on failure | Integration test |
| AC-020 | Update duration is recorded | Unit test |

---

#### FR-UPD-002: Update Safety Mechanisms

| Attribute | Value |
|-----------|-------|
| **ID** | FR-UPD-002 |
| **Title** | Update Safety and Rollback |
| **Priority** | Critical |
| **Module** | Updater |

**Description:**
The system SHALL implement safety mechanisms to prevent data loss and ensure recoverability.

**Backup Strategy:**
```python
class BackupConfig:
    enabled: bool = True
    retention_days: int = 7
    compression: bool = True        # Use gzip
    include_filestore: bool = True  # Odoo filestore
    backup_path: str = "/var/backups/odoo"
```

**Backup Format:**
```
/var/backups/odoo/
├── 2024-11-23_10-30-45/
│   ├── database.sql.gz           # PostgreSQL dump
│   ├── filestore.tar.gz          # Odoo filestore (optional)
│   ├── manifest.json             # Backup metadata
│   └── modules_state.json        # Module versions before update
```

**Rollback Procedure:**
```python
def rollback_update(backup_path: str, database: str) -> RollbackResult:
    """
    Rollback database to previous state.

    Steps:
    1. Stop Odoo service
    2. Drop current database
    3. Restore from backup
    4. Restore filestore if included
    5. Start Odoo service
    6. Verify database integrity
    """
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-021 | Backup completes within 5 minutes for 1GB DB | Performance test |
| AC-022 | Backup is verifiable (can be restored) | Integration test |
| AC-023 | Old backups are deleted per retention policy | Unit test |
| AC-024 | Rollback restores exact previous state | Integration test |
| AC-025 | Filestore backup includes all attachments | Integration test |

---

### 3.3 Error Detection Module

#### FR-ERR-001: Real-Time Log Monitoring

| Attribute | Value |
|-----------|-------|
| **ID** | FR-ERR-001 |
| **Title** | Odoo Log File Monitoring |
| **Priority** | High |
| **Module** | ErrorDetector |

**Description:**
The system SHALL continuously monitor Odoo log files and detect errors/warnings in real-time.

**Input:**
```python
class LogMonitorConfig:
    log_file_path: str              # e.g., "/var/log/odoo/odoo.log"
    start_from_datetime: datetime   # Ignore logs before this time
    poll_interval_ms: int = 500     # Check for new lines
    error_patterns: List[str]       # Regex patterns to match
    warning_patterns: List[str]
```

**Output:**
```python
class DetectedError:
    id: str                         # UUID
    timestamp: datetime
    level: LogLevel                 # ERROR, WARNING, CRITICAL
    error_type: str                 # e.g., "ImportError", "ValidationError"
    message: str                    # Error message
    stack_trace: Optional[str]      # Full traceback
    module_name: Optional[str]      # Affected module
    file_path: Optional[str]        # Source file
    line_number: Optional[int]      # Line in source
    context_before: List[str]       # 10 lines before error
    context_after: List[str]        # 10 lines after error
    raw_log_lines: List[str]        # Original log entries
```

**Error Pattern Definitions:**
```python
ERROR_PATTERNS = {
    # Python Errors
    "ImportError": r"ImportError: (.*)",
    "ModuleNotFoundError": r"ModuleNotFoundError: No module named '(.*)'",
    "SyntaxError": r"SyntaxError: (.*)",
    "AttributeError": r"AttributeError: (.*)",
    "TypeError": r"TypeError: (.*)",
    "ValueError": r"ValueError: (.*)",
    "KeyError": r"KeyError: (.*)",

    # Database Errors
    "psycopg2.OperationalError": r"psycopg2\.OperationalError: (.*)",
    "psycopg2.IntegrityError": r"psycopg2\.IntegrityError: (.*)",
    "psycopg2.ProgrammingError": r"psycopg2\.ProgrammingError: (.*)",

    # Odoo Errors
    "odoo.exceptions.ValidationError": r"odoo\.exceptions\.ValidationError: (.*)",
    "odoo.exceptions.UserError": r"odoo\.exceptions\.UserError: (.*)",
    "odoo.exceptions.AccessError": r"odoo\.exceptions\.AccessError: (.*)",
    "odoo.exceptions.MissingError": r"odoo\.exceptions\.MissingError: (.*)",
    "ParseError": r"odoo\.tools\.convert\.ParseError: (.*)",

    # Asset Errors
    "JavaScript Error": r"Error: (.*\.js:\d+)",
    "SCSS Compilation": r"Error compiling scss: (.*)",
    "Asset Bundling": r"AssetError: (.*)",
}
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-026 | Detects error within 1 second of log write | Integration test |
| AC-027 | Correctly extracts stack trace | Unit test |
| AC-028 | Identifies affected module from traceback | Unit test |
| AC-029 | Captures ±10 lines of context | Unit test |
| AC-030 | Handles multi-line error messages | Unit test |
| AC-031 | Does not miss errors during high log volume | Performance test |

---

#### FR-ERR-002: Error Classification

| Attribute | Value |
|-----------|-------|
| **ID** | FR-ERR-002 |
| **Title** | Error Type Classification |
| **Priority** | High |
| **Module** | ErrorDetector |

**Description:**
The system SHALL classify detected errors by type, severity, and affected component.

**Classification Schema:**
```python
class ErrorClassification:
    category: ErrorCategory     # PYTHON, DATABASE, ODOO, ASSET, DEPENDENCY
    severity: Severity          # CRITICAL, HIGH, MEDIUM, LOW
    is_auto_fixable: bool       # Can be fixed by Claude Code
    requires_restart: bool      # Needs Odoo restart after fix
    affected_component: str     # Module or system component
    suggested_action: str       # Human-readable suggestion
```

**Classification Rules:**
| Error Type | Category | Severity | Auto-Fixable | Requires Restart |
|------------|----------|----------|--------------|------------------|
| ImportError | PYTHON | HIGH | Yes | Yes |
| SyntaxError | PYTHON | CRITICAL | Yes | Yes |
| ModuleNotFoundError | DEPENDENCY | HIGH | Yes | Yes |
| psycopg2.OperationalError | DATABASE | CRITICAL | No | No |
| psycopg2.IntegrityError | DATABASE | HIGH | Maybe | No |
| ValidationError | ODOO | MEDIUM | Yes | No |
| UserError | ODOO | LOW | No | No |
| ParseError (XML) | ODOO | HIGH | Yes | Yes |
| JavaScript Error | ASSET | MEDIUM | Yes | No |
| SCSS Compilation | ASSET | MEDIUM | Yes | No |

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-032 | All error types are correctly classified | Unit test |
| AC-033 | Severity is correctly assigned | Unit test |
| AC-034 | Auto-fixable flag is accurate | Manual verification |
| AC-035 | Unknown errors classified as HIGH/PYTHON | Unit test |

---

### 3.4 Error Resolution Module

#### FR-FIX-001: Claude Code CLI Integration

| Attribute | Value |
|-----------|-------|
| **ID** | FR-FIX-001 |
| **Title** | Claude Code CLI Error Resolution |
| **Priority** | Critical |
| **Module** | ErrorFixer |

**Description:**
The system SHALL invoke Claude Code CLI to analyze errors and generate fixes.

**CLI Invocation:**
```python
def invoke_claude_code(error: DetectedError, workspace_path: str) -> ClaudeResponse:
    """
    Invoke Claude Code CLI to fix an error.

    Command:
    claude --print --dangerously-skip-permissions \
           --allowedTools "Edit,Read,Bash,Write" \
           -p "{prompt}" \
           --max-turns 10

    Environment:
    - Working directory: {workspace_path}
    - Timeout: 300 seconds (5 minutes)
    """
```

**Prompt Template:**
```python
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
```

**Output:**
```python
class ClaudeResponse:
    success: bool
    files_modified: List[str]
    changes_made: str           # Description of changes
    reasoning: str              # Claude's analysis
    execution_time_seconds: float
    tokens_used: int
    raw_output: str
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-036 | Claude Code CLI invoked with correct parameters | Integration test |
| AC-037 | Prompt includes all error context | Unit test |
| AC-038 | Response parsed correctly | Unit test |
| AC-039 | Timeout enforced (5 minutes max) | Integration test |
| AC-040 | Files modified are tracked | Integration test |

---

#### FR-FIX-002: Retry Mechanism with Exponential Backoff

| Attribute | Value |
|-----------|-------|
| **ID** | FR-FIX-002 |
| **Title** | Error Fix Retry Mechanism |
| **Priority** | Critical |
| **Module** | ErrorFixer |

**Description:**
The system SHALL retry failed fix attempts up to 5 times with exponential backoff.

**Retry Configuration:**
```python
class RetryConfig:
    max_attempts: int = 5
    base_delay_seconds: int = 60      # 1 minute
    multiplier: float = 2.0           # Exponential factor
    max_delay_seconds: int = 960      # 16 minutes cap

    def get_delay(self, attempt: int) -> int:
        """Calculate delay for given attempt number (1-indexed)."""
        delay = self.base_delay_seconds * (self.multiplier ** (attempt - 1))
        return min(int(delay), self.max_delay_seconds)
```

**Retry Schedule:**
| Attempt | Delay Before | Cumulative Wait |
|---------|--------------|-----------------|
| 1 | 0 | 0 |
| 2 | 60s (1 min) | 1 min |
| 3 | 120s (2 min) | 3 min |
| 4 | 240s (4 min) | 7 min |
| 5 | 480s (8 min) | 15 min |
| Escalate | - | - |

**State Machine:**
```
                    ┌─────────────────┐
                    │   ERROR_QUEUED  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
             ┌─────▶│  FIXING (n/5)   │◀─────┐
             │      └────────┬────────┘      │
             │               │               │
             │      ┌────────┴────────┐      │
             │      ▼                 ▼      │
      ┌──────┴───────┐        ┌─────────────┴┐
      │ FIX_SUCCESS  │        │  FIX_FAILED  │
      └──────────────┘        └──────┬───────┘
                                     │
                              attempt < 5?
                              ┌──────┴──────┐
                              │ Yes         │ No
                              ▼             ▼
                       ┌───────────┐  ┌───────────┐
                       │  WAITING  │  │ ESCALATED │
                       │ (backoff) │  │           │
                       └───────────┘  └───────────┘
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-041 | Maximum 5 attempts per error | Unit test |
| AC-042 | Correct delay between attempts | Unit test |
| AC-043 | Error escalated after 5 failures | Integration test |
| AC-044 | Each attempt is logged with details | Log verification |
| AC-045 | Attempt counter persists across restarts | Integration test |

---

#### FR-FIX-003: Fix Verification

| Attribute | Value |
|-----------|-------|
| **ID** | FR-FIX-003 |
| **Title** | Post-Fix Verification |
| **Priority** | High |
| **Module** | ErrorFixer |

**Description:**
The system SHALL verify that a fix resolved the error and did not introduce new errors.

**Verification Steps:**
```python
def verify_fix(error: DetectedError, fix_result: ClaudeResponse) -> VerificationResult:
    """
    Verify that the fix resolved the error.

    Steps:
    1. Syntax check modified files (python -m py_compile)
    2. Restart Odoo if required
    3. Wait for Odoo to stabilize (30 seconds)
    4. Check logs for same error (should not reappear)
    5. Check logs for new errors (should not appear)
    6. Run module tests if available
    """
```

**Output:**
```python
class VerificationResult:
    fix_successful: bool
    original_error_resolved: bool
    new_errors_introduced: List[DetectedError]
    syntax_check_passed: bool
    tests_passed: Optional[bool]        # None if no tests
    verification_duration_seconds: float
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-046 | Syntax errors detected before restart | Unit test |
| AC-047 | Original error verified as resolved | Integration test |
| AC-048 | New errors trigger fix rollback | Integration test |
| AC-049 | Module tests executed if available | Integration test |

---

### 3.5 API Server Module

#### FR-API-001: REST API Endpoints

| Attribute | Value |
|-----------|-------|
| **ID** | FR-API-001 |
| **Title** | REST API Implementation |
| **Priority** | Medium |
| **Module** | APIServer |

**Description:**
The system SHALL provide REST API endpoints for status, control, and configuration.

**API Specification:**

##### Authentication
```
POST /api/v1/auth/login
Request:
{
    "username": "string",
    "password": "string"
}
Response:
{
    "access_token": "string (JWT)",
    "refresh_token": "string",
    "expires_in": 3600
}
```

##### System Status
```
GET /api/v1/status
Headers: Authorization: Bearer {token}
Response:
{
    "status": "running|stopped|error",
    "uptime_seconds": 86400,
    "last_poll": "2024-11-23T10:30:00Z",
    "active_errors": 2,
    "pending_updates": 1,
    "components": {
        "monitor": "running",
        "updater": "idle",
        "error_fixer": "fixing",
        "odoo": "running"
    }
}
```

##### Module Updates
```
GET /api/v1/updates?limit=50&offset=0
Response:
{
    "total": 150,
    "items": [
        {
            "id": 1,
            "module_name": "sale_custom",
            "status": "success",
            "commit_hash": "abc123",
            "updated_at": "2024-11-23T10:30:00Z",
            "duration_seconds": 45
        }
    ]
}

POST /api/v1/updates/trigger
Request:
{
    "modules": ["sale_custom", "hr_extension"],
    "force": false
}
Response:
{
    "job_id": "uuid",
    "status": "queued"
}
```

##### Errors
```
GET /api/v1/errors?status=active&limit=50
Response:
{
    "total": 5,
    "items": [
        {
            "id": "uuid",
            "error_type": "ImportError",
            "module_name": "sale_custom",
            "message": "No module named 'missing_dep'",
            "detected_at": "2024-11-23T10:30:00Z",
            "status": "fixing",
            "attempts": 2
        }
    ]
}

POST /api/v1/errors/{id}/retry
Response:
{
    "status": "queued",
    "attempt_number": 3
}

POST /api/v1/errors/{id}/ignore
Response:
{
    "status": "ignored"
}
```

##### Configuration
```
GET /api/v1/config
Response:
{
    "polling_interval": 60,
    "max_retry_attempts": 5,
    "automation_enabled": true,
    "repositories": [...]
}

PUT /api/v1/config
Request:
{
    "polling_interval": 120,
    "automation_enabled": true
}
Response:
{
    "status": "updated",
    "restart_required": false
}
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-050 | All endpoints require authentication | API test |
| AC-051 | Invalid token returns 401 | API test |
| AC-052 | Endpoints return correct HTTP status codes | API test |
| AC-053 | Response format matches specification | API test |
| AC-054 | Rate limiting enforced (100 req/min) | Load test |

---

#### FR-API-002: WebSocket Real-Time Updates

| Attribute | Value |
|-----------|-------|
| **ID** | FR-API-002 |
| **Title** | WebSocket Event Streaming |
| **Priority** | Medium |
| **Module** | APIServer |

**Description:**
The system SHALL provide WebSocket connections for real-time event streaming.

**Connection:**
```
WebSocket URL: wss://{host}:{port}/ws
Headers: Authorization: Bearer {token}
```

**Event Types:**
```python
class WebSocketEvent:
    event_type: str         # Event name
    timestamp: datetime
    payload: dict           # Event-specific data

# Event Types:
EVENT_TYPES = {
    "status_change": {
        "old_status": "running",
        "new_status": "updating",
        "component": "updater"
    },
    "new_error": {
        "error_id": "uuid",
        "error_type": "ImportError",
        "module": "sale_custom",
        "severity": "HIGH"
    },
    "fix_progress": {
        "error_id": "uuid",
        "attempt": 2,
        "status": "in_progress|success|failed"
    },
    "update_complete": {
        "module": "sale_custom",
        "status": "success",
        "duration": 45
    },
    "heartbeat": {
        "uptime": 86400
    }
}
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-055 | WebSocket connects with valid token | Integration test |
| AC-056 | Events received within 1 second | Performance test |
| AC-057 | Automatic reconnection on disconnect | Integration test |
| AC-058 | Heartbeat every 30 seconds | Integration test |

---

## 4. MOBILE APPLICATION REQUIREMENTS

### 4.1 Overview

| Attribute | Value |
|-----------|-------|
| **Platform** | iOS 14+, Android 10+ |
| **Framework** | React Native 0.73+ |
| **State Management** | Redux Toolkit |
| **Navigation** | React Navigation 6 |
| **API Client** | Axios + React Query |
| **WebSocket** | Socket.io Client |
| **Push Notifications** | Firebase Cloud Messaging |

### 4.2 Application Architecture

```
mobile/
├── src/
│   ├── app/
│   │   ├── App.tsx                 # Root component
│   │   ├── navigation/
│   │   │   ├── RootNavigator.tsx
│   │   │   ├── AuthNavigator.tsx
│   │   │   └── MainNavigator.tsx
│   │   └── store/
│   │       ├── index.ts
│   │       ├── slices/
│   │       │   ├── authSlice.ts
│   │       │   ├── statusSlice.ts
│   │       │   ├── updatesSlice.ts
│   │       │   └── errorsSlice.ts
│   │       └── middleware/
│   │           └── websocketMiddleware.ts
│   ├── screens/
│   │   ├── auth/
│   │   │   ├── LoginScreen.tsx
│   │   │   └── BiometricScreen.tsx
│   │   ├── dashboard/
│   │   │   └── DashboardScreen.tsx
│   │   ├── updates/
│   │   │   ├── UpdatesListScreen.tsx
│   │   │   └── UpdateDetailScreen.tsx
│   │   ├── errors/
│   │   │   ├── ErrorsListScreen.tsx
│   │   │   └── ErrorDetailScreen.tsx
│   │   ├── logs/
│   │   │   └── LogsScreen.tsx
│   │   └── settings/
│   │       └── SettingsScreen.tsx
│   ├── components/
│   │   ├── common/
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── StatusBadge.tsx
│   │   ├── dashboard/
│   │   │   ├── StatusCard.tsx
│   │   │   ├── RecentUpdates.tsx
│   │   │   ├── ActiveErrors.tsx
│   │   │   └── SystemMetrics.tsx
│   │   └── errors/
│   │       ├── ErrorCard.tsx
│   │       ├── StackTraceViewer.tsx
│   │       └── FixProgressBar.tsx
│   ├── services/
│   │   ├── api.ts                  # Axios instance
│   │   ├── auth.service.ts
│   │   ├── status.service.ts
│   │   ├── updates.service.ts
│   │   ├── errors.service.ts
│   │   └── websocket.service.ts
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useStatus.ts
│   │   ├── useWebSocket.ts
│   │   └── useNotifications.ts
│   ├── utils/
│   │   ├── storage.ts              # AsyncStorage wrapper
│   │   ├── formatters.ts
│   │   └── validators.ts
│   └── types/
│       ├── api.types.ts
│       ├── navigation.types.ts
│       └── store.types.ts
├── ios/
├── android/
├── package.json
└── tsconfig.json
```

### 4.3 Screen Specifications

#### FR-MOB-001: Login Screen

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-001 |
| **Title** | User Authentication Screen |
| **Priority** | High |

**Wireframe:**
```
┌─────────────────────────────────┐
│                                 │
│         [Logo/Icon]             │
│                                 │
│    Odoo Automation Service      │
│                                 │
│  ┌───────────────────────────┐  │
│  │ Server URL                │  │
│  │ https://api.example.com   │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │ Username                  │  │
│  │ admin                     │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │ Password                  │  │
│  │ ••••••••                  │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │         LOGIN             │  │
│  └───────────────────────────┘  │
│                                 │
│     [Use Biometric Login]       │
│                                 │
└─────────────────────────────────┘
```

**Functional Requirements:**
1. User SHALL enter server URL, username, and password
2. App SHALL validate URL format before submission
3. App SHALL display loading indicator during authentication
4. App SHALL display error message on authentication failure
5. App SHALL store JWT token securely in Keychain (iOS) / Keystore (Android)
6. App SHALL support biometric authentication (Face ID / Touch ID / Fingerprint)
7. App SHALL remember server URL between sessions

**Input Validation:**
```typescript
interface LoginFormValidation {
    serverUrl: {
        required: true;
        pattern: /^https?:\/\/.+/;
        errorMessage: "Valid URL required (https://...)";
    };
    username: {
        required: true;
        minLength: 3;
        errorMessage: "Username required (min 3 characters)";
    };
    password: {
        required: true;
        minLength: 6;
        errorMessage: "Password required (min 6 characters)";
    };
}
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-001 | Login with valid credentials succeeds | E2E test |
| AC-MOB-002 | Invalid credentials show error message | E2E test |
| AC-MOB-003 | Token stored in secure storage | Unit test |
| AC-MOB-004 | Biometric login works after initial login | Manual test |
| AC-MOB-005 | Form validation prevents invalid input | Unit test |

---

#### FR-MOB-002: Dashboard Screen

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-002 |
| **Title** | Main Dashboard Screen |
| **Priority** | High |

**Wireframe:**
```
┌─────────────────────────────────┐
│ ≡  OAS Dashboard          [⚙]  │
├─────────────────────────────────┤
│                                 │
│  ┌───────────────────────────┐  │
│  │ SYSTEM STATUS             │  │
│  │                           │  │
│  │    ● Running              │  │
│  │    Uptime: 2d 4h 30m      │  │
│  │    Last Check: 30s ago    │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌─────────┐  ┌─────────────┐   │
│  │Updates  │  │  Errors     │   │
│  │   12    │  │     2       │   │
│  │ today   │  │   active    │   │
│  └─────────┘  └─────────────┘   │
│                                 │
│  RECENT UPDATES                 │
│  ┌───────────────────────────┐  │
│  │ ✓ sale_custom    10:30   │  │
│  │ ✓ hr_extension   10:25   │  │
│  │ ⚠ stock_mod      10:20   │  │
│  └───────────────────────────┘  │
│                                 │
│  ACTIVE ERRORS                  │
│  ┌───────────────────────────┐  │
│  │ ⚠ ImportError             │  │
│  │   sale_custom | Fixing... │  │
│  │   Attempt 2/5             │  │
│  ├───────────────────────────┤  │
│  │ ⚠ SyntaxError             │  │
│  │   hr_module | Queued      │  │
│  └───────────────────────────┘  │
│                                 │
├─────────────────────────────────┤
│ [Dashboard] [Updates] [Errors]  │
└─────────────────────────────────┘
```

**Data Requirements:**
```typescript
interface DashboardData {
    systemStatus: {
        status: 'running' | 'stopped' | 'error';
        uptimeSeconds: number;
        lastCheckAt: string;  // ISO 8601
    };
    metrics: {
        updatesToday: number;
        activeErrors: number;
        fixesCompleted: number;
        successRate: number;  // 0-100
    };
    recentUpdates: UpdateSummary[];  // Last 5
    activeErrors: ErrorSummary[];    // Up to 10
}
```

**Refresh Behavior:**
- Auto-refresh every 10 seconds via WebSocket
- Pull-to-refresh for manual update
- Visual indicator when data is stale (>30 seconds)

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-006 | Dashboard loads within 3 seconds | Performance test |
| AC-MOB-007 | Real-time updates via WebSocket work | Integration test |
| AC-MOB-008 | Pull-to-refresh updates all data | E2E test |
| AC-MOB-009 | Status indicator reflects actual state | Integration test |
| AC-MOB-010 | Navigation to details works correctly | E2E test |

---

#### FR-MOB-003: Updates List Screen

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-003 |
| **Title** | Module Updates History Screen |
| **Priority** | Medium |

**Wireframe:**
```
┌─────────────────────────────────┐
│ ←  Module Updates        [🔍]  │
├─────────────────────────────────┤
│ Filter: [All ▼] [Today ▼]       │
├─────────────────────────────────┤
│                                 │
│  November 23, 2024              │
│  ┌───────────────────────────┐  │
│  │ ✓ sale_custom             │  │
│  │   10:30 AM | 45s | abc123 │  │
│  ├───────────────────────────┤  │
│  │ ✓ hr_extension            │  │
│  │   10:25 AM | 32s | def456 │  │
│  ├───────────────────────────┤  │
│  │ ✗ stock_mod               │  │
│  │   10:20 AM | Failed       │  │
│  │   [View Error] [Retry]    │  │
│  └───────────────────────────┘  │
│                                 │
│  November 22, 2024              │
│  ┌───────────────────────────┐  │
│  │ ✓ purchase_custom         │  │
│  │   4:30 PM | 28s | 789xyz  │  │
│  └───────────────────────────┘  │
│                                 │
│        [Load More]              │
│                                 │
├─────────────────────────────────┤
│ [Dashboard] [Updates] [Errors]  │
└─────────────────────────────────┘
```

**Features:**
1. Infinite scroll pagination (50 items per page)
2. Filter by status (All, Success, Failed, Pending)
3. Filter by date range
4. Search by module name
5. Tap to view update details
6. Retry failed updates

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-011 | List loads first page within 2 seconds | Performance test |
| AC-MOB-012 | Infinite scroll loads next page | E2E test |
| AC-MOB-013 | Filters work correctly | E2E test |
| AC-MOB-014 | Retry button triggers update | Integration test |
| AC-MOB-015 | Search finds matching modules | E2E test |

---

#### FR-MOB-004: Error Detail Screen

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-004 |
| **Title** | Error Details and Fix Progress Screen |
| **Priority** | High |

**Wireframe:**
```
┌─────────────────────────────────┐
│ ←  Error Details               │
├─────────────────────────────────┤
│                                 │
│  ⚠ ImportError                  │
│  ─────────────────────────────  │
│  Module: sale_custom            │
│  File: models/sale.py           │
│  Line: 42                       │
│  Detected: 10:30 AM             │
│                                 │
│  STATUS: Fixing (Attempt 2/5)   │
│  ████████░░░░░░░░░░░░  40%     │
│                                 │
│  ┌───────────────────────────┐  │
│  │ ERROR MESSAGE             │  │
│  │                           │  │
│  │ No module named           │  │
│  │ 'missing_dependency'      │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌───────────────────────────┐  │
│  │ STACK TRACE          [⎘] │  │
│  │                           │  │
│  │ Traceback (most recent):  │  │
│  │ File "/odoo/addons/..."   │  │
│  │   line 42, in <module>    │  │
│  │     from missing_dep...   │  │
│  │ ImportError: No module... │  │
│  └───────────────────────────┘  │
│                                 │
│  FIX HISTORY                    │
│  ┌───────────────────────────┐  │
│  │ Attempt 1 - 10:31 AM      │  │
│  │ ✗ Failed: Syntax error    │  │
│  ├───────────────────────────┤  │
│  │ Attempt 2 - 10:33 AM      │  │
│  │ ⟳ In Progress...          │  │
│  └───────────────────────────┘  │
│                                 │
│  ┌─────────┐  ┌─────────────┐   │
│  │  Retry  │  │   Ignore    │   │
│  └─────────┘  └─────────────┘   │
│                                 │
└─────────────────────────────────┘
```

**Features:**
1. Full error details display
2. Expandable stack trace with copy function
3. Real-time fix progress updates
4. Fix attempt history
5. Manual retry button
6. Ignore/dismiss error option
7. Syntax highlighted code context

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-016 | All error details displayed correctly | E2E test |
| AC-MOB-017 | Stack trace is copyable | Manual test |
| AC-MOB-018 | Progress updates in real-time | Integration test |
| AC-MOB-019 | Retry triggers new fix attempt | Integration test |
| AC-MOB-020 | Ignore marks error as dismissed | Integration test |

---

#### FR-MOB-005: Settings Screen

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-005 |
| **Title** | Application Settings Screen |
| **Priority** | Medium |

**Wireframe:**
```
┌─────────────────────────────────┐
│ ←  Settings                    │
├─────────────────────────────────┤
│                                 │
│  CONNECTION                     │
│  ┌───────────────────────────┐  │
│  │ Server URL                │  │
│  │ https://api.example.com   │  │
│  └───────────────────────────┘  │
│  Connection Status: ● Connected │
│                                 │
│  NOTIFICATIONS                  │
│  ┌───────────────────────────┐  │
│  │ Push Notifications    [✓] │  │
│  │ Error Alerts          [✓] │  │
│  │ Update Alerts         [ ] │  │
│  │ Sound                 [✓] │  │
│  │ Vibration             [✓] │  │
│  └───────────────────────────┘  │
│                                 │
│  SECURITY                       │
│  ┌───────────────────────────┐  │
│  │ Biometric Login       [✓] │  │
│  │ Auto-Lock (5 min)     [▼] │  │
│  └───────────────────────────┘  │
│                                 │
│  AUTOMATION (Admin Only)        │
│  ┌───────────────────────────┐  │
│  │ Auto-Fix Enabled      [✓] │  │
│  │ Polling Interval      [▼] │  │
│  │ Max Retry Attempts    [5] │  │
│  └───────────────────────────┘  │
│                                 │
│  ACCOUNT                        │
│  ┌───────────────────────────┐  │
│  │ Logged in as: admin       │  │
│  │ [Logout]                  │  │
│  └───────────────────────────┘  │
│                                 │
│  App Version: 1.0.0             │
│                                 │
└─────────────────────────────────┘
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-021 | Settings persist between sessions | E2E test |
| AC-MOB-022 | Admin-only settings hidden for viewers | E2E test |
| AC-MOB-023 | Configuration changes sync to server | Integration test |
| AC-MOB-024 | Logout clears all sensitive data | Security test |

---

### 4.4 Push Notifications

#### FR-MOB-006: Push Notification System

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-006 |
| **Title** | Firebase Push Notifications |
| **Priority** | Medium |

**Notification Types:**
```typescript
interface NotificationPayload {
    type: 'error_detected' | 'fix_complete' | 'fix_failed' |
          'update_complete' | 'system_alert';
    title: string;
    body: string;
    data: {
        errorId?: string;
        moduleId?: string;
        action?: string;
    };
}

// Examples:
const NOTIFICATION_TEMPLATES = {
    error_detected: {
        title: "New Error Detected",
        body: "{error_type} in {module_name}",
        android_channel: "errors",
        ios_category: "ERROR"
    },
    fix_complete: {
        title: "Error Fixed",
        body: "{error_type} in {module_name} resolved",
        android_channel: "fixes",
        ios_category: "FIX"
    },
    fix_failed: {
        title: "Fix Failed",
        body: "{error_type} in {module_name} - all attempts exhausted",
        android_channel: "errors",
        ios_category: "ERROR"
    },
    system_alert: {
        title: "System Alert",
        body: "{message}",
        android_channel: "alerts",
        ios_category: "ALERT"
    }
};
```

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-025 | Notifications received when app in background | Manual test |
| AC-MOB-026 | Tapping notification opens relevant screen | E2E test |
| AC-MOB-027 | Notifications respect user preferences | E2E test |
| AC-MOB-028 | Silent notifications update app badge | Manual test |

---

### 4.5 Offline Support

#### FR-MOB-007: Offline Mode

| Attribute | Value |
|-----------|-------|
| **ID** | FR-MOB-007 |
| **Title** | Offline Data Caching |
| **Priority** | Low |

**Caching Strategy:**
```typescript
interface CacheConfig {
    // Cache durations in seconds
    durations: {
        systemStatus: 60,       // 1 minute
        updatesList: 300,       // 5 minutes
        errorsList: 300,        // 5 minutes
        errorDetails: 600,      // 10 minutes
        config: 3600            // 1 hour
    };
    maxCacheSize: 50 * 1024 * 1024;  // 50 MB
    storage: 'AsyncStorage';
}
```

**Behavior:**
1. Display cached data when offline
2. Show "Offline" indicator in header
3. Queue actions (retry, ignore) for sync when online
4. Auto-sync when connection restored
5. Clear stale cache on successful sync

**Acceptance Criteria:**
| AC ID | Criterion | Test Method |
|-------|-----------|-------------|
| AC-MOB-029 | App displays cached data when offline | E2E test |
| AC-MOB-030 | Offline indicator visible | Manual test |
| AC-MOB-031 | Queued actions sync when online | Integration test |
| AC-MOB-032 | Stale data indicator after cache TTL | E2E test |

---

## 5. NON-FUNCTIONAL REQUIREMENTS

### 5.1 Performance Requirements

| ID | Requirement | Target | Test Method |
|----|-------------|--------|-------------|
| NFR-PERF-001 | Repository poll completion time | < 5 seconds | Performance test |
| NFR-PERF-002 | Module update time (single) | < 2 minutes | Performance test |
| NFR-PERF-003 | Error detection latency | < 1 second | Performance test |
| NFR-PERF-004 | API response time (95th percentile) | < 500ms | Load test |
| NFR-PERF-005 | WebSocket event delivery | < 100ms | Performance test |
| NFR-PERF-006 | Mobile app cold start | < 3 seconds | Manual test |
| NFR-PERF-007 | Mobile app memory usage | < 150 MB | Profiling |
| NFR-PERF-008 | Log processing throughput | > 1000 lines/sec | Performance test |
| NFR-PERF-009 | Concurrent API connections | > 100 | Load test |
| NFR-PERF-010 | Database query time (95th) | < 100ms | Performance test |

### 5.2 Security Requirements

| ID | Requirement | Implementation |
|----|-------------|----------------|
| NFR-SEC-001 | Authentication | JWT with 1-hour expiry, refresh tokens |
| NFR-SEC-002 | Authorization | RBAC with Admin, Developer, Viewer roles |
| NFR-SEC-003 | Transport Security | TLS 1.3 for all communications |
| NFR-SEC-004 | Token Storage | iOS Keychain, Android Keystore |
| NFR-SEC-005 | API Rate Limiting | 100 requests/minute per user |
| NFR-SEC-006 | Input Validation | All inputs sanitized, parameterized queries |
| NFR-SEC-007 | Secrets Management | No hardcoded secrets, use environment variables |
| NFR-SEC-008 | Audit Logging | All privileged actions logged with user ID |
| NFR-SEC-009 | Session Management | Auto-logout after 30 minutes inactivity |
| NFR-SEC-010 | Log Sanitization | Remove passwords/tokens before AI processing |

### 5.3 Reliability Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-REL-001 | System Uptime | 99% |
| NFR-REL-002 | Mean Time Between Failures | > 720 hours |
| NFR-REL-003 | Mean Time To Recovery | < 15 minutes |
| NFR-REL-004 | Data Durability | 99.99% |
| NFR-REL-005 | Graceful Degradation | Continue with cached data on API failure |

### 5.4 Scalability Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-SCAL-001 | Monitored Repositories | Up to 50 |
| NFR-SCAL-002 | Concurrent Error Fixes | Up to 5 |
| NFR-SCAL-003 | Mobile App Users | Up to 100 concurrent |
| NFR-SCAL-004 | Log File Size | Up to 1 GB |
| NFR-SCAL-005 | History Retention | 90 days |

---

## 6. SYSTEM ARCHITECTURE

### 6.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OAS BACKEND                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Monitor    │    │   Updater    │    │ Error Fixer  │                   │
│  │              │    │              │    │              │                   │
│  │ - poll_repos │───▶│ - pull_code  │    │ - parse_logs │                   │
│  │ - detect_    │    │ - backup_db  │    │ - invoke_    │                   │
│  │   changes    │    │ - update_    │◀───│   claude     │                   │
│  │ - queue_     │    │   modules    │    │ - verify_fix │                   │
│  │   updates    │    │ - rollback   │───▶│ - retry_mgmt │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│         └─────────────┬─────┴───────────────────┘                            │
│                       │                                                      │
│                       ▼                                                      │
│              ┌──────────────────┐                                            │
│              │   Event Bus      │                                            │
│              │   (In-Memory)    │                                            │
│              └────────┬─────────┘                                            │
│                       │                                                      │
│         ┌─────────────┼─────────────┐                                        │
│         ▼             ▼             ▼                                        │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐                             │
│  │  API Server  │ │ Database │ │   Logger     │                             │
│  │  (FastAPI)   │ │ (SQLite) │ │   (JSON)     │                             │
│  │              │ │          │ │              │                             │
│  │ - REST API   │ │ - State  │ │ - Structured │                             │
│  │ - WebSocket  │ │ - History│ │ - Rotated    │                             │
│  │ - Auth       │ │ - Config │ │ - Queryable  │                             │
│  └──────────────┘ └──────────┘ └──────────────┘                             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Sequence Diagrams

#### Update Flow
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ Monitor │ │  Git    │ │ Updater │ │  Odoo   │ │Database │ │ Mobile  │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │           │
     │ fetch     │           │           │           │           │
     │──────────▶│           │           │           │           │
     │           │           │           │           │           │
     │ new commit│           │           │           │           │
     │◀──────────│           │           │           │           │
     │           │           │           │           │           │
     │ pull      │           │           │           │           │
     │──────────▶│           │           │           │           │
     │           │           │           │           │           │
     │ queue update          │           │           │           │
     │──────────────────────▶│           │           │           │
     │           │           │           │           │           │
     │           │           │ backup    │           │           │
     │           │           │──────────────────────▶│           │
     │           │           │           │           │           │
     │           │           │ stop      │           │           │
     │           │           │──────────▶│           │           │
     │           │           │           │           │           │
     │           │           │ update    │           │           │
     │           │           │──────────▶│           │           │
     │           │           │           │           │           │
     │           │           │ start     │           │           │
     │           │           │──────────▶│           │           │
     │           │           │           │           │           │
     │           │           │ log result│           │           │
     │           │           │──────────────────────▶│           │
     │           │           │           │           │           │
     │           │           │ notify    │           │           │
     │           │           │────────────────────────────────▶ │
     │           │           │           │           │           │
```

#### Error Fix Flow
```
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│  Odoo   │ │ErrorFix │ │ Claude  │ │Database │ │ Mobile  │
└────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘
     │           │           │           │           │
     │ error log │           │           │           │
     │──────────▶│           │           │           │
     │           │           │           │           │
     │           │ parse     │           │           │
     │           │──────────▶│           │           │
     │           │           │           │           │
     │           │ store error           │           │
     │           │──────────────────────▶│           │
     │           │           │           │           │
     │           │ notify new error      │           │
     │           │────────────────────────────────▶ │
     │           │           │           │           │
     │           │ invoke    │           │           │
     │           │──────────▶│           │           │
     │           │           │           │           │
     │           │ fix applied           │           │
     │           │◀──────────│           │           │
     │           │           │           │           │
     │ restart   │           │           │           │
     │◀──────────│           │           │           │
     │           │           │           │           │
     │           │ verify fix│           │           │
     │◀─────────▶│           │           │           │
     │           │           │           │           │
     │           │ update status         │           │
     │           │──────────────────────▶│           │
     │           │           │           │           │
     │           │ notify fix complete   │           │
     │           │────────────────────────────────▶ │
     │           │           │           │           │
```

### 6.3 Database Schema

```sql
-- =====================================================
-- OAS Database Schema v2.0
-- =====================================================

-- Repositories being monitored
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    remote TEXT NOT NULL DEFAULT 'origin',
    branch TEXT NOT NULL DEFAULT 'main',
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    last_commit_hash TEXT,
    last_checked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Module updates history
CREATE TABLE module_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repository_id INTEGER NOT NULL,
    module_name TEXT NOT NULL,
    previous_commit TEXT,
    current_commit TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'in_progress', 'success', 'failed', 'rolled_back')),
    files_changed TEXT,  -- JSON array
    error_message TEXT,
    backup_path TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (repository_id) REFERENCES repositories(id)
);

-- Detected errors
CREATE TABLE errors (
    id TEXT PRIMARY KEY,  -- UUID
    error_type TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    category TEXT NOT NULL CHECK(category IN ('PYTHON', 'DATABASE', 'ODOO', 'ASSET', 'DEPENDENCY')),
    message TEXT NOT NULL,
    stack_trace TEXT,
    module_name TEXT,
    file_path TEXT,
    line_number INTEGER,
    context_before TEXT,  -- JSON array of lines
    context_after TEXT,   -- JSON array of lines
    raw_log TEXT,
    status TEXT NOT NULL CHECK(status IN ('detected', 'queued', 'fixing', 'resolved', 'failed', 'ignored')),
    auto_fixable BOOLEAN NOT NULL DEFAULT TRUE,
    detected_at TIMESTAMP NOT NULL,
    resolved_at TIMESTAMP,
    ignored_at TIMESTAMP,
    ignored_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fix attempts
CREATE TABLE fix_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    error_id TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('in_progress', 'success', 'failed', 'timeout')),
    claude_prompt TEXT,
    claude_response TEXT,
    files_modified TEXT,  -- JSON array
    fix_diff TEXT,
    error_after_fix TEXT,  -- New error if fix introduced one
    execution_time_seconds REAL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (error_id) REFERENCES errors(id)
);

-- Audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    component TEXT NOT NULL,
    entity_type TEXT,
    entity_id TEXT,
    user_id TEXT,
    details TEXT,  -- JSON
    ip_address TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration
CREATE TABLE system_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT
);

-- User sessions (for API)
CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    refresh_token_hash TEXT,
    device_info TEXT,
    ip_address TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity_at TIMESTAMP
);

-- Indexes
CREATE INDEX idx_errors_status ON errors(status);
CREATE INDEX idx_errors_detected_at ON errors(detected_at);
CREATE INDEX idx_module_updates_status ON module_updates(status);
CREATE INDEX idx_module_updates_created_at ON module_updates(created_at);
CREATE INDEX idx_fix_attempts_error_id ON fix_attempts(error_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);
CREATE INDEX idx_audit_log_action ON audit_log(action);
```

---

## 7. DATA REQUIREMENTS

### 7.1 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              DATA FLOW                                    │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│   ┌─────────────┐                                                        │
│   │  Git Repo   │                                                        │
│   │   (Source)  │                                                        │
│   └──────┬──────┘                                                        │
│          │ Commits                                                       │
│          ▼                                                               │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐             │
│   │  Monitor    │─────▶│  SQLite DB  │◀─────│ API Server  │             │
│   │  Process    │      │  (Storage)  │      │  Process    │             │
│   └──────┬──────┘      └──────┬──────┘      └──────┬──────┘             │
│          │                    │                    │                     │
│          │ Update             │ Query              │ REST/WS             │
│          │ Request            │                    │                     │
│          ▼                    ▼                    ▼                     │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐             │
│   │   Odoo      │      │   Logs      │      │  Mobile     │             │
│   │  Instance   │─────▶│  (Files)    │      │   App       │             │
│   └─────────────┘      └──────┬──────┘      └─────────────┘             │
│                               │                                          │
│                               │ Parse                                    │
│                               ▼                                          │
│                        ┌─────────────┐                                   │
│                        │ Error Fixer │                                   │
│                        │  Process    │                                   │
│                        └──────┬──────┘                                   │
│                               │                                          │
│                               │ Invoke                                   │
│                               ▼                                          │
│                        ┌─────────────┐                                   │
│                        │ Claude Code │                                   │
│                        │    CLI      │                                   │
│                        └─────────────┘                                   │
│                                                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

### 7.2 Data Retention Policy

| Data Type | Retention Period | Storage Location |
|-----------|------------------|------------------|
| Module Update History | 90 days | SQLite |
| Error Logs | 90 days | SQLite |
| Fix Attempts | 90 days | SQLite |
| Audit Logs | 1 year | SQLite |
| Database Backups | 7 days | Filesystem |
| Application Logs | 30 days | Filesystem |

---

## 8. EXTERNAL INTERFACES

### 8.1 REST API Specification

**Base URL:** `https://{host}:{port}/api/v1`

**Authentication:**
```
Header: Authorization: Bearer {jwt_token}
```

**Common Response Format:**
```json
{
    "success": true,
    "data": { ... },
    "error": null,
    "meta": {
        "timestamp": "2024-11-23T10:30:00Z",
        "request_id": "uuid"
    }
}
```

**Error Response Format:**
```json
{
    "success": false,
    "data": null,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input",
        "details": [
            {"field": "email", "message": "Invalid email format"}
        ]
    },
    "meta": { ... }
}
```

**HTTP Status Codes:**
| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET/PUT |
| 201 | Created | Successful POST |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Invalid/missing token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### 8.2 WebSocket Protocol

**Connection:**
```javascript
const ws = new WebSocket('wss://{host}:{port}/ws');
ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'authenticate',
        token: '{jwt_token}'
    }));
};
```

**Message Format:**
```json
{
    "type": "event_type",
    "timestamp": "2024-11-23T10:30:00Z",
    "payload": { ... }
}
```

---

## 9. TESTING REQUIREMENTS

### 9.1 Testing Overview

| Test Level | Coverage Target | Tools |
|------------|-----------------|-------|
| Unit Tests | 80% code coverage | pytest, Jest |
| Integration Tests | All component interfaces | pytest, Detox |
| API Tests | All endpoints | pytest, Postman |
| E2E Tests | Critical user flows | Detox, Appium |
| Performance Tests | All performance requirements | Locust, k6 |
| Security Tests | OWASP Top 10 | Bandit, OWASP ZAP |

### 9.2 Unit Test Specifications

#### 9.2.1 Monitor Module Tests

```python
# test_monitor.py

class TestRepositoryPolling:
    """Tests for FR-MON-001: Git Repository Polling"""

    def test_detect_new_commits(self, mock_git_repo):
        """
        Given: A repository with new commits on remote
        When: poll_repository() is called
        Then: Returns ChangeEvent with correct commit hashes
        """
        # Arrange
        mock_git_repo.fetch.return_value = None
        mock_git_repo.rev_parse.side_effect = ['abc123', 'def456']

        # Act
        result = poll_repository('/path/to/repo', 'origin', 'main')

        # Assert
        assert result is not None
        assert result.previous_commit == 'abc123'
        assert result.current_commit == 'def456'

    def test_no_changes_returns_none(self, mock_git_repo):
        """
        Given: A repository with no new commits
        When: poll_repository() is called
        Then: Returns None
        """
        mock_git_repo.rev_parse.return_value = 'abc123'  # Same hash
        result = poll_repository('/path/to/repo', 'origin', 'main')
        assert result is None

    def test_network_error_raises_exception(self, mock_git_repo):
        """
        Given: Network is unavailable
        When: poll_repository() is called
        Then: Raises NetworkError with appropriate message
        """
        mock_git_repo.fetch.side_effect = GitCommandError('fetch', 'Network unreachable')

        with pytest.raises(NetworkError) as exc:
            poll_repository('/path/to/repo', 'origin', 'main')

        assert 'Network unreachable' in str(exc.value)

    def test_invalid_repository_raises_exception(self):
        """
        Given: An invalid repository path
        When: poll_repository() is called
        Then: Raises RepositoryNotFoundError
        """
        with pytest.raises(RepositoryNotFoundError):
            poll_repository('/nonexistent/path', 'origin', 'main')


class TestChangeDetection:
    """Tests for FR-MON-002: Change Detection"""

    @pytest.mark.parametrize("file_path,expected_module", [
        ("sale_custom/models/sale.py", "sale_custom"),
        ("hr_extension/__manifest__.py", "hr_extension"),
        ("stock_mod/static/src/js/widget.js", "stock_mod"),
    ])
    def test_extract_module_from_path(self, file_path, expected_module):
        """Correctly extracts module name from file path"""
        result = extract_module_name(file_path)
        assert result == expected_module

    @pytest.mark.parametrize("file_path,expected_type", [
        ("sale_custom/models/sale.py", ChangeType.PYTHON),
        ("sale_custom/views/sale_view.xml", ChangeType.XML),
        ("sale_custom/static/src/js/widget.js", ChangeType.ASSET),
        ("sale_custom/__manifest__.py", ChangeType.MANIFEST),
    ])
    def test_classify_change_type(self, file_path, expected_type):
        """Correctly classifies file change type"""
        result = classify_change_type(file_path)
        assert result == expected_type

    def test_python_change_requires_restart(self):
        """Python file changes require Odoo restart"""
        changes = detect_module_changes(["sale_custom/models/sale.py"])
        assert changes[0].requires_restart is True

    def test_xml_change_no_restart(self):
        """XML file changes do not require restart"""
        changes = detect_module_changes(["sale_custom/views/sale_view.xml"])
        assert changes[0].requires_restart is False
```

#### 9.2.2 Updater Module Tests

```python
# test_updater.py

class TestModuleUpdate:
    """Tests for FR-UPD-001: Automated Module Updates"""

    def test_successful_single_module_update(self, mock_odoo, mock_db):
        """
        Given: A valid module name and running Odoo
        When: update_module() is called
        Then: Module is updated and result status is SUCCESS
        """
        request = UpdateRequest(
            modules=['sale_custom'],
            database='test_db',
            backup_before=True
        )

        result = update_modules(request)

        assert result.status == UpdateStatus.SUCCESS
        assert 'sale_custom' in result.modules_updated
        assert result.backup_path is not None

    def test_backup_created_before_update(self, mock_odoo, mock_db):
        """
        Given: backup_before=True
        When: update_module() is called
        Then: Database backup is created before update starts
        """
        # Test implementation
        pass

    def test_rollback_on_update_failure(self, mock_odoo, mock_db):
        """
        Given: A module update that fails
        When: update_module() is called
        Then: Database is rolled back to backup
        """
        mock_odoo.update.side_effect = OdooUpdateError("Update failed")

        request = UpdateRequest(modules=['broken_module'], database='test_db')
        result = update_modules(request)

        assert result.status == UpdateStatus.FAILED
        mock_db.restore.assert_called_once()


class TestBackupSafety:
    """Tests for FR-UPD-002: Update Safety Mechanisms"""

    def test_backup_includes_database(self):
        """Backup contains complete database dump"""
        pass

    def test_backup_compressed(self):
        """Backup is compressed with gzip"""
        pass

    def test_old_backups_deleted(self):
        """Backups older than retention period are deleted"""
        pass

    def test_restore_exact_state(self):
        """Restore returns database to exact previous state"""
        pass
```

#### 9.2.3 Error Fixer Module Tests

```python
# test_error_fixer.py

class TestLogParsing:
    """Tests for FR-ERR-001: Real-Time Log Monitoring"""

    @pytest.mark.parametrize("log_line,expected_type", [
        ("ImportError: No module named 'missing'", "ImportError"),
        ("SyntaxError: invalid syntax", "SyntaxError"),
        ("psycopg2.OperationalError: connection refused", "psycopg2.OperationalError"),
        ("odoo.exceptions.ValidationError: Invalid value", "ValidationError"),
    ])
    def test_error_type_extraction(self, log_line, expected_type):
        """Correctly extracts error type from log line"""
        result = parse_error_type(log_line)
        assert result == expected_type

    def test_stack_trace_extraction(self):
        """Extracts complete stack trace from multi-line log"""
        log_content = '''
2024-11-23 10:30:00 ERROR module Traceback (most recent call last):
  File "/odoo/addons/sale_custom/models/sale.py", line 42, in _compute_total
    result = self.amount / self.quantity
ZeroDivisionError: division by zero
'''
        result = parse_stack_trace(log_content)

        assert 'sale_custom/models/sale.py' in result.file_path
        assert result.line_number == 42
        assert 'ZeroDivisionError' in result.error_type

    def test_context_lines_captured(self):
        """Captures 10 lines before and after error"""
        pass


class TestClaudeIntegration:
    """Tests for FR-FIX-001: Claude Code CLI Integration"""

    def test_prompt_contains_all_context(self):
        """Generated prompt includes all error context"""
        error = DetectedError(
            error_type="ImportError",
            module_name="sale_custom",
            file_path="models/sale.py",
            line_number=42,
            message="No module named 'missing_dep'",
            stack_trace="Traceback..."
        )

        prompt = generate_claude_prompt(error)

        assert "ImportError" in prompt
        assert "sale_custom" in prompt
        assert "models/sale.py" in prompt
        assert "line 42" in prompt.lower()
        assert "missing_dep" in prompt

    def test_timeout_enforced(self, mock_subprocess):
        """Claude CLI call times out after 5 minutes"""
        mock_subprocess.run.side_effect = subprocess.TimeoutExpired('claude', 300)

        result = invoke_claude_code(error, '/path/to/workspace')

        assert result.success is False
        assert 'timeout' in result.error_message.lower()


class TestRetryMechanism:
    """Tests for FR-FIX-002: Retry Mechanism"""

    @pytest.mark.parametrize("attempt,expected_delay", [
        (1, 0),      # No delay for first attempt
        (2, 60),     # 1 minute
        (3, 120),    # 2 minutes
        (4, 240),    # 4 minutes
        (5, 480),    # 8 minutes
    ])
    def test_exponential_backoff_delays(self, attempt, expected_delay):
        """Correct delay calculated for each attempt"""
        config = RetryConfig(base_delay_seconds=60, multiplier=2.0)
        result = config.get_delay(attempt)
        assert result == expected_delay

    def test_max_five_attempts(self):
        """Error is escalated after 5 failed attempts"""
        error = create_test_error()

        for i in range(5):
            result = attempt_fix(error)
            assert result.success is False

        # 6th attempt should be rejected
        with pytest.raises(MaxAttemptsExceededError):
            attempt_fix(error)

    def test_attempts_persist_across_restart(self):
        """Attempt counter persists in database"""
        pass
```

### 9.3 Integration Test Specifications

```python
# test_integration.py

class TestEndToEndUpdateFlow:
    """Integration tests for complete update flow"""

    @pytest.fixture
    def running_odoo(self):
        """Start a test Odoo instance"""
        # Setup code
        yield odoo_instance
        # Teardown code

    def test_commit_triggers_update(self, running_odoo, test_repo):
        """
        E2E test: New commit triggers complete update flow

        Steps:
        1. Make a commit to test repository
        2. Wait for monitor to detect change
        3. Verify module is updated
        4. Verify Odoo reflects changes
        """
        # Arrange
        original_value = get_module_version(running_odoo, 'test_module')

        # Act
        make_commit(test_repo, 'test_module/__manifest__.py',
                   version='2.0.0')

        # Wait for detection and update (max 2 minutes)
        wait_for_condition(
            lambda: get_module_version(running_odoo, 'test_module') == '2.0.0',
            timeout=120
        )

        # Assert
        assert get_module_version(running_odoo, 'test_module') == '2.0.0'
        assert get_update_status('test_module') == 'success'


class TestErrorFixFlow:
    """Integration tests for error detection and fixing"""

    def test_syntax_error_detected_and_fixed(self, running_odoo):
        """
        E2E test: Syntax error is detected and fixed automatically

        Steps:
        1. Introduce a syntax error in module
        2. Wait for error detection
        3. Wait for Claude Code fix
        4. Verify error is resolved
        """
        # Arrange
        introduce_syntax_error('test_module/models/test.py')

        # Act - Restart Odoo to trigger error
        restart_odoo(running_odoo)

        # Wait for error detection
        error = wait_for_error(error_type='SyntaxError', timeout=60)
        assert error is not None

        # Wait for fix (max 10 minutes for all attempts)
        wait_for_condition(
            lambda: get_error_status(error.id) == 'resolved',
            timeout=600
        )

        # Assert
        assert get_error_status(error.id) == 'resolved'
        assert odoo_is_running(running_odoo)
```

### 9.4 API Test Specifications

```python
# test_api.py

class TestAuthenticationAPI:
    """API tests for authentication endpoints"""

    def test_login_success(self, api_client):
        """POST /api/v1/auth/login returns JWT on valid credentials"""
        response = api_client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'valid_password'
        })

        assert response.status_code == 200
        assert 'access_token' in response.json()['data']
        assert 'refresh_token' in response.json()['data']

    def test_login_invalid_credentials(self, api_client):
        """POST /api/v1/auth/login returns 401 on invalid credentials"""
        response = api_client.post('/api/v1/auth/login', json={
            'username': 'admin',
            'password': 'wrong_password'
        })

        assert response.status_code == 401
        assert response.json()['error']['code'] == 'INVALID_CREDENTIALS'

    def test_protected_endpoint_without_token(self, api_client):
        """Protected endpoints return 401 without token"""
        response = api_client.get('/api/v1/status')
        assert response.status_code == 401


class TestStatusAPI:
    """API tests for status endpoints"""

    def test_get_system_status(self, authenticated_client):
        """GET /api/v1/status returns current system status"""
        response = authenticated_client.get('/api/v1/status')

        assert response.status_code == 200
        data = response.json()['data']
        assert 'status' in data
        assert 'uptime_seconds' in data
        assert 'components' in data


class TestUpdatesAPI:
    """API tests for updates endpoints"""

    def test_list_updates_paginated(self, authenticated_client):
        """GET /api/v1/updates returns paginated list"""
        response = authenticated_client.get('/api/v1/updates?limit=10&offset=0')

        assert response.status_code == 200
        data = response.json()['data']
        assert 'total' in data
        assert 'items' in data
        assert len(data['items']) <= 10

    def test_trigger_update(self, authenticated_client):
        """POST /api/v1/updates/trigger queues update job"""
        response = authenticated_client.post('/api/v1/updates/trigger', json={
            'modules': ['test_module']
        })

        assert response.status_code == 201
        assert 'job_id' in response.json()['data']


class TestErrorsAPI:
    """API tests for errors endpoints"""

    def test_list_active_errors(self, authenticated_client):
        """GET /api/v1/errors?status=active returns active errors"""
        response = authenticated_client.get('/api/v1/errors?status=active')

        assert response.status_code == 200
        for error in response.json()['data']['items']:
            assert error['status'] in ['detected', 'queued', 'fixing']

    def test_retry_error_fix(self, authenticated_client, active_error):
        """POST /api/v1/errors/{id}/retry queues retry"""
        response = authenticated_client.post(f'/api/v1/errors/{active_error.id}/retry')

        assert response.status_code == 200
        assert response.json()['data']['status'] == 'queued'
```

### 9.5 Mobile App Test Specifications

```typescript
// __tests__/screens/LoginScreen.test.tsx

describe('LoginScreen', () => {
    it('should display validation error for invalid URL', async () => {
        const { getByTestId, getByText } = render(<LoginScreen />);

        fireEvent.changeText(getByTestId('server-url-input'), 'invalid-url');
        fireEvent.press(getByTestId('login-button'));

        await waitFor(() => {
            expect(getByText('Valid URL required')).toBeTruthy();
        });
    });

    it('should navigate to dashboard on successful login', async () => {
        mockApi.login.mockResolvedValue({ access_token: 'token' });

        const { getByTestId } = render(<LoginScreen />);

        fireEvent.changeText(getByTestId('server-url-input'), 'https://api.example.com');
        fireEvent.changeText(getByTestId('username-input'), 'admin');
        fireEvent.changeText(getByTestId('password-input'), 'password');
        fireEvent.press(getByTestId('login-button'));

        await waitFor(() => {
            expect(mockNavigation.navigate).toHaveBeenCalledWith('Dashboard');
        });
    });

    it('should store token securely on successful login', async () => {
        mockApi.login.mockResolvedValue({ access_token: 'secure_token' });

        const { getByTestId } = render(<LoginScreen />);
        // ... fill form and submit

        await waitFor(() => {
            expect(SecureStore.setItemAsync).toHaveBeenCalledWith(
                'auth_token',
                'secure_token'
            );
        });
    });
});

describe('DashboardScreen', () => {
    it('should display system status', async () => {
        mockApi.getStatus.mockResolvedValue({
            status: 'running',
            uptime_seconds: 86400
        });

        const { getByText } = render(<DashboardScreen />);

        await waitFor(() => {
            expect(getByText('Running')).toBeTruthy();
            expect(getByText(/1d/)).toBeTruthy();  // 1 day uptime
        });
    });

    it('should update in real-time via WebSocket', async () => {
        const { getByTestId } = render(<DashboardScreen />);

        // Simulate WebSocket event
        act(() => {
            mockWebSocket.emit('status_change', {
                old_status: 'running',
                new_status: 'updating'
            });
        });

        await waitFor(() => {
            expect(getByTestId('status-indicator')).toHaveTextContent('Updating');
        });
    });
});
```

### 9.6 Performance Test Specifications

```python
# locustfile.py

from locust import HttpUser, task, between

class OASUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Login and get token"""
        response = self.client.post('/api/v1/auth/login', json={
            'username': 'loadtest',
            'password': 'loadtest123'
        })
        self.token = response.json()['data']['access_token']
        self.client.headers = {'Authorization': f'Bearer {self.token}'}

    @task(10)
    def get_status(self):
        """Most common operation"""
        self.client.get('/api/v1/status')

    @task(5)
    def list_updates(self):
        self.client.get('/api/v1/updates?limit=20')

    @task(5)
    def list_errors(self):
        self.client.get('/api/v1/errors?status=active')

    @task(1)
    def get_error_detail(self):
        self.client.get('/api/v1/errors/test-error-id')

# Performance Targets:
# - 100 concurrent users
# - 95th percentile response time < 500ms
# - Error rate < 1%
# - Throughput > 100 requests/second
```

### 9.7 Security Test Specifications

```yaml
# security_tests.yaml

tests:
  - name: SQL Injection
    target: All API endpoints with parameters
    tool: sqlmap
    expected: No successful injections

  - name: Authentication Bypass
    target: Protected endpoints
    tool: Manual + Burp Suite
    expected: All return 401 without valid token

  - name: JWT Token Validation
    checks:
      - Expired token rejected
      - Modified token rejected
      - Token from different server rejected
    expected: All return 401

  - name: Rate Limiting
    target: /api/v1/auth/login
    method: Send 200 requests in 1 minute
    expected: Returns 429 after 100 requests

  - name: Sensitive Data Exposure
    target: Error responses, logs
    check: No passwords, tokens, or secrets exposed
    expected: All sensitive data masked

  - name: HTTPS Enforcement
    target: All endpoints
    expected: HTTP redirects to HTTPS

  - name: Dependency Vulnerabilities
    tool: pip-audit, npm audit
    expected: No high/critical vulnerabilities
```

### 9.8 Test Data

```python
# test_fixtures.py

TEST_ERRORS = [
    {
        "id": "test-error-001",
        "error_type": "ImportError",
        "message": "No module named 'missing_dep'",
        "module_name": "sale_custom",
        "file_path": "models/sale.py",
        "line_number": 42,
        "stack_trace": """Traceback (most recent call last):
  File "/odoo/addons/sale_custom/models/sale.py", line 42, in <module>
    from missing_dep import helper
ImportError: No module named 'missing_dep'""",
        "severity": "HIGH",
        "auto_fixable": True
    },
    {
        "id": "test-error-002",
        "error_type": "SyntaxError",
        "message": "invalid syntax",
        "module_name": "hr_extension",
        "file_path": "models/employee.py",
        "line_number": 15,
        "stack_trace": """  File "/odoo/addons/hr_extension/models/employee.py", line 15
    def calculate_salary(self)
                              ^
SyntaxError: invalid syntax""",
        "severity": "CRITICAL",
        "auto_fixable": True
    }
]

TEST_UPDATES = [
    {
        "id": 1,
        "module_name": "sale_custom",
        "status": "success",
        "commit_hash": "abc123def456",
        "duration_seconds": 45,
        "updated_at": "2024-11-23T10:30:00Z"
    }
]
```

---

## 10. IMPLEMENTATION PLAN

### 10.1 Phase Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1: Core Infrastructure | Week 1 | Project setup, config, database, logging |
| Phase 2: Repository Monitoring | Week 2 | Git polling, change detection |
| Phase 3: Module Updates | Week 3 | Odoo update, backup, rollback |
| Phase 4: Error Detection | Week 4 | Log parsing, error classification |
| Phase 5: Error Resolution | Week 5 | Claude CLI integration, retry mechanism |
| Phase 6: API Server | Week 6 | REST API, WebSocket, authentication |
| Phase 7: Mobile App | Weeks 7-8 | React Native app, all screens |
| Phase 8: Testing & QA | Week 9 | All test suites, bug fixes |
| Phase 9: Documentation | Week 10 | User guide, API docs, deployment guide |

### 10.2 Deliverables per Phase

#### Phase 1 Deliverables
- [ ] Project directory structure created
- [ ] requirements.txt with all dependencies
- [ ] config.yaml schema and loader
- [ ] SQLite database schema and migrations
- [ ] Structured JSON logging setup
- [ ] Unit tests for config and database modules

#### Phase 2 Deliverables
- [ ] monitor.py with GitPython integration
- [ ] Change detection algorithm
- [ ] Scheduler for 1-minute polling
- [ ] Unit tests for monitor module (80% coverage)
- [ ] Integration test for change detection

---

## 11. APPENDICES

### 11.1 Configuration Reference

```yaml
# Complete config.yaml reference

# Odoo Instance Configuration
odoo:
  path: /opt/odoo19                    # Odoo installation path
  config: /etc/odoo/odoo.conf          # Odoo configuration file
  database: production                 # Database name
  log_file: /var/log/odoo/odoo.log    # Odoo log file path
  service_name: odoo                   # Systemd service name

# GitHub Repository Monitoring
github:
  repositories:
    - path: /home/odoo/custom_addons   # Local path to repo
      remote: origin                   # Git remote name
      branch: main                     # Branch to monitor
      enabled: true                    # Enable monitoring
      modules_whitelist: []            # Only these modules (empty = all)
      modules_blacklist:               # Ignore these modules
        - test_module
  polling_interval: 60                 # Seconds between polls (1-300)
  max_concurrent_pulls: 3              # Parallel git operations

# Automation Settings
automation:
  enabled: true                        # Master switch
  max_retry_attempts: 5                # Max fix attempts per error
  backoff_base: 60                     # Base delay in seconds
  backoff_multiplier: 2.0              # Exponential multiplier
  claude_code_path: /usr/local/bin/claude  # Claude CLI path
  claude_timeout: 300                  # CLI timeout in seconds
  fix_verification_wait: 30            # Seconds to wait after fix

# Backup Configuration
backup:
  enabled: true                        # Enable pre-update backups
  path: /var/backups/odoo             # Backup storage path
  retention_days: 7                    # Keep backups for N days
  compression: true                    # Use gzip compression
  include_filestore: false             # Include Odoo filestore

# API Server Configuration
api:
  host: 0.0.0.0                       # Bind address
  port: 8080                          # HTTP port
  websocket_port: 8081                # WebSocket port
  cors_origins:                       # Allowed CORS origins
    - http://localhost:3000
    - https://app.example.com
  rate_limit: 100                     # Requests per minute
  jwt_secret: ${JWT_SECRET}           # From environment
  jwt_expiry: 3600                    # Token expiry in seconds

# Logging Configuration
logging:
  level: INFO                         # DEBUG, INFO, WARNING, ERROR
  format: json                        # json or text
  file: logs/automation.log           # Log file path
  max_size_mb: 10                     # Max file size before rotation
  backup_count: 5                     # Number of rotated files

# Database Configuration
database:
  path: data/oas.db                   # SQLite database path
  backup_on_startup: true             # Backup DB on service start
```

### 11.2 Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| AUTH_001 | 401 | Invalid credentials |
| AUTH_002 | 401 | Token expired |
| AUTH_003 | 401 | Token invalid |
| AUTH_004 | 403 | Insufficient permissions |
| VAL_001 | 400 | Invalid input format |
| VAL_002 | 400 | Required field missing |
| VAL_003 | 400 | Field value out of range |
| RES_001 | 404 | Resource not found |
| RES_002 | 409 | Resource conflict |
| SRV_001 | 500 | Internal server error |
| SRV_002 | 503 | Service unavailable |
| RATE_001 | 429 | Rate limit exceeded |

### 11.3 Glossary

| Term | Definition |
|------|------------|
| Polling | Repeatedly checking for changes at fixed intervals |
| Exponential Backoff | Retry strategy where wait time increases exponentially |
| Rollback | Reverting to a previous known-good state |
| Correlation ID | Unique identifier to trace requests across components |
| Filestore | Odoo's attachment storage directory |
| Manifest | Odoo module's `__manifest__.py` file |

---

## DOCUMENT APPROVAL

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Project Manager | | | |
| Technical Lead | | | |
| QA Lead | | | |
| Security Lead | | | |
| Stakeholder | | | |

---

## REVISION HISTORY

| Version | Date | Description | Author |
|---------|------|-------------|--------|
| 1.0 | Nov 2024 | Initial Draft | OAS Team |
| 2.0 | Nov 2024 | Added mobile specs, testing, detailed requirements | OAS Team |

---

*End of Document*
