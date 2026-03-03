PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS step_runs (
    job_id TEXT NOT NULL,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    error_json TEXT,
    error_kind TEXT,
    retry_meta_json TEXT,
    result_json TEXT,
    cache_key TEXT,
    UNIQUE(job_id, step_name, attempt)
);

CREATE INDEX IF NOT EXISTS idx_step_runs_job_id_step_name
    ON step_runs(job_id, step_name);

CREATE INDEX IF NOT EXISTS idx_step_runs_job_id_step_name_cache_key
    ON step_runs(job_id, step_name, cache_key);

CREATE TABLE IF NOT EXISTS locks (
    lock_key TEXT PRIMARY KEY,
    owner TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_locks_expires_at
    ON locks(expires_at);

CREATE TABLE IF NOT EXISTS checkpoints (
    job_id TEXT PRIMARY KEY,
    last_completed_step TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    payload_json TEXT
);
