import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.cache import seats_cache
from src.enums import EventStatus
from src.models import Event, Ticket
from src.provider_client import EventsProviderClient

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    pass


class BusinessLogicError(Exception):
    pass


def get_events_list(
    db: Session,
    date_from_dt: Optional[datetime],
    page: int,
    page_size: int,
) -> tuple[int, list[Event]]:
    query = db.query(Event)
    if date_from_dt:
        query = query.filter(Event.event_time >= date_from_dt)
    total = query.count()
    events = (
        query.order_by(Event.event_time)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return total, events


def get_event_by_id(db: Session, event_id: str) -> Event:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundError(f"Event {event_id} not found")
    return event


async def get_event_seats(db: Session, event_id: str) -> list[str]:
    cached = seats_cache.get(f"seats_{event_id}")
    if cached:
        return cached

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundError(f"Event {event_id} not found")

    if event.status != EventStatus.PUBLISHED:
        raise BusinessLogicError("Event is not published")

    client = EventsProviderClient()
    seats = await client.get_seats(event_id)
    seats_cache.set(f"seats_{event_id}", seats, ttl_seconds=30)
    return seats


async def register_ticket(
    db: Session,
    event_id: str,
    first_name: str,
    last_name: str,
    email: str,
    seat: str,
) -> str:
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise NotFoundError(f"Event {event_id} not found")

    if event.status != EventStatus.PUBLISHED:
        raise BusinessLogicError("Event is not published")

    client = EventsProviderClient()
    ticket_id = await client.register(
        event_id=event_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        seat=seat,
    )

    ticket = Ticket(ticket_id=ticket_id, event_id=event_id)
    db.add(ticket)
    db.commit()

    seats_cache.delete(f"seats_{event_id}")

    return ticket_id


async def cancel_ticket(db: Session, ticket_id: str) -> bool:
    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise NotFoundError(f"Ticket {ticket_id} not found")

    client = EventsProviderClient()
    success = await client.unregister(
        event_id=str(ticket.event_id), ticket_id=ticket_id
    )

    seats_cache.delete(f"seats_{ticket.event_id}")

    db.delete(ticket)
    db.commit()

    return success
