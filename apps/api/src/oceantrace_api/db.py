from collections.abc import Generator
from contextlib import contextmanager

from oceantrace_common.config import settings
from sqlalchemy import Engine, MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.orm import sessionmaker as sessionmaker_type

metadata = MetaData(naming_convention={"ix": "ix_%(column_0_label)s"})


class Base(DeclarativeBase):
    metadata = metadata


_engine: Engine | None = None
_SessionLocal: sessionmaker_type[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_factory() -> sessionmaker_type[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def init_db() -> None:
    from oceantrace_api import db_models  # noqa: F401
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()