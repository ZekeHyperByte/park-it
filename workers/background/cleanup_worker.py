"""Background cleanup worker jobs."""

from datetime import datetime, timedelta, timezone

from shared.logging import get_logger

logger = get_logger("cleanup_worker")

SNAPSHOT_RETENTION_DAYS = 30
SESSION_RETENTION_DAYS = 90
PENDING_PAYMENT_TIMEOUT_MINUTES = 5


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


async def timeout_pending_payments(ctx) -> dict:
    """Reset PENDING e-money transactions that have been stuck too long.

    If the PASSTI reader never responds, transactions stay in PENDING forever.
    This job resets them so the operator can retry with a different payment method.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

    from api.app.models import ParkingTransaction
    from shared.config import get_settings

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=PENDING_PAYMENT_TIMEOUT_MINUTES)
    logger.info("timeout_pending_start", cutoff=cutoff.isoformat())

    try:
        async with async_session() as db:
            # Find stuck PENDING transactions
            result = await db.execute(
                select(ParkingTransaction).where(
                    ParkingTransaction.status == "ACTIVE",
                    ParkingTransaction.payment_method == "PENDING",
                    ParkingTransaction.updated_at < cutoff,
                )
            )
            stuck_txs = result.scalars().all()

            reset_count = 0
            for tx in stuck_txs:
                tx.payment_method = None
                tx.fee = None
                reset_count += 1
                logger.warning(
                    "pending_payment_timeout",
                    transaction_id=tx.id,
                    updated_at=tx.updated_at.isoformat() if tx.updated_at else None,
                )

            if reset_count > 0:
                await db.commit()

            logger.info("timeout_pending_complete", reset_count=reset_count)
            return {"status": "success", "reset_count": reset_count}
    except Exception as e:
        logger.error("timeout_pending_error", error=str(e))
        return {"status": "error", "message": str(e)}
    finally:
        await engine.dispose()
