class EventsPaginator:
    def __init__(self, client, changed_at: str = "2000-01-01"):
        self.client = client
        self.changed_at = changed_at

    def __aiter__(self):
        self._next_url = None
        self._first_page = True
        self._current_page_events = []
        self._current_index = 0
        return self

    async def __anext__(self):
        if self._current_index >= len(self._current_page_events):
            if self._first_page:
                response = await self.client.get_events(self.changed_at)
                self._first_page = False
            elif self._next_url:
                response = await self.client.get_events("", self._next_url)
            else:
                raise StopAsyncIteration

            self._current_page_events = response["results"]
            self._next_url = response.get("next")
            self._current_index = 0

            if not self._current_page_events:
                raise StopAsyncIteration

        event = self._current_page_events[self._current_index]
        self._current_index += 1
        return event
