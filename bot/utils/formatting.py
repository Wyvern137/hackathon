"""
Утилиты для форматирования текста
"""
import re
from typing import List
from datetime import datetime


class Formatters:
    """Класс с методами форматирования"""
    
    @staticmethod
    def format_text_for_telegram(text: str, max_length: int = 4096) -> str:
        """
        Форматирует текст для Telegram
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина (4096 для Telegram)
        
        Returns:
            Отформатированный текст
        """
        if not text:
            return ""
        
        # Обрезаем до максимальной длины
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        # Убираем множественные переносы строк (максимум 2 подряд)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Убираем пробелы в начале и конце строк
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        return text.strip()
    
    @staticmethod
    def format_date(date: datetime, format_str: str = "%d.%m.%Y") -> str:
        """
        Форматирует дату в строку
        
        Args:
            date: Объект datetime
            format_str: Формат строки
        
        Returns:
            Отформатированная дата
        """
        return date.strftime(format_str)
    
    @staticmethod
    def format_date_with_time(date: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
        """
        Форматирует дату и время в строку
        
        Args:
            date: Объект datetime
            format_str: Формат строки
        
        Returns:
            Отформатированная дата и время
        """
        return date.strftime(format_str)
    
    @staticmethod
    def format_hashtags_list(hashtags: List[str]) -> str:
        """
        Форматирует список хештегов в строку
        
        Args:
            hashtags: Список хештегов
        
        Returns:
            Строка с хештегами через пробел
        """
        return ' '.join(hashtags)
    
    @staticmethod
    def format_post_with_hashtags(text: str, hashtags: List[str]) -> str:
        """
        Форматирует пост с хештегами
        
        Args:
            text: Текст поста
            hashtags: Список хештегов
        
        Returns:
            Отформатированный пост
        """
        if not text:
            return Formatters.format_hashtags_list(hashtags)
        
        if not hashtags:
            return text
        
        return f"{text}\n\n{Formatters.format_hashtags_list(hashtags)}"
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """
        Обрезает текст до указанной длины
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина
            suffix: Суффикс для обрезанного текста
        
        Returns:
            Обрезанный текст
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_content_plan_entry(date: datetime, category: str, topic: str = "") -> str:
        """
        Форматирует запись контент-плана
        
        Args:
            date: Дата
            category: Категория поста
            topic: Тема поста
        
        Returns:
            Отформатированная запись
        """
        date_str = Formatters.format_date(date)
        result = f"📅 {date_str} - {category}"
        if topic:
            result += f"\n   💡 {topic}"
        return result
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Экранирует специальные символы Markdown для Telegram
        
        Args:
            text: Исходный текст
        
        Returns:
            Экранированный текст
        """
        if not text:
            return ""
        
        # Символы, которые нужно экранировать
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        
        return text


# Глобальный экземпляр форматтера
formatters = Formatters()

