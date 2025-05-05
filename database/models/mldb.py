from sqlalchemy import Boolean, Column, DateTime, Integer, MetaData, Text, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import text
from config import settings

Base = declarative_base(metadata=MetaData(schema=settings.MLDB_SCHEMA))


class TVSchedule(Base):
    __tablename__ = "tv_schedule"

    channel_title = Column(String(255), nullable=False)

    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    program_id = Column(Integer, nullable=True)
    program_title = Column(Text, nullable=True)

    episode_id = Column(Integer, nullable=True)
    episode_title = Column(Text, nullable=True)

    program_type = Column(String(100), nullable=True)

    is_live = Column(Boolean, nullable=False, default=False)

    has_reminder = Column(Boolean, nullable=False, default=False)
    has_started = Column(Boolean, nullable=False, default=False)
    has_finished = Column(Boolean, nullable=False, default=False)
    is_now = Column(Boolean, nullable=False, default=False)

    event_id = Column(Integer, primary_key=True)
    event_title = Column(String, nullable=False)

    start_time_utc = Column(DateTime(timezone=True), nullable=False)
    end_time_utc = Column(DateTime(timezone=True), nullable=False)

    moscow_tz_now = text("TIMEZONE('Europe/Moscow', CURRENT_TIMESTAMP)")

    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=moscow_tz_now
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=moscow_tz_now,
        onupdate=moscow_tz_now,
    )

    def __repr__(self):
        return (
            f"<TVSchedule(event_id={self.event_id}, "
            f"channel='{self.channel_title}', title='{self.event_title[:30]}...', "
            f"start='{self.start_time}', end='{self.end_time}', start_utc='{self.start_time_utc}')>"
        )
