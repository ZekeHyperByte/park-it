"""Background cleanup worker jobs."""

from datetime import datetime, timedelta
from pathlib import Path

from shared.logging import get_logger

logger = get_logger("cleanup_worker")

SNAPSHOT_RETENTION_DAYS = 30
SESSION_RETENTION_DAYS = 90


async def cleanup_old_sessions(ctx) -> dict:
    """Clean up old parking transaction sessions.

    Stub implementation — full logic in Week 5.
    """
    cutoff = datetime.now() - timedelta(days=SESSION_RETENTION_DAYS)
    logger.info("cleanup_sessions_start", cutoff=cutoff.isoformat())

    # TODO: Archive and delete old completed transactions

    return {"status": "success", "message": "Old sessions cleaned (stub)"}


async def cleanup_old_snapshots(ctx) -> dict:
    """Clean up old snapshot files from local filesystem."""
    from workers.critical.snapshot_worker import SNAPSHOT_DIR

    cutoff = datetime.now() - timedelta(days=SNAPSHOT_RETENTION_DAYS)
    logger.info("cleanup_snapshots_start", cutoff=cutoff.isoformat())

    deleted = 0
    try:
        for filepath in SNAPSHOT_DIR.glob("*.jpg"):
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            if mtime < cutoff:
                filepath.unlink()
                deleted += 1
    except Exception as e:
        logger.error("cleanup_snapshots_error", error=str(e))
        return {"status": "error", "message": str(e)}

    logger.info("cleanup_snapshots_complete", deleted=deleted)
    return {"status": "success", "deleted": deleted}
