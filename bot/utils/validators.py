"""
Утилиты для валидации пользовательского ввода
"""
import re
from typing import Optional, List, Tuple
from datetime import datetime


class Validators:
    """Класс с методами валидации"""
    
    @staticmethod
    def validate_text(text: str, min_length: int = 1, max_length: int = 5000) -> Tuple[bool, Optional[str]]:
        """
        Валидирует текст
        
        Args:
            text: Текст для валидации
            min_length: Минимальная длина
            max_length: Максимальная длина
        
        Returns:
            (is_valid, error_message)
        """
        if not text or not isinstance(text, str):
            return False, "Текст не может быть пустым"
        
        text = text.strip()
        
        if len(text) < min_length:
            return False, f"Текст должен содержать минимум {min_length} символов"
        
        if len(text) > max_length:
            return False, f"Текст не должен превышать {max_length} символов"
        
        return True, None
    
    @staticmethod
    def validate_organization_name(name: str) -> Tuple[bool, Optional[str]]:
        """
        Валидирует название организации
        
        Args:
            name: Название организации
        
        Returns:
            (is_valid, error_message)
        """
        return Validators.validate_text(name, min_length=2, max_length=500)
    
    @staticmethod
    def validate_date(date_str: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """
        Валидирует дату
        
        Args:
            date_str: Строка с датой
        
        Returns:
            (is_valid, datetime_object, error_message)
        """
        # Популярные форматы даты
        date_formats = [
            "%d.%m.%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d.%m.%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M",
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return True, dt, None
            except ValueError:
                continue
        
        return False, None, "Неверный формат даты. Используйте формат: ДД.ММ.ГГГГ или ДД.ММ.ГГГГ ЧЧ:ММ"
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Валидирует email
        
        Args:
            email: Email адрес
        
        Returns:
            (is_valid, error_message)
        """
        if not email:
            return False, "Email не может быть пустым"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email.strip()):
            return False, "Неверный формат email"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Валидирует телефон
        
        Args:
            phone: Номер телефона
        
        Returns:
            (is_valid, error_message)
        """
        if not phone:
            return False, "Телефон не может быть пустым"
        
        # Убираем все нецифровые символы кроме +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Проверяем формат (российские номера)
        if cleaned.startswith('+7'):
            if len(cleaned) == 12:
                return True, None
        elif cleaned.startswith('8'):
            if len(cleaned) == 11:
                return True, None
        elif cleaned.startswith('7'):
            if len(cleaned) == 11:
                return True, None
        elif len(cleaned) == 10:
            return True, None
        
        return False, "Неверный формат телефона. Используйте формат: +7XXXXXXXXXX или 8XXXXXXXXXX"
    
    @staticmethod
    def validate_url(url: str) -> Tuple[bool, Optional[str]]:
        """
        Валидирует URL
        
        Args:
            url: URL адрес
        
        Returns:
            (is_valid, error_message)
        """
        if not url:
            return False, "URL не может быть пустым"
        
        # Добавляем протокол, если его нет
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
        
        if re.match(pattern, url):
            return True, None
        
        return False, "Неверный формат URL"
    
    @staticmethod
    def validate_hashtags(hashtags: List[str]) -> Tuple[bool, Optional[str]]:
        """
        Валидирует хештеги
        
        Args:
            hashtags: Список хештегов
        
        Returns:
            (is_valid, error_message)
        """
        if not hashtags:
            return True, None  # Пустой список - это нормально
        
        for hashtag in hashtags:
            if not hashtag.startswith('#'):
                return False, f"Хештег должен начинаться с символа #: {hashtag}"
            
            if len(hashtag) < 2:
                return False, "Хештег не может быть пустым"
            
            if len(hashtag) > 100:
                return False, f"Хештег слишком длинный (максимум 100 символов): {hashtag}"
            
            # Проверяем, что после # идут только буквы, цифры и подчеркивания
            tag_part = hashtag[1:]
            if not re.match(r'^[\wа-яёА-ЯЁ]+$', tag_part):
                return False, f"Хештег содержит недопустимые символы: {hashtag}"
        
        return True, None
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """
        Очищает текст от потенциально опасных символов
        
        Args:
            text: Исходный текст
        
        Returns:
            Очищенный текст
        """
        if not text:
            return ""
        
        # Убираем нулевые байты и другие управляющие символы
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
        
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        
        # Убираем пробелы в начале и конце
        text = text.strip()
        
        return text


# Глобальный экземпляр валидатора
validators = Validators()

