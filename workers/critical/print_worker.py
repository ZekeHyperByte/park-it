"""Critical print worker jobs."""

from arq import Retry

from shared.logging import get_logger

logger = get_logger("print_worker")


async def print_ticket(ctx, gate_id: str, barcode: str, gate_name: str = "") -> dict:
    """Print an entry ticket.

    Stub implementation — actual ESC/POS logic in Week 4.
    """
    logger.info(
        "print_ticket_job",
        gate_id=gate_id,
        barcode=barcode,
        gate_name=gate_name,
    )
    # TODO: Implement ESC/POS printing in Week 4
    return {"status": "success", "message": "Ticket printed (stub)"}


async def print_receipt(ctx, gate_id: str, transaction_data: dict) -> dict:
    """Print an exit receipt.

    Stub implementation — actual ESC/POS logic in Week 4.
    """
    logger.info(
        "print_receipt_job",
        gate_id=gate_id,
        transaction_id=transaction_data.get("id"),
    )
    # TODO: Implement ESC/POS printing in Week 4
    return {"status": "success", "message": "Receipt printed (stub)"}
