"""Settlement file generation utilities."""

from datetime import datetime


def generate_filename(
    settlement_datetime: datetime,
    mid: str,
    tid: str,
    batch_number: int,
) -> str:
    """Generate settlement filename per Multibank v1.3 spec.

    Format: YYYYMMDDHHMMSS + MID(16, left-pad 0) + TID(8, left-pad 0) + Version(2) + BatchNo(3) + .txt
    """
    date_part = settlement_datetime.strftime("%Y%m%d%H%M%S")
    mid_padded = mid.zfill(16)
    tid_padded = tid.zfill(8)
    version = "01"
    batch_padded = str(batch_number).zfill(3)
    return f"{date_part}{mid_padded}{tid_padded}{version}{batch_padded}.txt"


def build_settlement_content(
    transactions: list[dict],
    total_amount: int,
) -> str:
    """Build settlement file content per Multibank v1.3 spec.

    Header: TrxCount(3) + TrxAmount(10) + LF
    Body: TransactionLog(n) + LF per transaction
    """
    trx_count = len(transactions)
    header = f"{str(trx_count).zfill(3)}{str(total_amount).zfill(10)}\n"

    body_lines = []
    for tx in transactions:
        raw_hex = tx.get("raw_response_hex", "")
        body_lines.append(f"{raw_hex}\n")

    return header + "".join(body_lines)
