import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    artist = Column(String(200), nullable=False)
    album = Column(String(200), nullable=False, default="Single")
    duration_sec = Column(Integer, nullable=False, default=180)
    rating = Column(Integer, nullable=False, default=3)
    version = Column(Integer, nullable=False, default=1)
    updated_at = Column(String(64), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "duration_sec": self.duration_sec,
            "rating": self.rating,
            "version": self.version,
            "updated_at": self.updated_at,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_session_factory(db_url: str | None = None):
    url = db_url or os.getenv("DATABASE_URL", "sqlite:///./musicsync.db")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args, future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)