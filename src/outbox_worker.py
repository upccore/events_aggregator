import asyncio
import logging

from src.capashino_client import CapashinoClient
from src.config import OUTBOX_MAX_RETRIES, OUTBOX_WORKER_INTERVAL
from src.database import SessionLocal
from src.enums import OutboxStatus
from src.models import OutboxEvent

logger = logging.getLogger(__name__)


async def process_outbox():
    db = SessionLocal()
    try:
        pending = (
            db.query(OutboxEvent)
            .filter(
                OutboxEvent.status == OutboxStatus.PENDING,
                OutboxEvent.attempts < OUTBOX_MAX_RETRIES,
            )
            .all()
        )

        client = CapashinoClient()

        for event in pending:
            try:
                payload = event.payload
                await client.send_notification(
                    message=payload["message"],
                    reference_id=payload["reference_id"],
                    idempotency_key=payload["idempotency_key"],
                )
                event.status = OutboxStatus.SENT
                logger.info("Outbox event %s sent successfully", event.id)
            except Exception as e:
                event.attempts += 1
                logger.error(
                    "Failed to send outbox event %s (attempt %d): %s",
                    event.id,
                    event.attempts,
                    e,
                )

        db.commit()
    except Exception as e:
        logger.error("Outbox worker error: %s", e)
        db.rollback()
    finally:
        db.close()


async def background_outbox_worker():
    logger.info("Outbox worker started")
    while True:
        await process_outbox()
        await asyncio.sleep(OUTBOX_WORKER_INTERVAL)
