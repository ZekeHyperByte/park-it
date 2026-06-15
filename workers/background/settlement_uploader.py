"""Settlement upload and response processing for Multibank v1.3 §I + §II.

Two responsibilities live here:

1. **Upload** generated settlement files to the bank via SFTP. Atomic delivery
   pattern: write to ``<file>.partial`` then rename → bank polling never sees
   a half-written file.

2. **Poll** the bank's response files (``<basename>.OK`` / ``.NOK``) and
   reconcile per-transaction status onto the EmoneyTransaction rows.

Configuration is read from shared.config.Settings; see the
``settlement_sftp_*`` keys.
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from shared.logging import get_logger

logger = get_logger("settlement_uploader")

# Multibank v1.3 §II — Response Transaction Data, Status field
RESPONSE_STATUS_CODES: dict[str, str] = {
    "00": "Accepted",
    "01": "Invalid Format",
    "02": "Duplicate Data",
    "03": "Transaction count mismatch",
    "04": "Transaction amount mismatch",
    "05": "Invalid Merchant Terminal",
    "07": "Data Corrupt",
    "08": "Invalid Device SN",
    "09": "Invalid Bank Log",
    "10": "Invalid Filename Format",
    "11": "Invalid Header Format",
}


# ---------------------------------------------------------------------------
# Response file parsing (kept pure for unit tests)
# ---------------------------------------------------------------------------


def parse_ok_response(content: str) -> dict[str, Any]:
    """Parse a Multibank v1.3 §II response file body (.OK or .NOK).

    Format:
        Line 0: TrxType(2) + TrxCount(3) — header
        Line N: <settlement_payload_hex><status(2)>

    Returns a dict::

        {
            "trx_type": "01",
            "trx_count": 123,
            "results": [
                {
                    "settlement_payload_hex": "01...",
                    "status": "00",
                    "status_description": "Accepted",
                },
                ...
            ],
        }
    """
    lines = content.strip().split("\n")
    if not lines or len(lines[0]) < 5:
        return {"trx_type": "", "trx_count": 0, "results": []}

    header = lines[0]
    trx_type = header[:2]
    try:
        trx_count = int(header[2:5])
    except ValueError:
        trx_count = 0

    results: list[dict[str, str]] = []
    for line in lines[1:]:
        if len(line) < 2:
            continue
        status = line[-2:]
        payload = line[:-2]
        results.append(
            {
                "settlement_payload_hex": payload.upper(),
                "status": status,
                "status_description": RESPONSE_STATUS_CODES.get(status, "Unknown"),
            }
        )

    return {"trx_type": trx_type, "trx_count": trx_count, "results": results}


def parse_nok_response(content: str) -> dict[str, Any]:
    """Parse a .NOK response file. Same format as .OK; semantically all
    transactions are rejected (header status applies file-wide)."""
    return parse_ok_response(content)


# ---------------------------------------------------------------------------
# SFTP transport
# ---------------------------------------------------------------------------


def _have_asyncssh() -> bool:
    try:
        import asyncssh  # noqa: F401

        return True
    except ImportError:
        return False


@asynccontextmanager
async def _sftp_session(
    host: str,
    port: int,
    username: str,
    key_path: str,
    known_hosts: str | None,
    connect_timeout: int = 30,
):
    """Yield an open SFTP client. Raises on auth/connect failure."""
    import asyncssh

    async with asyncssh.connect(
        host=host,
        port=port,
        username=username,
        client_keys=[key_path] if key_path else None,
        known_hosts=known_hosts if known_hosts else None,
        connect_timeout=connect_timeout,
    ) as conn:
        async with conn.start_sftp_client() as sftp:
            yield sftp


async def upload_settlement_file(
    file_path: str,
    *,
    host: str,
    port: int = 22,
    username: str,
    key_path: str,
    known_hosts: str | None = None,
    remote_dir: str = "/",
    connect_timeout: int = 30,
) -> bool:
    """Upload a settlement file via SFTP using atomic .partial→rename.

    Returns True on success. Raises asyncssh exceptions on connect/auth/IO
    failure so the caller (ARQ retry policy) can decide whether to retry.

    The bank polls the inbox for files matching the multibank filename pattern;
    writing to ``<name>.partial`` first and renaming on completion guarantees
    that polling never sees a half-written file.
    """
    if not Path(file_path).is_file():
        logger.error("settlement_upload_no_file", file_path=file_path)
        return False

    if not _have_asyncssh():
        logger.error("settlement_upload_asyncssh_missing")
        raise RuntimeError("asyncssh is required for SFTP upload")

    remote_name = os.path.basename(file_path)
    remote_dir = remote_dir.rstrip("/") or "/"
    tmp_remote = f"{remote_dir}/{remote_name}.partial"
    final_remote = f"{remote_dir}/{remote_name}"

    logger.info(
        "settlement_upload_start",
        file_path=file_path,
        host=host,
        remote=final_remote,
    )

    async with _sftp_session(
        host=host,
        port=port,
        username=username,
        key_path=key_path,
        known_hosts=known_hosts,
        connect_timeout=connect_timeout,
    ) as sftp:
        # Best-effort cleanup of any stale .partial from a previous run.
        try:
            await sftp.remove(tmp_remote)
        except Exception:
            pass
        await sftp.put(file_path, tmp_remote)
        await sftp.rename(tmp_remote, final_remote)

    logger.info("settlement_upload_complete", file_path=file_path, remote=final_remote)
    return True


async def fetch_response_file(
    settlement_filename: str,
    *,
    host: str,
    port: int = 22,
    username: str,
    key_path: str,
    known_hosts: str | None = None,
    remote_dir: str = "/",
    connect_timeout: int = 30,
) -> tuple[str | None, str | None]:
    """One-shot fetch attempt for the matching .OK/.NOK response file.

    Returns ``(extension, content)`` on hit (extension is "OK" or "NOK"),
    or ``(None, None)`` if neither file exists yet.

    The bank may write either file, so we try .OK first then .NOK.
    """
    import asyncssh

    base = settlement_filename
    if base.lower().endswith(".txt"):
        base = base[:-4]

    remote_dir = remote_dir.rstrip("/") or "/"

    async with _sftp_session(
        host=host,
        port=port,
        username=username,
        key_path=key_path,
        known_hosts=known_hosts,
        connect_timeout=connect_timeout,
    ) as sftp:
        for ext in ("OK", "NOK"):
            remote = f"{remote_dir}/{base}.{ext}"
            try:
                # asyncssh has no "read into memory" helper; use a temp file.
                local_tmp = f"/tmp/{base}.{ext}.fetched"
                await sftp.get(remote, local_tmp)
            except (FileNotFoundError, asyncssh.SFTPNoSuchFile):
                continue
            except OSError:
                # Some asyncssh versions raise plain OSError for "no such file".
                continue

            try:
                with open(local_tmp, encoding="ascii") as f:
                    content = f.read()
            finally:
                try:
                    os.remove(local_tmp)
                except OSError:
                    pass
            return ext, content

    return None, None


# ---------------------------------------------------------------------------
# ARQ jobs
# ---------------------------------------------------------------------------


async def upload_settlement_job(ctx: dict, settlement_id: int) -> dict:
    """ARQ job: upload one EmoneySettlement file by ID.

    Marks status UPLOADED on success; raises on failure so ARQ retries.
    """
    from shared.config import get_settings

    from api.app.models.emoney_settlement import EmoneySettlement
    from api.database import AsyncSessionLocal

    settings = get_settings()

    if not settings.settlement_sftp_host:
        logger.warning("settlement_upload_no_host_configured", settlement_id=settlement_id)
        return {"status": "skipped", "reason": "no_sftp_host"}

    async with AsyncSessionLocal() as db:
        settlement = await db.get(EmoneySettlement, settlement_id)
        if settlement is None:
            logger.warning("settlement_upload_not_found", settlement_id=settlement_id)
            return {"status": "error", "reason": "not_found"}

        if settlement.status not in ("GENERATED", "FAILED"):
            logger.info(
                "settlement_upload_skip_state",
                settlement_id=settlement_id,
                status=settlement.status,
            )
            return {"status": "skipped", "reason": f"state={settlement.status}"}

        try:
            await upload_settlement_file(
                file_path=settlement.file_path,
                host=settings.settlement_sftp_host,
                port=settings.settlement_sftp_port,
                username=settings.settlement_sftp_username,
                key_path=settings.settlement_sftp_key_path,
                known_hosts=settings.settlement_sftp_known_hosts or None,
                remote_dir=settings.settlement_sftp_remote_dir,
                connect_timeout=settings.settlement_sftp_connect_timeout,
            )
        except Exception as e:
            logger.error(
                "settlement_upload_failed",
                settlement_id=settlement_id,
                error=str(e),
            )
            settlement.status = "FAILED"
            await db.commit()
            raise

        settlement.status = "UPLOADED"
        settlement.uploaded_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info("settlement_upload_job_done", settlement_id=settlement_id)
        return {"status": "success", "settlement_id": settlement_id}


async def poll_settlement_responses(ctx: dict) -> dict:
    """ARQ cron job: poll bank SFTP for .OK/.NOK responses on UPLOADED files.

    For each match: parse, set per-transaction bank_response_status, update
    settlement status to ACKED_OK / ACKED_NOK / PARTIAL.
    """
    from sqlalchemy import select

    from shared.config import get_settings

    from api.app.models.emoney_settlement import EmoneySettlement
    from api.app.models.emoney_transaction import EmoneyTransaction
    from api.database import AsyncSessionLocal

    settings = get_settings()
    if not settings.settlement_sftp_host:
        logger.info("settlement_poll_no_host_configured")
        return {"status": "skipped", "reason": "no_sftp_host"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    processed = 0
    acked_ok = 0
    acked_nok = 0
    partial = 0

    async with AsyncSessionLocal() as db:
        pending = await db.execute(
            select(EmoneySettlement)
            .where(
                EmoneySettlement.status == "UPLOADED",
                EmoneySettlement.uploaded_at.is_not(None),
                EmoneySettlement.uploaded_at >= cutoff,
            )
            .order_by(EmoneySettlement.uploaded_at)
        )
        for settlement in pending.scalars():
            try:
                ext, content = await fetch_response_file(
                    settlement_filename=settlement.filename,
                    host=settings.settlement_sftp_host,
                    port=settings.settlement_sftp_port,
                    username=settings.settlement_sftp_username,
                    key_path=settings.settlement_sftp_key_path,
                    known_hosts=settings.settlement_sftp_known_hosts or None,
                    remote_dir=settings.settlement_sftp_response_dir,
                    connect_timeout=settings.settlement_sftp_connect_timeout,
                )
            except Exception as e:
                logger.warning(
                    "settlement_poll_fetch_error",
                    settlement_id=settlement.id,
                    error=str(e),
                )
                continue

            if ext is None:
                continue

            parsed = (
                parse_ok_response(content) if ext == "OK" else parse_nok_response(content)
            )
            results = parsed["results"]

            # Build a lookup from settlement_payload_hex → status code.
            status_by_payload = {
                r["settlement_payload_hex"]: r["status"] for r in results
            }

            tx_rows = await db.execute(
                select(EmoneyTransaction).where(
                    EmoneyTransaction.settlement_batch_id == settlement.id
                )
            )
            ok_count = nok_count = 0
            now_utc = datetime.now(timezone.utc)
            for tx in tx_rows.scalars():
                payload_key = (tx.settlement_payload_hex or "").upper()
                code = status_by_payload.get(payload_key)
                if code is None:
                    # Bank didn't enumerate this row; mark as response-missing.
                    code = "??"
                tx.bank_response_status = code
                tx.bank_response_at = now_utc
                if code == "00":
                    ok_count += 1
                else:
                    nok_count += 1

            if ext == "NOK" or ok_count == 0:
                settlement.status = "ACKED_NOK"
                acked_nok += 1
            elif nok_count == 0:
                settlement.status = "ACKED_OK"
                acked_ok += 1
            else:
                settlement.status = "PARTIAL"
                partial += 1
            settlement.response_received_at = now_utc
            settlement.response_extension = ext

            processed += 1
            await db.commit()

    logger.info(
        "settlement_poll_done",
        processed=processed,
        acked_ok=acked_ok,
        acked_nok=acked_nok,
        partial=partial,
    )
    return {
        "status": "success",
        "processed": processed,
        "acked_ok": acked_ok,
        "acked_nok": acked_nok,
        "partial": partial,
    }



