from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Events Aggregator", lifespan=lifespan)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
