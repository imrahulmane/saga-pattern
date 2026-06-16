import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql import select, update
from broker import Broker
from db.session import get_engine
from inventory_service.models import OutboxMessage


class OutboxProcessor:
    def __init__(self, broker: Broker, poll_interval: float = 0.5) -> None:
        self.broker = broker
        self.poll_interval = poll_interval
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running=True
        self._task = asyncio.create_task(self._poll_loop())

    async def stop(self) ->  None:
        self._running=False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _poll_loop(self) ->  None:
        engine = get_engine()

        while self._running:
            try:
                await self._process_pending_messages(engine)
            except Exception as e:
                print(f"Outbox processor error {e}")

            await asyncio.sleep(self.poll_interval)

    async def _process_pending_messages(self, engine: AsyncEngine) -> None:
        async with  AsyncSession(engine, expire_on_commit=False) as db:
            result = await db.execute(
                select(OutboxMessage)
                .where(OutboxMessage.published_at.is_(None))
                .order_by(OutboxMessage.id)
                .limit(100)
            )

            messages = result.scalars().all()

            for message in messages:
                try:
                    await self.broker._redis.publish(message.channel, message.payload)

                    _ = await db.execute(
                        update(OutboxMessage)
                        .where(OutboxMessage.id == message.id)
                        .values(published_at=datetime.now(timezone.utc))
                    )
                    
                    await db.commit()
                except Exception as e:
                    print(f"Failed to publish message {message.id}: {e}")
                    await db.rollback()