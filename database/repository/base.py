from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_one(self, obj):
        self.session.add(obj)
        return obj
