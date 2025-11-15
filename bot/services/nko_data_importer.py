"""
Сервис для импорта данных НКО из открытых источников
"""
import logging
import json
import re
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


class NKODataImporter:
    """Класс для импорта данных НКО из открытых источников"""
    
    # Регулярные выражения для валидации ИНН и ОГРН
    INN_PATTERN = re.compile(r'^\d{10}$|^\d{12}$')  # 10 или 12 цифр
    OGRN_PATTERN = re.compile(r'^\d{13}$|^\d{15}$')  # 13 или 15 цифр
    
    def __init__(self):
        """Инициализация импортера"""
        # Здесь можно добавить API ключи для внешних сервисов
        # Например, для получения данных из реестра НКО
        pass
    
    def validate_inn(self, inn: str) -> bool:
        """
        Валидация ИНН
        
        Args:
            inn: ИНН организации
        
        Returns:
            True, если ИНН валиден
        """
        inn = inn.strip()
        if not self.INN_PATTERN.match(inn):
            return False
        
        # Дополнительная проверка контрольной суммы (упрощенная версия)
        return len(inn) in [10, 12]
    
    def validate_ogrn(self, ogrn: str) -> bool:
        """
        Валидация ОГРН
        
        Args:
            ogrn: ОГРН организации
        
        Returns:
            True, если ОГРН валиден
        """
        ogrn = ogrn.strip()
        if not self.OGRN_PATTERN.match(ogrn):
            return False
        
        return len(ogrn) in [13, 15]
    
    async def search_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Поиск информации об НКО по ИНН
        
        Args:
            inn: ИНН организации
        
        Returns:
            Словарь с данными организации или None
        """
        if not self.validate_inn(inn):
            logger.warning(f"Некорректный ИНН: {inn}")
            return None
        
        try:
            # Здесь можно добавить интеграцию с API реестра НКО
            # Например, с API Федеральной налоговой службы или других открытых источников
            # Пока возвращаем заглушку
            
            # Пример структуры данных, которая может быть получена из API:
            # data = {
            #     "organization_name": "Название организации",
            #     "inn": inn,
            #     "address": "Адрес",
            #     "activities": ["Деятельность 1", "Деятельность 2"],
            #     "registration_date": "2020-01-01"
            # }
            
            logger.info(f"Поиск информации по ИНН: {inn}")
            # TODO: Реализовать реальный поиск через API
            # Пока возвращаем None, так как требуется API ключ
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске по ИНН {inn}: {e}")
            return None
    
    async def search_by_ogrn(self, ogrn: str) -> Optional[Dict[str, Any]]:
        """
        Поиск информации об НКО по ОГРН
        
        Args:
            ogrn: ОГРН организации
        
        Returns:
            Словарь с данными организации или None
        """
        if not self.validate_ogrn(ogrn):
            logger.warning(f"Некорректный ОГРН: {ogrn}")
            return None
        
        try:
            logger.info(f"Поиск информации по ОГРН: {ogrn}")
            # TODO: Реализовать реальный поиск через API
            # Пока возвращаем None, так как требуется API ключ
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при поиске по ОГРН {ogrn}: {e}")
            return None
    
    def parse_organization_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Парсинг сырых данных об организации в формат профиля НКО
        
        Args:
            raw_data: Сырые данные из API
        
        Returns:
            Словарь с данными профиля НКО
        """
        profile_data = {
            "organization_name": raw_data.get("organization_name"),
            "description": raw_data.get("description") or raw_data.get("activities"),
            "activity_types": self._map_activities(raw_data.get("activities", [])),
            "contact_info": {
                "address": raw_data.get("address"),
                "phone": raw_data.get("phone"),
                "email": raw_data.get("email"),
                "website": raw_data.get("website")
            }
        }
        
        return profile_data
    
    def _map_activities(self, activities: list) -> list:
        """
        Маппинг видов деятельности в стандартные категории
        
        Args:
            activities: Список видов деятельности
        
        Returns:
            Список категорий деятельности
        """
        activity_map = {
            "экология": "environmental",
            "животные": "animal_welfare",
            "помощь людям": "humanitarian",
            "образование": "education",
            "культура": "culture",
            "здоровье": "health",
            "социальная помощь": "social"
        }
        
        mapped = []
        activities_lower = [a.lower() for a in activities]
        
        for keyword, category in activity_map.items():
            if any(keyword in activity for activity in activities_lower):
                mapped.append(category)
        
        return mapped if mapped else ["other"]


# Глобальный экземпляр импортера
nko_data_importer = NKODataImporter()

