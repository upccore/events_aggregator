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
