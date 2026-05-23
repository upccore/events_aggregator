import asyncio
import logging
from datetime import datetime, timezone

from src.database import SessionLocal
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
                sync_status="idle",
            )
            db.add(sync_meta)
            db.commit()

        sync_meta.sync_status = "running"
        sync_meta.last_sync_time = datetime.now(timezone.utc)
        db.commit()

        last_changed = sync_meta.last_changed_at
        if last_changed.tzinfo is None:
            last_changed = last_changed.replace(tzinfo=timezone.utc)

        paginator = EventsPaginator(client)
        max_changed_at = last_changed

        async for event_data in paginator:
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

        if sync_meta:
            sync_meta.last_changed_at = max_changed_at
            sync_meta.sync_status = "completed"
            db.commit()

        logger.info(f"Sync completed. Events updated up to {max_changed_at}")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        if sync_meta:
            sync_meta.sync_status = "failed"
            db.commit()
        raise
    finally:
        db.close()


async def background_sync_worker():
    client = EventsProviderClient()

    try:
        await sync_events(client)
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")

    while True:
        await asyncio.sleep(86400)
        try:
            await sync_events(client)
        except Exception as e:
            logger.error(f"Periodic sync failed: {e}")
