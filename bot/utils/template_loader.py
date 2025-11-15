"""
Утилиты для загрузки и применения шаблонов профилей НКО
"""
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


def load_profile_templates() -> List[Dict[str, Any]]:
    """
    Загружает шаблоны профилей НКО из JSON файла
    
    Returns:
        Список шаблонов профилей
    """
    try:
        templates_path = Path(__file__).parent.parent / "data" / "nko_profile_templates.json"
        
        if not templates_path.exists():
            logger.warning(f"Файл шаблонов не найден: {templates_path}")
            return []
        
        with open(templates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("templates", [])
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке шаблонов профилей: {e}")
        return []


def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон по ID
    
    Args:
        template_id: ID шаблона
    
    Returns:
        Шаблон профиля или None
    """
    templates = load_profile_templates()
    for template in templates:
        if template.get("id") == template_id:
            return template
    return None


def get_template_by_category(category: str) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон по категории
    
    Args:
        category: Категория НКО
    
    Returns:
        Шаблон профиля или None
    """
    templates = load_profile_templates()
    for template in templates:
        if template.get("category") == category:
            return template
    return None


def apply_profile_template(template: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Применяет шаблон к данным профиля НКО
    
    Args:
        template: Шаблон профиля
        user_data: Существующие данные пользователя
    
    Returns:
        Обновленные данные профиля
    """
    result = user_data.copy()
    
    # Применяем поля из шаблона напрямую (структура JSON файла)
    mapping = {
        "organization_name": "organization_name",
        "description_text": "description",
        "activity_types": "activity_types",
        "target_audience": "target_audience",
        "tone_of_voice": "tone_of_voice"
    }
    
    for template_key, data_key in mapping.items():
        if template_key in template:
            value = template[template_key]
            # Не перезаписываем, если пользователь уже ввел данные
            if data_key not in result or result[data_key] is None:
                result[data_key] = value
    
    # Обрабатываем org_name отдельно
    if "organization_name" in template and ("organization_name" not in result or result["organization_name"] is None):
        result["organization_name"] = template["organization_name"]
    
    return result


def get_all_templates() -> List[Dict[str, Any]]:
    """
    Получает все доступные шаблоны
    
    Returns:
        Список всех шаблонов
    """
    return load_profile_templates()


def load_content_plan_templates() -> List[Dict[str, Any]]:
    """
    Загружает шаблоны контент-планов из JSON файла
    
    Returns:
        Список шаблонов контент-планов
    """
    try:
        templates_path = Path(__file__).parent.parent / "data" / "content_plan_templates.json"
        
        if not templates_path.exists():
            logger.warning(f"Файл шаблонов контент-планов не найден: {templates_path}")
            return []
        
        with open(templates_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("templates", [])
    
    except Exception as e:
        logger.error(f"Ошибка при загрузке шаблонов контент-планов: {e}")
        return []


def get_content_plan_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон контент-плана по ID
    
    Args:
        template_id: ID шаблона
    
    Returns:
        Шаблон контент-плана или None
    """
    templates = load_content_plan_templates()
    for template in templates:
        if template.get("id") == template_id:
            return template
    return None


def get_content_plan_template_by_category(category: str) -> Optional[Dict[str, Any]]:
    """
    Получает шаблон контент-плана по категории
    
    Args:
        category: Категория НКО
    
    Returns:
        Шаблон контент-плана или None
    """
    templates = load_content_plan_templates()
    for template in templates:
        if template.get("category") == category:
            return template
    return None

