from datetime import datetime

from sqlalchemy.orm import Session

from src.cache import seats_cache
from src.enums import EventStatus
from src.models import Event, IdempotencyKey, OutboxEvent, Ticket
from src.provider_client import EventsProviderClient


class NotFoundError(Exception):
    pass


class BusinessLogicError(Exception):
    pass


class ConflictError(Exception):
    pass


def get_events_list(
    db: Session,
    date_from_dt: datetime | None,
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
    idempotency_key: str | None = None,
) -> str:
    if idempotency_key:
        existing = (
            db.query(IdempotencyKey)
            .filter(IdempotencyKey.key == idempotency_key)
            .first()
        )
        if existing:
            if (
                existing.event_id != event_id
                or existing.seat != seat
                or existing.email != email
            ):
                raise ConflictError("Idempotency key already used with different data")
            return existing.ticket_id

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

    outbox_event = OutboxEvent(
        event_type="ticket_purchased",
        payload={
            "message": f"Вы успешно зарегистрированы на мероприятие - {event.name}",
            "reference_id": ticket_id,
            "idempotency_key": ticket_id,
        },
    )
    db.add(outbox_event)

    if idempotency_key:
        db.add(
            IdempotencyKey(
                key=idempotency_key,
                ticket_id=ticket_id,
                event_id=event_id,
                seat=seat,
                email=email,
            )
        )

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
