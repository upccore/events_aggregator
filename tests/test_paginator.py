from unittest.mock import AsyncMock

import pytest

from src.paginator import EventsPaginator


def make_event(i):
    return {"id": str(i), "name": f"Event {i}"}


@pytest.mark.asyncio
async def test_single_page():
    client = AsyncMock()
    client.get_events.return_value = {
        "results": [make_event(1), make_event(2)],
        "next": None,
    }
    events = [e async for e in EventsPaginator(client)]
    assert len(events) == 2
    assert events[0]["id"] == "1"


@pytest.mark.asyncio
async def test_multiple_pages():
    client = AsyncMock()
    client.get_events.side_effect = [
        {"results": [make_event(1)], "next": "http://example.com/page2"},
        {"results": [make_event(2)], "next": None},
    ]
    events = [e async for e in EventsPaginator(client)]
    assert len(events) == 2


@pytest.mark.asyncio
async def test_empty_results():
    client = AsyncMock()
    client.get_events.return_value = {"results": [], "next": None}
    events = [e async for e in EventsPaginator(client)]
    assert events == []


@pytest.mark.asyncio
async def test_reusable_iterator():
    client = AsyncMock()
    client.get_events.side_effect = [
        {"results": [make_event(1)], "next": None},
        {"results": [make_event(1)], "next": None},
    ]
    paginator = EventsPaginator(client)
    first = [e async for e in paginator]
    second = [e async for e in paginator]
    assert first == second
    assert client.get_events.call_count == 2
