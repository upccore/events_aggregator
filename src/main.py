import asyncio
import logging
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.cache import seats_cache
from src.database import get_db
from src.models import Event, Ticket
from src.provider_client import EventsProviderClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Events Aggregator")

_initialized = False
_init_lock = asyncio.Lock()


async def ensure_initialized():
    global _initialized
    if _initialized:
        return

    async with _init_lock:
        if _initialized:
            return

        try:
            from src.database import init_db

            init_db()
            logger.info("Database initialized")
        except Exception as e:
            logger.error(f"Database init failed: {e}")

        try:
            from src.sync import background_sync_worker

            asyncio.create_task(background_sync_worker())
            logger.info("Sync worker started")
        except Exception as e:
            logger.error(f"Sync worker start failed: {e}")

        _initialized = True


class PlaceSchema(BaseModel):
    id: str
    name: str
    city: str
    address: str
    seats_pattern: str | None = None


class EventSchema(BaseModel):
    id: str
    name: str
    place: PlaceSchema
    event_time: datetime
    registration_deadline: datetime
    status: str
    number_of_visitors: int


class EventListResponse(BaseModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[EventSchema]


class SeatsResponse(BaseModel):
    event_id: str
    available_seats: list[str]


class TicketResponse(BaseModel):
    ticket_id: str


class CancelResponse(BaseModel):
    success: bool


class RegisterRequest(BaseModel):
    event_id: str
    first_name: str
    last_name: str
    email: str
    seat: str


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/sync/trigger")
async def trigger_sync():
    await ensure_initialized()
    from src.sync import sync_events

    try:
        await sync_events()
        return {"message": "Sync completed successfully"}
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/events", response_model=EventListResponse)
async def get_events(
    date_from: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    await ensure_initialized()

    query = db.query(Event)

    if date_from:
        try:
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(Event.event_time >= date_from_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    total = query.count()
    events = (
        query.order_by(Event.event_time)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    next_url = None
    if page * page_size < total:
        params = f"page={page + 1}&page_size={page_size}"
        if date_from:
            params += f"&date_from={date_from}"
        next_url = f"/api/events?{params}"

    results = [
        EventSchema(
            id=str(e.id),
            name=e.name,
            place=PlaceSchema(
                id=str(e.place_id),
                name=e.place_name,
                city=e.place_city,
                address=e.place_address,
            ),
            event_time=e.event_time,
            registration_deadline=e.registration_deadline,
            status=e.status,
            number_of_visitors=e.number_of_visitors,
        )
        for e in events
    ]

    return EventListResponse(count=total, next=next_url, results=results)


@app.get("/api/events/{event_id}", response_model=EventSchema)
async def get_event(event_id: str, db: Session = Depends(get_db)):
    await ensure_initialized()

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventSchema(
        id=str(event.id),
        name=event.name,
        place=PlaceSchema(
            id=str(event.place_id),
            name=event.place_name,
            city=event.place_city,
            address=event.place_address,
            seats_pattern=event.place_seats_pattern,
        ),
        event_time=event.event_time,
        registration_deadline=event.registration_deadline,
        status=event.status,
        number_of_visitors=event.number_of_visitors,
    )


@app.get("/api/events/{event_id}/seats", response_model=SeatsResponse)
async def get_seats(event_id: str, db: Session = Depends(get_db)):
    await ensure_initialized()

    cached = seats_cache.get(f"seats_{event_id}")
    if cached:
        return SeatsResponse(event_id=event_id, available_seats=cached)

    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published")

    client = EventsProviderClient()
    seats = await client.get_seats(event_id)

    seats_cache.set(f"seats_{event_id}", seats, ttl_seconds=30)
    return SeatsResponse(event_id=event_id, available_seats=seats)


@app.post("/api/tickets", status_code=201)
async def register_ticket(request: Request, db: Session = Depends(get_db)):
    await ensure_initialized()

    try:
        body = await request.json()
        req = RegisterRequest(**body)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request body")

    if not req.event_id:
        raise HTTPException(status_code=400, detail="event_id is required")
    if not req.first_name:
        raise HTTPException(status_code=400, detail="first_name is required")
    if not req.last_name:
        raise HTTPException(status_code=400, detail="last_name is required")
    if not req.email:
        raise HTTPException(status_code=400, detail="email is required")
    if not req.seat:
        raise HTTPException(status_code=400, detail="seat is required")

    event = db.query(Event).filter(Event.id == req.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if event.status != "published":
        raise HTTPException(status_code=400, detail="Event is not published")

    client = EventsProviderClient()
    try:
        ticket_id = await client.register(
            event_id=req.event_id,
            first_name=req.first_name,
            last_name=req.last_name,
            email=req.email,
            seat=req.seat,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    ticket = Ticket(ticket_id=ticket_id, event_id=req.event_id)
    db.add(ticket)
    db.commit()

    seats_cache.delete(f"seats_{req.event_id}")

    return TicketResponse(ticket_id=ticket_id)


@app.delete("/api/tickets/{ticket_id}", response_model=CancelResponse)
async def cancel_ticket(ticket_id: str, db: Session = Depends(get_db)):
    await ensure_initialized()

    ticket = db.query(Ticket).filter(Ticket.ticket_id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    client = EventsProviderClient()
    success = await client.unregister(
        event_id=str(ticket.event_id), ticket_id=ticket_id
    )

    db.delete(ticket)
    db.commit()

    seats_cache.delete(f"seats_{ticket.event_id}")

    return CancelResponse(success=success)
