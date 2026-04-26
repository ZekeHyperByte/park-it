"""Settlement upload and response processing."""

import asyncio
from datetime import datetime, timezone

from shared.logging import get_logger

logger = get_logger("settlement_uploader")

# Response status code mapping
RESPONSE_STATUS_CODES = {
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


def parse_ok_response(content: str) -> list[dict]:
    """Parse .OK response file.

    Format:
    01XXX     <- header: type + count
    <raw_data><status>  <- per transaction
    """
    lines = content.strip().split("\n")
    if not lines:
        return []

    header = lines[0]
    if len(header) < 5:
        return []

    count = int(header[2:5])
    results = []

    for line in lines[1:]:
        if len(line) < 2:
            continue
        status = line[-2:]
        raw_data = line[:-2]
        results.append({
            "status": status,
            "status_description": RESPONSE_STATUS_CODES.get(status, "Unknown"),
            "raw_data": raw_data,
        })

    return results


def parse_nok_response(content: str) -> list[dict]:
    """Parse .NOK response file. Same format as .OK but all rejected."""
    return parse_ok_response(content)


async def upload_settlement_file(
    file_path: str,
    remote_host: str,
    remote_username: str,
    remote_key_path: str,
    remote_dir: str = "/",
) -> bool:
    """Upload settlement file via SFTP.

    Stub: logs the action. Full asyncssh implementation can be added
    when SFTP credentials are available.
    """
    logger.info(
        "settlement_upload_start",
        file_path=file_path,
        remote_host=remote_host,
        remote_dir=remote_dir,
    )
    # TODO: Implement asyncssh SFTP upload when credentials available
    # import asyncssh
    # async with asyncssh.connect(remote_host, username=remote_username, client_keys=[remote_key_path]) as conn:
    #     async with conn.start_sftp_client() as sftp:
    #         await sftp.put(file_path, f"{remote_dir}/{os.path.basename(file_path)}")
    logger.info("settlement_upload_complete", file_path=file_path)
    return True


async def poll_for_response(
    settlement_filename: str,
    remote_host: str,
    remote_username: str,
    remote_key_path: str,
    remote_dir: str = "/",
    max_attempts: int = 24,
    interval_seconds: int = 300,
) -> tuple[str | None, str | None]:
    """Poll for .OK or .NOK response file.

    Returns (response_type, content) or (None, None) if timeout.
    """
    base_name = settlement_filename.replace(".txt", "")
    ok_name = f"{base_name}.OK"
    nok_name = f"{base_name}.NOK"

    for attempt in range(max_attempts):
        logger.info("settlement_poll_attempt", attempt=attempt + 1, max=max_attempts)
        # TODO: Implement SFTP list/get when credentials available
        # For now, return None to indicate pending
        await asyncio.sleep(interval_seconds)

    logger.warning("settlement_poll_timeout", settlement=settlement_filename)
    return None, None
