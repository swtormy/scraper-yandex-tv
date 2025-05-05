from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.sql import or_

from database.repository.base import BaseRepository
from database.models.mldb import TVSchedule


class TVScheduleRepository(BaseRepository):
    model = TVSchedule

    async def find_by_event_id(self, event_id: int) -> TVSchedule | None:
        stmt = select(self.model).where(self.model.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_upsert(self, event_data_list: list[dict]):
        if not event_data_list:
            return

        insert_stmt = pg_insert(self.model.__table__).values(event_data_list)

        update_cols = {
            "channel_title": insert_stmt.excluded.channel_title,
            "start_time": insert_stmt.excluded.start_time,
            "end_time": insert_stmt.excluded.end_time,
            "program_id": insert_stmt.excluded.program_id,
            "program_title": insert_stmt.excluded.program_title,
            "episode_id": insert_stmt.excluded.episode_id,
            "episode_title": insert_stmt.excluded.episode_title,
            "program_type": insert_stmt.excluded.program_type,
            "is_live": insert_stmt.excluded.is_live,
            "has_reminder": insert_stmt.excluded.has_reminder,
            "has_started": insert_stmt.excluded.has_started,
            "has_finished": insert_stmt.excluded.has_finished,
            "is_now": insert_stmt.excluded.is_now,
            "event_title": insert_stmt.excluded.event_title,
            "start_time_utc": insert_stmt.excluded.start_time_utc,
            "end_time_utc": insert_stmt.excluded.end_time_utc,
            "updated_at": text("TIMEZONE('Europe/Moscow', CURRENT_TIMESTAMP)"),
        }

        compare_columns = [
            col.name
            for col in self.model.__table__.c
            if col.name not in ["event_id", "created_at", "updated_at"]
        ]

        where_condition = or_(
            self.model.__table__.c[col_name].is_distinct_from(
                getattr(insert_stmt.excluded, col_name)
            )
            for col_name in compare_columns
        )

        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["event_id"],
            set_=update_cols,
            where=where_condition,
        )

        await self.session.execute(upsert_stmt)
