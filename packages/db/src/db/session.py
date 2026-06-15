
from dataclasses import dataclass
from functools import lru_cache

from db.settings import get_db_settings
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.asyncio.engine import create_async_engine
from collections.abc import AsyncGenerator

@dataclass
class DatabaseManager:
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]

@lru_cache(maxsize=1)
def _get_db_manager():
    url = get_db_settings().db_url
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return DatabaseManager(engine=engine, session_factory=session_factory)

def get_engine() -> AsyncEngine:
    return _get_db_manager().engine

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    db = _get_db_manager()
    async with db.session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise