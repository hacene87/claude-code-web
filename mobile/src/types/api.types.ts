/**
 * API Type Definitions
 * ====================
 */

// Authentication
export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  username: string;
  role: 'admin' | 'developer' | 'viewer';
  disabled: boolean;
}

// System Status
export interface SystemStatus {
  status: 'running' | 'stopped' | 'error' | 'degraded';
  uptime_seconds: number;
  last_poll?: string;
  active_errors: number;
  pending_updates: number;
  components: {
    monitor: string;
    updater: string;
    error_detector: string;
    error_fixer: string;
  };
}

export interface ComponentStatus {
  name: string;
  status: string;
  details: Record<string, any>;
}

export interface Metrics {
  updates_today: number;
  successful_updates_today: number;
  errors_today: number;
  resolved_today: number;
  fix_success_rate_7d: number;
  total_fix_attempts_7d: number;
  successful_fixes_7d: number;
}

// Updates
export interface UpdateSummary {
  id: number;
  module_name: string;
  status: string;
  commit_hash: string;
  created_at: string;
  completed_at?: string;
  duration_seconds?: number;
  error_message?: string;
}

export interface UpdateList {
  total: number;
  items: UpdateSummary[];
}

export interface UpdateDetail extends UpdateSummary {
  repository_id: number;
  previous_commit?: string;
  current_commit: string;
  files_changed?: string[];
  backup_path?: string;
  started_at?: string;
}

export interface TriggerUpdateRequest {
  modules: string[];
  force?: boolean;
}

export interface TriggerUpdateResponse {
  job_id: string;
  status: string;
}

// Errors
export type ErrorSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
export type ErrorCategory = 'PYTHON' | 'DATABASE' | 'ODOO' | 'ASSET' | 'DEPENDENCY';
export type ErrorStatus = 'detected' | 'queued' | 'fixing' | 'resolved' | 'failed' | 'ignored';

export interface ErrorSummary {
  id: string;
  error_type: string;
  severity: ErrorSeverity;
  category: ErrorCategory;
  module_name?: string;
  message: string;
  status: ErrorStatus;
  attempts: number;
  detected_at: string;
  resolved_at?: string;
}

export interface ErrorList {
  total: number;
  items: ErrorSummary[];
}

export interface FixAttemptSummary {
  id: number;
  attempt_number: number;
  status: string;
  started_at: string;
  completed_at?: string;
  execution_time_seconds?: number;
  files_modified?: string[];
}

export interface ErrorDetail extends ErrorSummary {
  stack_trace?: string;
  file_path?: string;
  line_number?: number;
  context_before?: string[];
  context_after?: string[];
  raw_log?: string;
  auto_fixable: boolean;
  ignored_at?: string;
  ignored_by?: string;
  fix_attempts: FixAttemptSummary[];
}

// Configuration
export interface RepositoryConfig {
  path: string;
  remote: string;
  branch: string;
  enabled: boolean;
}

export interface AppConfig {
  polling_interval: number;
  max_retry_attempts: number;
  automation_enabled: boolean;
  claude_enabled: boolean;
  backup_enabled: boolean;
  backup_retention_days: number;
  repositories: RepositoryConfig[];
}

// WebSocket Events
export interface WebSocketEvent {
  type: string;
  timestamp: string;
  payload: Record<string, any>;
}

// API Response wrapper
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
    details?: any[];
  };
  meta: {
    timestamp: string;
    request_id: string;
  };
}
