from enum import Enum


class EventStatus(str, Enum):
    PUBLISHED = "published"
    DRAFT = "draft"
    CANCELLED = "cancelled"


class SyncStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
