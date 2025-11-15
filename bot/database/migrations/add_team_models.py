"""
Миграция для добавления моделей командной работы
"""
from sqlalchemy import Integer, String, Boolean, DateTime, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
from bot.database.models import Base


class TeamRole(str, enum.Enum):
    """Роли в команде"""
    ADMIN = "admin"  # Администратор
    EDITOR = "editor"  # Редактор
    AUTHOR = "author"  # Автор
    VIEWER = "viewer"  # Наблюдатель


class Team(Base):
    """Модель команды"""
    __tablename__ = "teams"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Связи
    members: Mapped[list["TeamMember"]] = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    shared_content: Mapped[list["SharedContent"]] = relationship("SharedContent", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    """Участник команды"""
    __tablename__ = "team_members"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    role: Mapped[str] = mapped_column(String(20))  # Роль в команде
    permissions: Mapped[dict] = mapped_column(JSON, nullable=True)  # Дополнительные права
    
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    team: Mapped["Team"] = relationship("Team", back_populates="members")
    user: Mapped["User"] = relationship("User")


class SharedContent(Base):
    """Общий контент команды"""
    __tablename__ = "shared_content"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id", ondelete="CASCADE"))
    content_history_id: Mapped[int] = mapped_column(Integer, ForeignKey("content_history.id", ondelete="CASCADE"))
    
    shared_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    comments: Mapped[list] = mapped_column(JSON, nullable=True)  # Комментарии к контенту
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    team: Mapped["Team"] = relationship("Team", back_populates="shared_content")


class ContentComment(Base):
    """Комментарии к контенту"""
    __tablename__ = "content_comments"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shared_content_id: Mapped[int] = mapped_column(Integer, ForeignKey("shared_content.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    comment_text: Mapped[str] = mapped_column(String(1000))
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Связи
    user: Mapped["User"] = relationship("User")

