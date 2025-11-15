"""
Утилиты для работы с праздничными и памятными датами
"""
import logging
import json
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


def load_holidays() -> List[Dict[str, Any]]:
    """
    Загружает праздничные даты из JSON файла
    
    Returns:
        Список праздников
    """
    try:
        holidays_path = Path(__file__).parent.parent / "data" / "holidays.json"
        
        if not holidays_path.exists():
            logger.warning(f"Файл праздников не найден: {holidays_path}")
            return []
        
        with open(holidays_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("holidays", [])
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке праздников: {e}")
        return []


def get_relevant_dates(
    start_date: date,
    end_date: date,
    activity_types: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Получает релевантные праздничные даты для периода
    
    Args:
        start_date: Дата начала периода
        end_date: Дата окончания периода
        activity_types: Типы деятельности НКО для фильтрации
    
    Returns:
        Список релевантных праздников
    """
    holidays = load_holidays()
    relevant = []
    
    current_year = start_date.year
    end_year = end_date.year
    
    for year in range(current_year, end_year + 1):
        for holiday in holidays:
            holiday_date_str = holiday.get("date", "")
            if not holiday_date_str:
                continue
            
            # Парсим дату (MM-DD формат)
            try:
                month, day = map(int, holiday_date_str.split("-"))
                holiday_date = date(year, month, day)
            except:
                continue
            
            # Проверяем, попадает ли в период
            if start_date <= holiday_date <= end_date:
                # Фильтруем по типам деятельности
                if activity_types:
                    category = holiday.get("category", "")
                    # Если категория соответствует типу деятельности или общая
                    if category in activity_types or category == "general" or category == "volunteer":
                        relevant.append({
                            "date": holiday_date,
                            "name": holiday.get("name", ""),
                            "description": holiday.get("description", ""),
                            "category": category
                        })
                else:
                    relevant.append({
                        "date": holiday_date,
                        "name": holiday.get("name", ""),
                        "description": holiday.get("description", ""),
                        "category": holiday.get("category", "")
                    })
    
    # Сортируем по дате
    relevant.sort(key=lambda x: x["date"])
    
    return relevant


def get_holidays_for_month(year: int, month: int, activity_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Получает праздники для конкретного месяца
    
    Args:
        year: Год
        month: Месяц (1-12)
        activity_types: Типы деятельности НКО
    
    Returns:
        Список праздников в месяце
    """
    holidays = load_holidays()
    relevant = []
    
    for holiday in holidays:
        holiday_date_str = holiday.get("date", "")
        if not holiday_date_str:
            continue
        
        try:
            holiday_month, holiday_day = map(int, holiday_date_str.split("-"))
            
            if holiday_month == month:
                holiday_date = date(year, holiday_month, holiday_day)
                
                # Фильтруем по типам деятельности
                if activity_types:
                    category = holiday.get("category", "")
                    if category in activity_types or category == "general" or category == "volunteer":
                        relevant.append({
                            "date": holiday_date,
                            "name": holiday.get("name", ""),
                            "description": holiday.get("description", ""),
                            "category": category
                        })
                else:
                    relevant.append({
                        "date": holiday_date,
                        "name": holiday.get("name", ""),
                        "description": holiday.get("description", ""),
                        "category": holiday.get("category", "")
                    })
        except:
            continue
    
    relevant.sort(key=lambda x: x["date"])
    return relevant

