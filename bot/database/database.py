"""
Подключение к базе данных и утилиты для работы с БД
"""
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.pool import StaticPool

from bot.config import config
from bot.database.models import Base


# Создаем engine для подключения к БД
if config.DATABASE_URL.startswith("sqlite"):
    # Для SQLite используем специальные настройки
    engine = create_engine(
        config.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=config.DEBUG
    )
    
    # Включаем поддержку внешних ключей для SQLite
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # Для PostgreSQL и других БД
    engine = create_engine(
        config.DATABASE_URL,
        echo=config.DEBUG,
        pool_pre_ping=True  # Проверка соединения перед использованием
    )

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Scoped сессия для использования в async контексте
db_session = scoped_session(SessionLocal)


def init_db() -> None:
    """Инициализация базы данных - создание всех таблиц"""
    Base.metadata.create_all(bind=engine)
    print("База данных инициализирована успешно")


def drop_db() -> None:
    """Удаление всех таблиц из базы данных (используется для тестов)"""
    Base.metadata.drop_all(bind=engine)
    print("База данных очищена")


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """
    Контекстный менеджер для работы с сессией БД
    
    Использование:
        with get_db() as db:
            user = db.query(User).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db_session() -> Session:
    """
    Получить сессию БД напрямую
    
    Внимание: нужно явно закрывать сессию после использования!
    Используйте get_db() для автоматического управления.
    """
    return SessionLocal()

