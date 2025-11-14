"""
Вспомогательные функции
"""
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from bot.database.models import User
from bot.database.database import get_db

logger = logging.getLogger(__name__)


def get_or_create_user(user_id: int, username: Optional[str] = None, first_name: str = "", 
                      last_name: Optional[str] = None, language_code: str = "ru") -> User:
    """
    Получает или создает пользователя в БД
    
    Args:
        user_id: ID пользователя Telegram
        username: Имя пользователя
        first_name: Имя
        last_name: Фамилия
        language_code: Код языка
    
    Returns:
        Объект User
    """
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            user = User(
                id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            logger.info(f"Создан новый пользователь: {user_id} ({username or first_name})")
        else:
            # Обновляем информацию о пользователе
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if language_code and user.language_code != language_code:
                user.language_code = language_code
                updated = True
            
            if updated:
                user.updated_at = datetime.now()
                db.commit()
                logger.info(f"Обновлен пользователь: {user_id}")
        
        return user


def calculate_content_plan_dates(start_date: date, period_days: int) -> Tuple[date, date]:
    """
    Вычисляет даты начала и окончания контент-плана
    
    Args:
        start_date: Дата начала
        period_days: Период в днях
    
    Returns:
        (start_date, end_date)
    """
    end_date = start_date + timedelta(days=period_days - 1)
    return start_date, end_date


def parse_period_days(period_str: str) -> Optional[int]:
    """
    Парсит строку периода в количество дней
    
    Args:
        period_str: Строка периода (1w, 2w, 1m, 3m)
    
    Returns:
        Количество дней или None
    """
    period_str = period_str.lower().strip()
    
    if period_str.endswith('w'):
        weeks = int(period_str[:-1])
        return weeks * 7
    elif period_str.endswith('m'):
        months = int(period_str[:-1])
        return months * 30  # Приблизительно
    elif period_str.isdigit():
        return int(period_str)
    
    return None


def get_weekday_name(weekday: int) -> str:
    """
    Возвращает название дня недели
    
    Args:
        weekday: Номер дня недели (0=понедельник, 6=воскресенье)
    
    Returns:
        Название дня недели
    """
    weekdays = [
        "Понедельник",
        "Вторник",
        "Среда",
        "Четверг",
        "Пятница",
        "Суббота",
        "Воскресенье"
    ]
    
    if 0 <= weekday < 7:
        return weekdays[weekday]
    
    return ""


def format_user_name(user: User) -> str:
    """
    Форматирует имя пользователя для отображения
    
    Args:
        user: Объект User
    
    Returns:
        Отформатированное имя
    """
    name_parts = [user.first_name]
    if user.last_name:
        name_parts.append(user.last_name)
    
    name = ' '.join(name_parts)
    
    if user.username:
        name += f" (@{user.username})"
    
    return name


def safe_get(data: Dict[str, Any], *keys, default: Any = None) -> Any:
    """
    Безопасно получает значение из вложенного словаря
    
    Args:
        data: Словарь
        *keys: Ключи для доступа к значению
        default: Значение по умолчанию
    
    Returns:
        Значение или default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current if current is not None else default

