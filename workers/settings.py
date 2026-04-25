"""ARQ worker settings."""

from arq import cron
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
    """Critical worker: handles print jobs, snapshots, and other time-sensitive tasks."""

    redis_settings = arq_redis_settings
    queue_name = "arq:queue:critical"

    functions = [
        "workers.critical.print_worker.print_ticket",
        "workers.critical.print_worker.print_receipt",
        "workers.critical.snapshot_worker.take_snapshot",
    ]

    # Retry settings
    max_tries = 3
    job_timeout = 30  # seconds

    # Worker settings
    handle_signals = True


class BackgroundWorkerSettings:
    """Background worker: handles settlement, cleanup, notifications."""

    redis_settings = arq_redis_settings
    queue_name = "arq:queue:background"

    functions = [
        "workers.background.settlement_worker.generate_settlement_file",
        "workers.background.cleanup_worker.cleanup_old_sessions",
        "workers.background.cleanup_worker.cleanup_old_snapshots",
        "workers.background.notification_worker.send_telegram_alert",
    ]

    # Cron jobs
    cron_jobs = [
        # Daily settlement at 2 AM
        cron(
            "workers.background.settlement_worker.generate_settlement_file",
            hour=2,
            minute=0,
        ),
        # Cleanup old data daily at 3 AM
        cron(
            "workers.background.cleanup_worker.cleanup_old_sessions",
            hour=3,
            minute=0,
        ),
    ]

    # Retry settings
    max_tries = 3
    job_timeout = 300  # seconds (5 minutes for settlement)

    # Worker settings
    handle_signals = True
