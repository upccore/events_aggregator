import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Integer, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID

from src.database import Base
from src.enums import EventStatus, OutboxStatus, SyncStatus


class _EnumType(TypeDecorator):

    impl = String(50)
    cache_ok = True

    def __init__(self, enum_class, *args, **kwargs):
        self.enum_class = enum_class
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):
        if isinstance(value, self.enum_class):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        try:
            return self.enum_class(value)
        except ValueError:
            return value


class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True)
    name = Column(String, nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    registration_deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(_EnumType(EventStatus), nullable=False)
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
    sync_status = Column(_EnumType(SyncStatus), default=SyncStatus.IDLE)


class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id = Column(UUID(as_uuid=True), primary_key=True)
    event_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(String(20), nullable=False, default="active")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(
        _EnumType(OutboxStatus),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True,
    )
    attempts = Column(Integer, default=0, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    key = Column(String(255), primary_key=True)
    ticket_id = Column(String, nullable=False)
    event_id = Column(String, nullable=False)
    seat = Column(String, nullable=False)
    email = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
