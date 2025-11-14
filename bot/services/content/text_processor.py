"""
Обработка и форматирование текста
"""
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)


class TextProcessor:
    """Класс для обработки текста"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Очищает текст от лишних пробелов и символов
        
        Args:
            text: Исходный текст
        
        Returns:
            Очищенный текст
        """
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        # Убираем пробелы в начале и конце
        text = text.strip()
        return text
    
    @staticmethod
    def split_into_paragraphs(text: str, max_length: int = 2000) -> List[str]:
        """
        Разбивает текст на абзацы по длине
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина абзаца
        
        Returns:
            Список абзацев
        """
        paragraphs = []
        current_paragraph = ""
        
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            if len(current_paragraph) + len(sentence) + 2 <= max_length:
                if current_paragraph:
                    current_paragraph += ". " + sentence
                else:
                    current_paragraph = sentence
            else:
                if current_paragraph:
                    paragraphs.append(current_paragraph + ".")
                current_paragraph = sentence
        
        if current_paragraph:
            paragraphs.append(current_paragraph + ".")
        
        return paragraphs
    
    @staticmethod
    def format_for_telegram(text: str) -> str:
        """
        Форматирует текст для Telegram с сохранением абзацев
        
        Args:
            text: Исходный текст
        
        Returns:
            Отформатированный текст с абзацами
        """
        # Если текст пустой, возвращаем как есть
        if not text or not text.strip():
            return text
        
        # Нормализуем переносы строк
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Разбиваем на строки
        lines = text.split('\n')
        
        # Обрабатываем строки: убираем пробелы в начале/конце, но сохраняем пустые строки для абзацев
        processed_lines = []
        for line in lines:
            stripped = line.strip()
            # Если строка не пустая - добавляем её
            if stripped:
                processed_lines.append(stripped)
            # Если строка пустая и это не первый/последний элемент, добавляем для создания абзаца
            elif processed_lines and processed_lines[-1] != '':
                processed_lines.append('')
        
        # Объединяем строки: между непустыми строками одной группы - один пробел, между группами - двойной перенос (абзац)
        result_lines = []
        for i, line in enumerate(processed_lines):
            if line:  # Непустая строка
                result_lines.append(line)
            else:  # Пустая строка - начинаем новый абзац
                # Добавляем пустую строку только если предыдущая строка была непустой
                if result_lines and result_lines[-1] != '':
                    result_lines.append('')
        
        # Объединяем результат с двойными переносами между абзацами
        # Группируем строки: непустые строки одной группы объединяем пробелом, группы разделяем двойным переносом
        final_text = ''
        current_paragraph = []
        
        for line in result_lines:
            if line:  # Непустая строка - добавляем в текущий абзац
                current_paragraph.append(line)
            else:  # Пустая строка - заканчиваем текущий абзац и начинаем новый
                if current_paragraph:
                    if final_text:
                        final_text += '\n\n' + ' '.join(current_paragraph)
                    else:
                        final_text = ' '.join(current_paragraph)
                    current_paragraph = []
        
        # Добавляем последний абзац, если он есть
        if current_paragraph:
            if final_text:
                final_text += '\n\n' + ' '.join(current_paragraph)
            else:
                final_text = ' '.join(current_paragraph)
        
        return final_text
    
    @staticmethod
    def add_hashtags(text: str, hashtags: List[str]) -> str:
        """
        Добавляет хештеги к тексту
        
        Args:
            text: Исходный текст
            hashtags: Список хештегов
        
        Returns:
            Текст с хештегами
        """
        if not hashtags:
            return text
        
        hashtags_str = ' '.join(hashtags)
        return f"{text}\n\n{hashtags_str}"


# Глобальный экземпляр процессора
text_processor = TextProcessor()

