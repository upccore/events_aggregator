from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    registration_deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, nullable=False)
    number_of_visitors = Column(Integer, default=0)
    place_id = Column(UUID(as_uuid=True))
    place_name = Column(String)
    place_city = Column(String)
    place_address = Column(String)
    place_seats_pattern = Column(String)
    changed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True))
    status_changed_at = Column(DateTime(timezone=True))


class SyncMetadata(Base):
    __tablename__ = "sync_metadata"

    id = Column(String, primary_key=True, default="sync_state")
    last_changed_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime(2000, 1, 1, tzinfo=timezone.utc),
    )
    last_sync_time = Column(DateTime(timezone=True))
    sync_status = Column(String, default="idle")


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(UUID(as_uuid=True), primary_key=True)
    event_id = Column(UUID(as_uuid=True), nullable=False)
