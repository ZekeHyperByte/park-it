"""Redis Pub/Sub event consumer for server-side event processing.

Subscribes to parking.events.* and handles business logic for specific event types:
- passti_card_tap: logged (entry flow is daemon-driven)
- deduct_result: delegates to payment service to complete e-money exit
"""

import asyncio
import contextlib
import json

from shared.logging import get_logger
from shared.redis import redis_client

logger = get_logger("event_consumer")


class EventConsumer:
    """Subscribe to Redis pub/sub and process events server-side."""

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the Redis pub/sub listener."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._listen())
        logger.info("event_consumer_started")

    async def stop(self) -> None:
        """Stop the Redis pub/sub listener."""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("event_consumer_stopped")

    async def _listen(self) -> None:
        """Listen for Redis pub/sub messages."""
        await redis_client.connect()
        pubsub = redis_client.client.pubsub()
        await pubsub.psubscribe("parking.events.*")

        try:
            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] == "pmessage":
                    channel = message["channel"]
                    data = message["data"]
                    await self._handle_message(channel, data)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("event_consumer_listen_error", error=str(e))
        finally:
            await pubsub.punsubscribe("parking.events.*")
            await pubsub.close()

    async def _handle_message(self, channel: str, data: str) -> None:
        """Handle a Redis pub/sub message."""
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("event_consumer_invalid_json", channel=channel, data=data)
            return

        event_type = payload.get("event_type")
        if event_type is None:
            logger.warning("event_consumer_missing_event_type", channel=channel, payload=payload)
            return

        if event_type == "passti_card_tap":
            await self._handle_passti_card_tap(payload)
        elif event_type == "ticket_button_pressed":
            await self._handle_ticket_button_pressed(payload)
        elif event_type == "rfid_card_read":
            await self._handle_rfid_card_read(payload)
        elif event_type == "emoney_print_decision":
            await self._handle_emoney_print_decision(payload)
        elif event_type == "deduct_result":
            await self._handle_deduct_result(payload)
        elif event_type == "vehicle_detected":
            await self._handle_vehicle_detected(payload)
        elif event_type == "help_button_pressed":
            await self._handle_help_button_pressed(payload)
        else:
            pass

    async def _handle_passti_card_tap(self, payload: dict) -> None:
        """Handle passti_card_tap event.

        The entry gate daemon drives the entry flow (sends check_balance and
        waits for response). For now we just log the tap.
        """
        gate_id = payload.get("gate_id", "unknown")
        card_number = payload.get("card_number", "unknown")
        card_type = payload.get("card_type", "unknown")
        logger.info(
            "passti_card_tap_received",
            gate_id=gate_id,
            card_number=card_number,
            card_type=card_type,
        )

    async def _handle_emoney_print_decision(self, event: dict) -> None:
        """Handle print decision at entry gate — create transaction and open gate."""
        from sqlalchemy import select

        from api.app.models import Gate
        from api.app.services.gate_command import publish_command
        from api.app.services.transaction import create_entry_transaction
        from api.database import AsyncSessionLocal
        from shared.events import OpenGateCommand

        gate_code = event.get("gate_id", "")
        card_number = event.get("card_number", "")

        logger.info("entry_emoney_decision", gate_id=gate_code, card_number=card_number)

        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(Gate).where(Gate.code == gate_code))
                gate = result.scalar_one_or_none()
                if gate is None:
                    logger.error("entry_emoney_gate_not_found", gate_id=gate_code)
                    return

                tx = await create_entry_transaction(
                    db,
                    gate_in_id=gate.id,
                    card_number=card_number,
                    payment_method="EMONEY",
                )
                await db.commit()

                await publish_command(OpenGateCommand(gate_id=gate_code))
                logger.info("entry_emoney_gate_opened", gate_id=gate_code, transaction_id=tx.id)
            except Exception as e:
                logger.error("entry_emoney_decision_error", gate_id=gate_code, error=str(e))

    async def _handle_deduct_result(self, payload: dict) -> None:
        """Handle deduct_result event by processing the e-money payment."""
        from sqlalchemy import select

        from api.app.models import Gate
        from api.app.services.payment import process_emoney_result
        from api.database import AsyncSessionLocal
        from shared.events import DeductStatus

        gate_id = payload.get("gate_id")
        if gate_id is None:
            logger.error("deduct_result_missing_gate_id", payload=payload)
            return

        async with AsyncSessionLocal() as db:
            try:
                # Look up gate by code to obtain the integer DB id
                result = await db.execute(select(Gate).where(Gate.code == gate_id))
                gate = result.scalar_one_or_none()
                if gate is None:
                    logger.error("deduct_result_gate_not_found", gate_id=gate_id)
                    return

                status_str = payload.get("status")
                try:
                    status = DeductStatus(status_str)
                except ValueError:
                    logger.error(
                        "deduct_result_invalid_status",
                        gate_id=gate_id,
                        status=status_str,
                    )
                    return

                await process_emoney_result(
                    db,
                    gate_id=gate_id,
                    gate_out_id=gate.id,
                    card_number=payload.get("card_number", ""),
                    status=status,
                    deduct_amount=payload.get("deduct_amount", 0),
                    balance_before=payload.get("balance_before", 0),
                    balance_after=payload.get("balance_after", 0),
                    transaction_counter=payload.get("transaction_counter", 0),
                    raw_response_hex=payload.get("raw_response_hex", ""),
                    settlement_payload_hex=payload.get("settlement_payload_hex", ""),
                    card_type=payload.get("card_type"),
                    card_type_code=(
                        payload.get("card_type_code") or None
                    ),
                )

                from api.app.services.gate_command import publish_command
                from shared.events import PlayAudioCommand
                if status == DeductStatus.WRONG_CARD:
                    await publish_command(PlayAudioCommand(gate_id=gate_id, track=7))
                elif status == DeductStatus.INSUFFICIENT_BALANCE:
                    await publish_command(PlayAudioCommand(gate_id=gate_id, track=6))

                logger.info(
                    "deduct_result_processed",
                    gate_id=gate_id,
                    gate_out_id=gate.id,
                    status=status.value,
                )
            except Exception as e:
                logger.error(
                    "deduct_result_processing_error",
                    gate_id=gate_id,
                    error=str(e),
                )


    async def _handle_ticket_button_pressed(self, payload: dict) -> None:
        """Cash entry: create transaction, send print_ticket_then_open to daemon."""
        import uuid

        from sqlalchemy import select

        from api.app.models import Gate
        from api.app.services.gate_command import publish_command
        from api.app.services.transaction import create_entry_transaction
        from api.database import AsyncSessionLocal
        from shared.events import PrintTicketThenOpenCommand

        gate_code = payload.get("gate_id", "")
        logger.info("ticket_button_pressed_received", gate_id=gate_code)

        async with AsyncSessionLocal() as db:
            try:
                result = await db.execute(select(Gate).where(Gate.code == gate_code))
                gate = result.scalar_one_or_none()
                if gate is None:
                    logger.error("ticket_button_gate_not_found", gate_id=gate_code)
                    return

                barcode = uuid.uuid4().hex[:12].upper()
                tx = await create_entry_transaction(
                    db,
                    barcode=barcode,
                    gate_in_id=gate.id,
                    payment_method="CASH",
                )
                await db.commit()

                await publish_command(
                    PrintTicketThenOpenCommand(
                        gate_id=gate_code,
                        barcode=tx.barcode,
                        gate_name=gate.name,
                    )
                )
                logger.info("cash_entry_ticket_sent", gate_id=gate_code, barcode=tx.barcode)
            except Exception as e:
                logger.error("ticket_button_error", gate_id=gate_code, error=str(e))

    async def _handle_rfid_card_read(self, payload: dict) -> None:
        """RFID/UHF card read — branches on gate direction: entry creates tx, exit closes tx."""
        from datetime import date

        from sqlalchemy import select

        from api.app.models import Gate, Member, ParkingTransaction
        from api.app.services.gate_command import publish_command
        from api.app.services.transaction import create_entry_transaction
        from api.database import AsyncSessionLocal
        from shared.events import DisplayTextCommand, OpenGateCommand, PlayAudioCommand, RejectCardCommand

        gate_code = payload.get("gate_id", "")
        card_number = payload.get("card_number", "")
        logger.info("rfid_card_read_received", gate_id=gate_code, card=card_number)

        async with AsyncSessionLocal() as db:
            try:
                gate_result = await db.execute(select(Gate).where(Gate.code == gate_code))
                gate = gate_result.scalar_one_or_none()
                if gate is None:
                    logger.error("rfid_gate_not_found", gate_id=gate_code)
                    return

                if gate.direction == "OUT":
                    # Exit: close active transaction, fee=0, open gate
                    from api.app.services.payment import process_rfid_payment
                    try:
                        await process_rfid_payment(
                            db,
                            gate_id=gate_code,
                            gate_out_id=gate.id,
                            card_number=card_number,
                        )
                        await db.commit()
                        logger.info("rfid_exit_gate_opened", gate_id=gate_code)
                    except ValueError as e:
                        msg = str(e)
                        if "No active transaction" in msg:
                            await publish_command(DisplayTextCommand(gate_id=gate_code, line1="Tidak Ada", line2="Transaksi Aktif"))
                        else:
                            await publish_command(DisplayTextCommand(gate_id=gate_code, line1="Kartu Tidak", line2="Valid"))
                        await publish_command(PlayAudioCommand(gate_id=gate_code, track=3))
                        logger.warning("rfid_exit_rejected", gate_id=gate_code, reason=msg)
                    return

                # Entry: validate member, create transaction, open gate
                member_result = await db.execute(
                    select(Member).where(Member.card_number == card_number)
                )
                member = member_result.scalar_one_or_none()

                if member is None:
                    await publish_command(RejectCardCommand(gate_id=gate_code, line1="Kartu Tidak", line2="Terdaftar", audio_track=3))
                    logger.info("rfid_member_not_found", gate_id=gate_code, card=card_number)
                    return

                if not member.is_active:
                    await publish_command(RejectCardCommand(gate_id=gate_code, line1="Kartu Tidak", line2="Aktif", audio_track=4))
                    return

                if member.valid_until and member.valid_until < date.today():
                    await publish_command(RejectCardCommand(gate_id=gate_code, line1="Kartu Expired", line2="", audio_track=3))
                    logger.info("rfid_member_expired", gate_id=gate_code, card=card_number)
                    return

                # Check for unclosed active transaction
                unclosed = await db.execute(
                    select(ParkingTransaction).where(
                        ParkingTransaction.card_number == card_number,
                        ParkingTransaction.status == "ACTIVE",
                    )
                )
                if unclosed.scalar_one_or_none():
                    await publish_command(RejectCardCommand(gate_id=gate_code, line1="Transaksi", line2="Belum Selesai", audio_track=11))
                    logger.info("rfid_unclosed_transaction", gate_id=gate_code, card=card_number)
                    return

                # Expiry warning — warn but allow entry (matches legacy MT00011/MT00012 behavior)
                if member.valid_until:
                    days_left = (member.valid_until - date.today()).days
                    if days_left == 1:
                        await publish_command(DisplayTextCommand(gate_id=gate_code, line1="Kartu Habis", line2="Dalam 1 Hari"))
                        await publish_command(PlayAudioCommand(gate_id=gate_code, track=12))
                        await asyncio.sleep(6)
                    elif days_left == 5:
                        await publish_command(DisplayTextCommand(gate_id=gate_code, line1="Kartu Habis", line2="Dalam 5 Hari"))
                        await publish_command(PlayAudioCommand(gate_id=gate_code, track=11))
                        await asyncio.sleep(6)

                await create_entry_transaction(
                    db,
                    card_number=card_number,
                    gate_in_id=gate.id,
                    payment_method="RFID_MEMBER",
                    member_id=member.id,
                    vehicle_type_id=member.vehicle_type_id,
                    plate_number=member.plate_number,
                )
                await db.commit()

                await publish_command(OpenGateCommand(gate_id=gate_code))
                logger.info("rfid_entry_gate_opened", gate_id=gate_code, member_id=member.id)
            except Exception as e:
                logger.error("rfid_card_read_error", gate_id=gate_code, error=str(e))

    async def _handle_help_button_pressed(self, payload: dict) -> None:
        """Operator assistance requested at gate."""
        gate_id = payload.get("gate_id", "")
        logger.warning("help_button_pressed", gate_id=gate_id)

    async def _handle_vehicle_detected(self, payload: dict) -> None:
        """Handle vehicle_detected event — logged for monitoring."""
        gate_id = payload.get("gate_id", "")
        logger.info("vehicle_detected_received", gate_id=gate_id)


# Global instance
event_consumer = EventConsumer()
