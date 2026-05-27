import asyncio
import logging
import traceback
from datetime import datetime, timezone

from src.database import SessionLocal
from src.enums import SyncStatus
from src.models import Event, SyncMetadata
from src.paginator import EventsPaginator
from src.provider_client import EventsProviderClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_events(client=None):
    if client is None:
        client = EventsProviderClient()

    db = SessionLocal()
    sync_meta = None

    try:
        sync_meta = db.query(SyncMetadata).first()
        if not sync_meta:
            sync_meta = SyncMetadata(
                id="sync_state",
                last_changed_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
                sync_status=SyncStatus.IDLE,
            )
            db.add(sync_meta)
            db.commit()
            logger.info("Created new sync metadata")

        sync_meta.sync_status = SyncStatus.RUNNING
        sync_meta.last_sync_time = datetime.now(timezone.utc)
        db.commit()

        last_changed = sync_meta.last_changed_at
        if last_changed.tzinfo is None:
            last_changed = last_changed.replace(tzinfo=timezone.utc)

        logger.info("Starting sync from %s", last_changed)

        paginator = EventsPaginator(client)
        max_changed_at = last_changed
        events_count = 0

        async for event_data in paginator:
            events_count += 1
            changed_at = datetime.fromisoformat(event_data["changed_at"])
            if changed_at > max_changed_at:
                max_changed_at = changed_at

            existing = db.query(Event).filter(Event.id == event_data["id"]).first()

            if existing:
                existing.name = event_data["name"]
                existing.event_time = datetime.fromisoformat(event_data["event_time"])
                existing.registration_deadline = datetime.fromisoformat(
                    event_data["registration_deadline"]
                )
                existing.status = event_data["status"]
                existing.number_of_visitors = event_data.get("number_of_visitors", 0)
                existing.place_id = event_data["place"]["id"]
                existing.place_name = event_data["place"]["name"]
                existing.place_city = event_data["place"]["city"]
                existing.place_address = event_data["place"]["address"]
                existing.place_seats_pattern = event_data["place"]["seats_pattern"]
                existing.changed_at = changed_at
                existing.created_at = datetime.fromisoformat(event_data["created_at"])
                existing.status_changed_at = datetime.fromisoformat(
                    event_data.get("status_changed_at", event_data["changed_at"])
                )
            else:
                event = Event(
                    id=event_data["id"],
                    name=event_data["name"],
                    event_time=datetime.fromisoformat(event_data["event_time"]),
                    registration_deadline=datetime.fromisoformat(
                        event_data["registration_deadline"]
                    ),
                    status=event_data["status"],
                    number_of_visitors=event_data.get("number_of_visitors", 0),
                    place_id=event_data["place"]["id"],
                    place_name=event_data["place"]["name"],
                    place_city=event_data["place"]["city"],
                    place_address=event_data["place"]["address"],
                    place_seats_pattern=event_data["place"]["seats_pattern"],
                    changed_at=changed_at,
                    created_at=datetime.fromisoformat(event_data["created_at"]),
                    status_changed_at=datetime.fromisoformat(
                        event_data.get("status_changed_at", event_data["changed_at"])
                    ),
                )
                db.add(event)

            if events_count % 50 == 0:
                db.commit()
                logger.info("Synced %d events so far...", events_count)

        if sync_meta:
            sync_meta.last_changed_at = max_changed_at
            sync_meta.sync_status = SyncStatus.COMPLETED
        db.commit()

        logger.info(
            "Sync completed. Total events: %d, last changed: %s",
            events_count,
            max_changed_at,
        )

    except Exception as e:
        logger.error("Sync failed: %s\n%s", e, traceback.format_exc())
        if sync_meta:
            sync_meta.sync_status = SyncStatus.FAILED
            db.commit()
        raise
    finally:
        db.close()


async def background_sync_worker():
    logger.info("Background sync worker started")

    for attempt in range(3):
        try:
            await sync_events()
            logger.info("Initial sync completed successfully")
            break
        except Exception as e:
            logger.error("Initial sync attempt %d failed: %s", attempt + 1, e)
            if attempt < 2:
                await asyncio.sleep(10)

    while True:
        await asyncio.sleep(86400)
        try:
            await sync_events()
        except Exception as e:
            logger.error("Periodic sync failed: %s", e)
