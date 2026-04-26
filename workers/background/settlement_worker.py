"""Background settlement worker job."""

import hashlib
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone

from sqlalchemy import select

from shared.logging import get_logger
from workers.background.settlement_file import generate_filename, build_settlement_content

# Deferred import to avoid circular dependency at module load time
_settlement_counter = None

def _get_settlement_counter():
    global _settlement_counter
    if _settlement_counter is None:
        from api.app.middleware.metrics import settlement_files_generated_total
        _settlement_counter = settlement_files_generated_total
    return _settlement_counter

logger = get_logger("settlement_worker")

# Settlement files storage path
SETTLEMENT_DIR = os.environ.get("SETTLEMENT_DIR", "/var/lib/parking/settlements")


async def generate_settlement_file(ctx, db=None) -> dict:
    """Generate daily settlement files from successful e-money transactions.

    Groups unsettled transactions by emoney_reader_id, generates one file
    per reader (MID/TID), stores file locally, creates EmoneySettlement record.

    Args:
        ctx: ARQ context dict (may contain redis client)
        db: Optional async DB session for testing. If None, creates a new session.
    """
    logger.info("generate_settlement_job_start")

    from api.database import AsyncSessionLocal
    from api.app.models.emoney_transaction import EmoneyTransaction
    from api.app.models.emoney_reader import EmoneyReader
    from api.app.models.emoney_settlement import EmoneySettlement

    os.makedirs(SETTLEMENT_DIR, exist_ok=True)

    files_generated = 0
    total_transactions = 0

    @asynccontextmanager
    async def _session():
        if db is not None:
            yield db
        else:
            async with AsyncSessionLocal() as session:
                yield session

    async with _session() as db:
        # Find all readers with unsettled SUCCESS transactions
        reader_ids_result = await db.execute(
            select(EmoneyTransaction.emoney_reader_id)
            .where(
                EmoneyTransaction.settlement_batch_id.is_(None),
                EmoneyTransaction.status == "SUCCESS",
                EmoneyTransaction.emoney_reader_id.isnot(None),
            )
            .distinct()
        )
        reader_ids = [r[0] for r in reader_ids_result.all()]

        if not reader_ids:
            logger.info("generate_settlement_no_transactions")
            return {"status": "success", "files_generated": 0, "total_transactions": 0}

        for reader_id in reader_ids:
            # Get reader details
            reader = await db.get(EmoneyReader, reader_id)
            if not reader or not reader.mid or not reader.tid:
                logger.warning("generate_settlement_skip_no_mid_tid", reader_id=reader_id)
                continue

            # Get unsettled transactions for this reader
            tx_result = await db.execute(
                select(EmoneyTransaction)
                .where(
                    EmoneyTransaction.settlement_batch_id.is_(None),
                    EmoneyTransaction.status == "SUCCESS",
                    EmoneyTransaction.emoney_reader_id == reader_id,
                )
                .order_by(EmoneyTransaction.created_at)
            )
            transactions = tx_result.scalars().all()

            if not transactions:
                continue

            # Get next batch number from Redis (resets daily)
            redis = ctx.get("redis")
            batch_number = 1
            if redis:
                try:
                    batch_key = f"settlement:batch:{reader_id}:{date.today().isoformat()}"
                    current = await redis.get(batch_key)
                    if current:
                        batch_number = int(current) + 1
                    await redis.set(batch_key, str(batch_number), ex=86400)
                except Exception:
                    pass

            now = datetime.now(timezone.utc)
            total_amount = sum(tx.amount_deducted for tx in transactions)

            filename = generate_filename(
                settlement_datetime=now,
                mid=reader.mid,
                tid=reader.tid,
                batch_number=batch_number,
            )

            tx_dicts = [{"raw_response_hex": tx.raw_response_hex or ""} for tx in transactions]
            content = build_settlement_content(tx_dicts, total_amount)

            # Write file
            file_path = os.path.join(SETTLEMENT_DIR, filename)
            with open(file_path, "w", encoding="ascii") as f:
                f.write(content)

            # Compute hash
            file_hash = hashlib.sha256(content.encode("ascii")).hexdigest()

            # Create settlement record
            settlement = EmoneySettlement(
                filename=filename,
                file_path=file_path,
                batch_date=date.today(),
                batch_number=batch_number,
                total_transactions=len(transactions),
                total_amount=total_amount,
                status="GENERATED",
                file_content_hash=file_hash,
            )
            db.add(settlement)
            await db.flush()  # Get settlement.id

            # Link transactions to settlement
            for tx in transactions:
                tx.settlement_batch_id = settlement.id

            await db.commit()

            files_generated += 1
            total_transactions += len(transactions)

            # Increment Prometheus counter
            try:
                _get_settlement_counter().inc()
            except Exception:
                pass

            logger.info(
                "generate_settlement_file_created",
                filename=filename,
                reader_id=reader_id,
                transactions=len(transactions),
                amount=total_amount,
            )

    logger.info(
        "generate_settlement_job_complete",
        files_generated=files_generated,
        total_transactions=total_transactions,
    )

    return {
        "status": "success",
        "files_generated": files_generated,
        "total_transactions": total_transactions,
    }
