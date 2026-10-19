-- Missing policy rows mean V1. Never infer V2 from the attempts counter.
CREATE TABLE mia_job_policy (
    job_id TEXT PRIMARY KEY REFERENCES mia_jobs(id) ON DELETE CASCADE,
    version INTEGER NOT NULL CHECK(version=2),
    phase TEXT NOT NULL,
    phase_at REAL NOT NULL,
    waiting_at REAL,
    slot_acquired_at REAL,
    rechecked_at REAL,
    feedback TEXT
);

-- Intent is a conservative attempt reservation, not proof of remote receipt.
CREATE TABLE mia_model_requests (
    job_id TEXT NOT NULL REFERENCES mia_job_policy(job_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK(ordinal BETWEEN 1 AND 2),
    waiting_at REAL,
    slot_acquired_at REAL NOT NULL,
    rechecked_at REAL NOT NULL,
    intent_at REAL NOT NULL,
    sdk_started_at REAL,
    http_started_at REAL,
    http_sends INTEGER NOT NULL DEFAULT 0 CHECK(http_sends BETWEEN 0 AND 1),
    response_completed_at REAL,
    native_finished_at REAL,
    outcome TEXT NOT NULL,
    PRIMARY KEY(job_id,ordinal)
);

CREATE TRIGGER mia_job_policy_terminal AFTER UPDATE OF state ON mia_jobs
WHEN NEW.state NOT IN ('pending','extracting','validated','retry_wait') BEGIN
    UPDATE mia_job_policy SET phase='terminal',phase_at=NEW.updated_at,feedback=NULL
        WHERE job_id=NEW.id;
END;
