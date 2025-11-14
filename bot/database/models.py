"""
Модели базы данных для Telegram-бота НКО
"""
from datetime import datetime, date, time
from typing import Optional
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, Date, Time, 
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class ContentType(str, enum.Enum):
    """Типы контента"""
    TEXT = "text"
    IMAGE = "image"
    PLAN = "plan"


class ToneOfVoice(str, enum.Enum):
    """Стили повествования"""
    CONVERSATIONAL = "conversational"  # Разговорный
    FORMAL = "formal"  # Официально-деловой
    ARTISTIC = "artistic"  # Художественный
    NEUTRAL = "neutral"  # Нейтральный
    FRIENDLY = "friendly"  # Дружелюбный


class ActivityType(str, enum.Enum):
    """Типы деятельности НКО"""
    ENVIRONMENTAL = "environmental"  # Экология
    ANIMAL_WELFARE = "animal_welfare"  # Помощь животным
    HUMANITARIAN = "humanitarian"  # Помощь людям
    EDUCATION = "education"  # Образование
    CULTURE = "culture"  # Культура
    HEALTH = "health"  # Здоровье
    SOCIAL = "social"  # Социальная помощь
    OTHER = "other"  # Другое


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # Telegram user_id
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str] = mapped_column(String(255))
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[str] = mapped_column(String(10), default="ru")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    nko_profile: Mapped[Optional["NKOProfile"]] = relationship(
        "NKOProfile", 
        back_populates="user", 
        uselist=False,
        cascade="all, delete-orphan"
    )
    content_history: Mapped[list["ContentHistory"]] = relationship(
        "ContentHistory",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    content_plans: Mapped[list["ContentPlan"]] = relationship(
        "ContentPlan",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    post_templates: Mapped[list["PostTemplate"]] = relationship(
        "PostTemplate",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    notification_settings: Mapped[Optional["NotificationSettings"]] = relationship(
        "NotificationSettings",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, first_name={self.first_name})>"


class NKOProfile(Base):
    """Профиль НКО пользователя"""
    __tablename__ = "nko_profiles"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    
    organization_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    activity_types: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Список ActivityType
    target_audience: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tone_of_voice: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # ToneOfVoice
    contact_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # Контакты
    brand_colors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Цвета бренда для генерации изображений
    
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="nko_profile")
    
    def __repr__(self) -> str:
        return f"<NKOProfile(id={self.id}, user_id={self.user_id}, org_name={self.organization_name})>"


class ContentHistory(Base):
    """История сгенерированного контента"""
    __tablename__ = "content_history"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    content_type: Mapped[str] = mapped_column(String(20))  # ContentType
    content_data: Mapped[dict] = mapped_column(JSON)  # Данные контента (текст, путь к изображению и т.д.)
    extra_data: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)  # Дополнительные данные
    
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)  # Теги для поиска
    
    generated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="content_history")
    
    def __repr__(self) -> str:
        return f"<ContentHistory(id={self.id}, user_id={self.user_id}, type={self.content_type})>"


class ContentPlan(Base):
    """Контент-план пользователя"""
    __tablename__ = "content_plans"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    plan_name: Mapped[str] = mapped_column(String(255))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    
    frequency: Mapped[int] = mapped_column(Integer)  # Публикаций в неделю
    schedule: Mapped[dict] = mapped_column(JSON)  # Расписание публикаций
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="content_plans")
    
    def __repr__(self) -> str:
        return f"<ContentPlan(id={self.id}, user_id={self.user_id}, name={self.plan_name})>"


class PostTemplate(Base):
    """Шаблоны постов"""
    __tablename__ = "post_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=True
    )  # null = общий шаблон
    
    template_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(100))  # новости, анонс, отчет и т.д.
    content_structure: Mapped[dict] = mapped_column(JSON)  # Структура контента
    
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    user: Mapped[Optional["User"]] = relationship("User", back_populates="post_templates")
    
    def __repr__(self) -> str:
        return f"<PostTemplate(id={self.id}, name={self.template_name}, category={self.category})>"


class NotificationSettings(Base):
    """Настройки уведомлений пользователя"""
    __tablename__ = "notification_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        unique=True
    )
    
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    reminder_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="notification_settings")
    
    def __repr__(self) -> str:
        return f"<NotificationSettings(id={self.id}, user_id={self.user_id}, enabled={self.reminder_enabled})>"

