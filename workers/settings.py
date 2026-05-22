"""ARQ worker settings."""

from arq import cron, func
from arq.connections import RedisSettings

from shared.config import get_settings

settings = get_settings()


# Redis connection settings for ARQ
arq_redis_settings = RedisSettings(
    host=settings.redis_host,
    port=settings.redis_port,
    database=settings.redis_db,
    password=settings.redis_password or None,
)


class CriticalWorkerSettings:
    """Critical worker: handles print jobs (time-sensitive, blocks gate UX)."""

    redis_settings = arq_redis_settings
    queue_name = "arq:queue:critical"

    functions = [
        func("workers.critical.print_worker.print_ticket", name="print_ticket"),
        func("workers.critical.print_worker.print_receipt", name="print_receipt"),
    ]

    # Retry settings
    max_tries = 3
    job_timeout = 30  # seconds

    # Worker settings
    handle_signals = True


class SnapshotWorkerSettings:
    """Snapshot worker: separate queue so slow RTSP grabs never block prints."""

    redis_settings = arq_redis_settings
    queue_name = "arq:queue:snapshot"

    functions = [
        func("workers.critical.snapshot_worker.take_snapshot", name="take_snapshot"),
    ]

    # Snapshot retries less aggressive — disk full / camera offline shouldn't spin.
    max_tries = 2
    job_timeout = 30
    max_jobs = 5  # cap parallel RTSP opens

    handle_signals = True


class BackgroundWorkerSettings:
    """Background worker: handles settlement, cleanup, notifications."""

    redis_settings = arq_redis_settings
    queue_name = "arq:queue:background"

    functions = [
        func("workers.background.settlement_worker.generate_settlement_file", name="generate_settlement_file"),
        func("workers.background.settlement_uploader.upload_settlement_job", name="upload_settlement_job"),
        func("workers.background.settlement_uploader.poll_settlement_responses", name="poll_settlement_responses"),
        func("workers.background.cleanup_worker.cleanup_old_sessions", name="cleanup_old_sessions"),
        func("workers.background.cleanup_worker.cleanup_old_snapshots", name="cleanup_old_snapshots"),
        func("workers.background.cleanup_worker.timeout_pending_payments", name="timeout_pending_payments"),
        func("workers.background.notification_worker.send_telegram_alert", name="send_telegram_alert"),
    ]

    # Cron jobs
    cron_jobs = [
        # Daily settlement at 2 AM (operational timezone enforced inside the job)
        cron(
            "workers.background.settlement_worker.generate_settlement_file",
            name="generate_settlement_file",
            hour=2,
            minute=0,
        ),
        # Poll bank for .OK/.NOK every 15 minutes — fast enough for prompt
        # reconciliation, sparse enough to not hammer the bank's SFTP.
        cron(
            "workers.background.settlement_uploader.poll_settlement_responses",
            name="poll_settlement_responses",
            minute={0, 15, 30, 45},
        ),
        # Cleanup old data daily at 3 AM
        cron(
            "workers.background.cleanup_worker.cleanup_old_sessions",
            name="cleanup_old_sessions",
            hour=3,
            minute=0,
        ),
        # Timeout stuck PENDING e-money payments every 2 minutes
        cron(
            "workers.background.cleanup_worker.timeout_pending_payments",
            name="timeout_pending_payments",
            minute={0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 26, 28, 30,
                    32, 34, 36, 38, 40, 42, 44, 46, 48, 50, 52, 54, 56, 58},
        ),
    ]

    # Retry settings
    max_tries = 3
    job_timeout = 300  # seconds (5 minutes for settlement)

    # Worker settings
    handle_signals = True
