"""Background notification worker jobs."""

import httpx

from shared.config import get_settings
from shared.logging import get_logger

logger = get_logger("notification_worker")


def _get_api_base() -> str:
    """Get Telegram API base URL from settings."""
    settings = get_settings()
    token = settings.telegram_bot_token
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not configured")
    return f"https://api.telegram.org/bot{token}"


async def send_telegram_alert(
    ctx,
    chat_id: str,
    message: str,
    parse_mode: str = "HTML",
) -> dict:
    """Send a Telegram alert message.

    Args:
        chat_id: Telegram chat ID (can be group or channel)
        message: Message text (HTML format supported)
        parse_mode: 'HTML', 'Markdown', or 'MarkdownV2'
    """
    logger.info("telegram_alert_start", chat_id=chat_id)

    url = f"{_get_api_base()}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": parse_mode,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
    except Exception as e:
        logger.error("telegram_alert_failed", error=str(e), chat_id=chat_id)
        return {"status": "error", "message": str(e)}

    if not result.get("ok"):
        logger.error("telegram_api_error", result=result)
        return {"status": "error", "message": result.get("description", "Unknown error")}

    logger.info("telegram_alert_sent", chat_id=chat_id, message_id=result["result"]["message_id"])
    return {"status": "success", "message_id": result["result"]["message_id"]}


async def send_gate_timeout_alert(
    ctx,
    chat_id: str,
    gate_id: str,
    gate_name: str,
    waiting_seconds: int,
    snapshot_url: str | None = None,
) -> dict:
    """Send a formatted gate timeout alert."""
    minutes = waiting_seconds // 60
    message = (
        f"<b>Gate Timeout Alert</b>\n\n"
        f"Gate: <code>{gate_name}</code>\n"
        f"Waiting: <b>{minutes} minutes</b>\n\n"
        f"Please check the POS or open the gate manually."
    )
    return await send_telegram_alert(ctx, chat_id, message)


async def send_hardware_failure_alert(
    ctx,
    chat_id: str,
    gate_id: str,
    gate_name: str,
    component: str,
    error_message: str,
) -> dict:
    """Send a formatted hardware failure alert."""
    message = (
        f"<b>Hardware Failure Alert</b>\n\n"
        f"Gate: <code>{gate_name}</code>\n"
        f"Component: <b>{component}</b>\n"
        f"Error: <code>{error_message}</code>\n\n"
        f"Please check the device immediately."
    )
    return await send_telegram_alert(ctx, chat_id, message)
