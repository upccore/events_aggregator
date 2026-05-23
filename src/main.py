from fastapi import FastAPI
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Events Aggregator", lifespan=lifespan)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}
