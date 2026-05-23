import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    from src.sync import background_sync_worker

    task = asyncio.create_task(background_sync_worker())
    yield
    task.cancel()


app = FastAPI(title="Events Aggregator", lifespan=lifespan)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/sync/trigger")
async def trigger_sync():
    from src.sync import sync_events

    await sync_events()
    return {"message": "Sync completed successfully"}
