"""Custom Prometheus metrics for STT application (2f.6)."""

from prometheus_client import Counter, Histogram

# --- Job metrics ---

JOBS_CREATED = Counter(
    "stt_jobs_created_total",
    "Total jobs created",
    ["job_type"],
)

JOBS_COMPLETED = Counter(
    "stt_jobs_completed_total",
    "Total jobs completed successfully",
    ["job_type"],
)

JOBS_FAILED = Counter(
    "stt_jobs_failed_total",
    "Total jobs that failed",
    ["job_type"],
)

JOB_DURATION = Histogram(
    "stt_job_duration_seconds",
    "Time from job start (RUNNING) to completion/failure",
    ["job_type"],
    buckets=(5, 15, 30, 60, 120, 300, 600, 1800, 3600),
)

# --- GDPR metrics ---

GDPR_DELETED = Counter(
    "stt_gdpr_auto_deleted_total",
    "Total jobs auto-deleted by GDPR retention policy",
)
