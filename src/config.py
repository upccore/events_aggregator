import os
from urllib.parse import quote_plus

POSTGRES_USERNAME = os.getenv("POSTGRES_USERNAME", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DATABASE_NAME = os.getenv("POSTGRES_DATABASE_NAME", "events_aggregator")

DATABASE_URL = (
    f"postgresql://{POSTGRES_USERNAME}:{quote_plus(POSTGRES_PASSWORD)}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DATABASE_NAME}"
)

EVENTS_PROVIDER_API_KEY = os.getenv("EVENTS_PROVIDER_API_KEY", "")
EVENTS_PROVIDER_URL = os.getenv(
    "EVENTS_PROVIDER_URL",
    "http://student-system-events-provider-web.student-system-events-provider.svc:8000",
)

CAPASHINO_URL = os.getenv(
    "CAPASHINO_URL",
    "http://student-system-capashino-web.student-system-capashino.svc:8000",
)
CAPASHINO_API_KEY = os.getenv("CAPASHINO_API_KEY", "")

GLITCHTIP_DSN = os.getenv("GLITCHTIP_DSN", "")

OUTBOX_WORKER_INTERVAL = int(os.getenv("OUTBOX_WORKER_INTERVAL", "10"))
OUTBOX_MAX_RETRIES = int(os.getenv("OUTBOX_MAX_RETRIES", "5"))
