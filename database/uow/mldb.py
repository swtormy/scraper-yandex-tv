from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from config import settings
from database.models.mldb import Base
from database.repository.tv_schedule import TVScheduleRepository

DATABASE_URL = (
    f"postgresql+asyncpg://{settings.MLDB_USER}:"
    f"{settings.MLDB_PASSWORD}@{settings.MLDB_HOST}:{settings.MLDB_PORT}/{settings.MLDB_NAME}"
)

async_engine = create_async_engine(DATABASE_URL, pool_recycle=600, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(
    bind=async_engine, expire_on_commit=False, autoflush=False
)


class MldbUow:
    def __init__(self):
        self._factory = async_session_factory
        self.session: AsyncSession | None = None
        self.tv_schedule: TVScheduleRepository | None = None

    async def __aenter__(self):
        self.session: AsyncSession = self._factory()
        self.tv_schedule = TVScheduleRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                if exc_type:
                    await self.rollback()
            finally:
                await self.session.close()
                self.session = None
                self.tv_schedule = None

    async def commit(self):
        if not self.session:
            raise RuntimeError("Сессия не активна для коммита")
        await self.session.commit()

    async def rollback(self):
        if not self.session:
            raise RuntimeError("Сессия не активна для отката")
        await self.session.rollback()


async def get_mldb_uow() -> MldbUow:
    return MldbUow()


async def init_db():
    async with async_engine.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.MLDB_SCHEMA}"))
        await conn.run_sync(Base.metadata.create_all)
