import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.database import get_db, init_db
from src.models import Event


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    from src.sync import background_sync_worker

    task = asyncio.create_task(background_sync_worker())
    yield
    task.cancel()


app = FastAPI(title="Events Aggregator", lifespan=lifespan)


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


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/sync/trigger")
async def trigger_sync():
    from src.sync import sync_events

    await sync_events()
    return {"message": "Sync completed successfully"}


@app.get("/api/events", response_model=EventListResponse)
async def get_events(
    date_from: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
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
