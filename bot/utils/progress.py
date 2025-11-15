"""
Утилиты для отображения прогресса операций
"""
import asyncio
from typing import Optional, Callable, List
from telegram import Message
from telegram.ext import ContextTypes


class ProgressBar:
    """Класс для отображения прогресс-бара в Telegram"""
    
    STAGES = [
        "⏳ Анализ запроса...",
        "🤔 Генерация контента...",
        "✨ Форматирование...",
        "✅ Готово!"
    ]
    
    def __init__(self, message: Message, total_stages: int = 4):
        """
        Инициализация прогресс-бара
        
        Args:
            message: Сообщение для обновления
            total_stages: Общее количество этапов
        """
        self.message = message
        self.total_stages = total_stages
        self.current_stage = 0
        self.stage_names = self.STAGES[:total_stages] if total_stages <= len(self.STAGES) else self.STAGES
    
    async def update(self, stage: int, custom_text: Optional[str] = None):
        """
        Обновляет прогресс-бар
        
        Args:
            stage: Номер этапа (0-based)
            custom_text: Кастомный текст для этапа
        """
        if stage < 0 or stage >= self.total_stages:
            return
        
        self.current_stage = stage
        
        # Формируем текст прогресса
        progress_text = custom_text or self.stage_names[stage]
        
        # Добавляем визуальный индикатор
        progress_bar = self._create_progress_bar(stage, self.total_stages)
        
        full_text = f"{progress_text}\n\n{progress_bar}"
        
        try:
            await self.message.edit_text(full_text)
        except Exception:
            # Если не удалось обновить (например, сообщение уже изменено), игнорируем
            pass
    
    def _create_progress_bar(self, current: int, total: int) -> str:
        """Создает визуальный прогресс-бар"""
        filled = "█" * current
        empty = "░" * (total - current)
        percentage = int((current / total) * 100) if total > 0 else 0
        return f"{filled}{empty} {percentage}%"
    
    async def complete(self, final_text: str):
        """Завершает прогресс-бар финальным сообщением"""
        progress_bar = self._create_progress_bar(self.total_stages, self.total_stages)
        full_text = f"{final_text}\n\n{progress_bar}"
        try:
            await self.message.edit_text(full_text)
        except Exception:
            pass


async def show_progress(
    message: Message,
    stages: List[str],
    update_interval: float = 2.0,
    callback: Optional[Callable] = None
) -> ProgressBar:
    """
    Показывает прогресс выполнения операции
    
    Args:
        message: Сообщение для обновления
        stages: Список названий этапов
        update_interval: Интервал обновления в секундах
        callback: Функция, которая будет вызвана для каждого этапа
    
    Returns:
        ProgressBar объект
    """
    progress = ProgressBar(message, len(stages))
    
    for i, stage_name in enumerate(stages):
        await progress.update(i, stage_name)
        
        if callback:
            await callback(i)
        
        if i < len(stages) - 1:  # Не ждем после последнего этапа
            await asyncio.sleep(update_interval)
    
    return progress


async def update_progress_message(
    message: Message,
    text: str,
    stage: int = 0,
    total_stages: int = 4
):
    """
    Быстрое обновление сообщения с прогрессом
    
    Args:
        message: Сообщение для обновления
        text: Текст этапа
        stage: Текущий этап
        total_stages: Всего этапов
    """
    progress_bar = ProgressBar(message, total_stages)
    await progress_bar.update(stage, text)

