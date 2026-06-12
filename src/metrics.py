from prometheus_client import Counter, Gauge, Histogram

http_requests_total = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

events_provider_requests_total = Counter(
    "events_provider_requests_total",
    "Total number of requests to Events Provider",
    ["endpoint", "status"],
)

events_provider_request_duration_seconds = Histogram(
    "events_provider_request_duration_seconds",
    "Events Provider request duration in seconds",
    ["endpoint"],
)

tickets_created_total = Gauge(
    "tickets_created_total",
    "Total number of tickets in database",
)

tickets_cancelled_total = Gauge(
    "tickets_cancelled_total",
    "Total number of cancelled tickets in database",
)

events_total = Gauge(
    "events_total",
    "Total number of events in database",
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total number of cache hits",
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total number of cache misses",
)
