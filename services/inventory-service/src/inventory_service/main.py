from sqlalchemy.sql import text

from broker import get_broker
from db.base import Base
from db.session import get_engine
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from inventory_service.handlers import register_handlers
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from inventory_service.outbox import OutboxProcessor

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with get_engine().begin() as conn:
        _ = await conn.execute(text("CREATE SCHEMA IF NOT EXISTS inventory"))
        await conn.run_sync(Base.metadata.create_all)

    broker = get_broker()
    await broker.connect()
    register_handlers(broker)
    await broker.start_listening()

    outbox_processor = OutboxProcessor(broker)
    await outbox_processor.start()

    yield

    await broker.disconnect()
    await outbox_processor.stop()


app = FastAPI(title="Inventory Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.get("/health")
async def health() -> dict:
    return {"status" : "ok", "service": "ok", "Service": "inventory"}