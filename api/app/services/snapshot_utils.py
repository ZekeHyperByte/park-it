"""Shared snapshot enqueue utilities."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.logging import get_logger

logger = get_logger("snapshot_utils")


async def enqueue_snapshots_for_gate(
    db: AsyncSession,
    gate_code: str,
    transaction_id: int,
    snapshot_type: str,
) -> None:
    """Enqueue snapshot jobs for all cameras on a gate.

    Args:
        db: Database session
        gate_code: Gate code (e.g., "GIN01", "GOUT01")
        transaction_id: Transaction to link snapshots to
        snapshot_type: "entry" or "exit"
    """
    try:
        from api.app.models import Gate
        from shared.redis import get_arq_redis

        result = await db.execute(select(Gate).where(Gate.code == gate_code))
        gate = result.scalar_one_or_none()
        if gate is None:
            return

        cameras = gate.get_cameras()
        if not cameras:
            return

        arq_redis = await get_arq_redis()
        for idx, cam in enumerate(cameras):
            cam_key = cam.get("label") or str(idx)
            await arq_redis.enqueue_job(
                "take_snapshot",
                gate_id=gate_code,
                camera_url=cam["url"],
                transaction_id=transaction_id,
                snapshot_type=snapshot_type,
                camera_label=cam.get("label"),
                camera_username=cam.get("username"),
                camera_password=cam.get("password"),
                camera_auth_type=cam.get("auth_type", "none"),
                _job_id=f"snapshot:{snapshot_type}:{transaction_id}:{cam_key}",
                _queue_name="arq:queue:critical",
            )

        logger.info(
            f"{snapshot_type}_snapshot_enqueued",
            transaction_id=transaction_id,
            gate_id=gate_code,
            count=len(cameras),
        )
    except Exception as exc:
        logger.warning(
            f"{snapshot_type}_snapshot_enqueue_failed",
            transaction_id=transaction_id,
            gate_id=gate_code,
            error=str(exc),
        )
