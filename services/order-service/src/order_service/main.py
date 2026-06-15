from broker import get_broker
from db.base import Base
from db.session import get_engine
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from order_service.routes import router
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    broker = get_broker()
    await broker.connect()

    # register handlers
    await broker.start_listening()

    yield

    await broker.disconnect()


app = FastAPI(title="Order Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(router)

@app.get("/health")
async def health() -> dict:
    return {"status" : "ok", "service": "ok"}