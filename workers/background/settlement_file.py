"""Settlement file generation utilities — Multibank v1.3.

Spec reference: "Format File Settlement Multibank v1.3" §I.
"""

from datetime import datetime


def generate_filename(
    settlement_datetime: datetime,
    mid: str,
    tid: str,
    batch_number: int,
) -> str:
    """Generate settlement filename per Multibank v1.3 §I.

    Format: YYYYMMDDHHMMSS + MID(16, left-pad 0) + TID(8, left-pad 0)
            + Version(2) + BatchNo(3) + .txt

    The settlement_datetime should be in Asia/Jakarta (operational timezone)
    so that filename date matches the batch counter day.
    """
    date_part = settlement_datetime.strftime("%Y%m%d%H%M%S")
    mid_padded = mid.zfill(16)
    tid_padded = tid.zfill(8)
    version = "01"
    batch_padded = f"{batch_number:03d}"
    return f"{date_part}{mid_padded}{tid_padded}{version}{batch_padded}.txt"


def build_settlement_content(
    transactions: list[dict],
    total_amount: int,
) -> str:
    """Build settlement file content per Multibank v1.3 §I.

    Each transaction dict must provide a 'settlement_payload_hex' key holding
    the deduct response body from cardtype byte through CardLog Transaction
    (i.e. the PASSTI deduct-response Data section, *excluding* the frame
    envelope STX/LEN/RespCode/StatusCode/LRC).

    Header: TrxCount(3) + TrxAmount(10) + LF
    Body: each transaction's payload hex + LF

    Args:
        transactions: list of dicts with key 'settlement_payload_hex' (string)
        total_amount: sum of all amount_deducted across transactions, in IDR.

    Returns:
        Full settlement file content as a string.
    """
    trx_count = len(transactions)
    if trx_count > 999:
        raise ValueError(
            f"Multibank v1.3 §I: max 999 transactions per file, got {trx_count}. "
            "Caller must split into multiple batches."
        )
    if total_amount < 0 or total_amount > 9_999_999_999:
        raise ValueError(
            f"Total amount {total_amount} out of range for 10-digit field."
        )

    header = f"{trx_count:03d}{total_amount:010d}\n"
    body_lines = [
        f"{(tx.get('settlement_payload_hex') or '').upper()}\n"
        for tx in transactions
    ]
    return header + "".join(body_lines)
