import asyncio
from collections.abc import Callable, Coroutine
from functools import lru_cache
import json
from typing import Any
from broker.settings import get_settings
import redis.asyncio as redis

_redis_url : str | None = None

class Broker:
    def __init__(self, redis_url: str | None = None):
        self.redis_url: str = redis_url or get_settings().redis_url
        self._redis: redis.Redis | None = None
        self._pubsub: redis.client.PubSub | None = None
        self._handlers:  dict[str, dict[str, tuple[type, Callable]]] = {}
        self._listener_task: asyncio.Task | None = None

    async def connect(self) -> None:
        if self._redis is not None: 
            # already connected
            return
        self._redis = redis.from_url(self.redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()
    
    async def disconnect(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()

            try: 
                await self._listener_task
            except asyncio.CancelledError:
                pass
            
        if self._pubsub:
            await self._pubsub.aclose()

        if self._redis:
            await self._redis.aclose()
        
        self._pubsub = None
        self._redis = None
    
    def __is_connected(self):
        return self._redis is not None

    async def publish(self, channel: str, event: Any) -> None:
        if not self.__is_connected():
            raise RuntimeError("Broker is not connected")

        if hasattr(event, "model_dump_json"):
            message = event.model_dump_json()
        else:
            message = json.dumps(event)

        await self._redis.publish(channel, message)

    def on_event(self, event_class: Any, channel: str = "saga:events"):
        def decorator(
            func: Callable[[Any], Coroutine[Any, Any, None]]
        ) -> Callable[[Any], Coroutine[Any, Any, None]]:
            if channel not in self._handlers:
                self._handlers[channel] = {}
            self._handlers[channel][event_class.__name__] = (event_class, func)
            return func
        return decorator

    async def start_listening(self) -> None:
        if self._pubsub is None:
            raise RuntimeError("Broker Not Connected")

        if not self._handlers:
            return

        await self._pubsub.subscribe(*self._handlers.keys())
        self._listener_task = asyncio.create_task(self._listen())

    async def _listen(self) -> None:
        if self._pubsub is None:
            return

        async for message in self._pubsub.listen():
            if message['type'] != 'message':
                continue

            channel = message['channel']
            data = json.loads(message['data'])

            handlers = self._handlers.get(channel, {})
            event_type = data.get("type")
            entry = handlers.get(event_type)

            if entry is None:
                continue

            event_class, handler = entry
            event = event_class.model_validate(data)
            
            try:
                await handler(event)
            except Exception as e:
                print(f"Error is handler for {channel}: {e}")

@lru_cache(maxsize=1)
def get_broker():
    return Broker(redis_url=_redis_url)

def init_broker(redis_url=None):
    global _redis_url
    _redis_url = redis_url
    get_broker.cache_clear()
    return get_broker()