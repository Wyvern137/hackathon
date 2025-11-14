#!/usr/bin/env python3
"""
Точка входа для запуска Telegram-бота для НКО
"""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую папку в путь
sys.path.insert(0, str(Path(__file__).parent))

from bot.config import config

# Настраиваем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    try:
        # Валидация конфигурации
        config.validate()
        logger.info("Конфигурация проверена успешно")
        
        # Импортируем и запускаем бота
        from bot.main import run_bot
        await run_bot()
        
    except ValueError as e:
        logger.error(f"Ошибка конфигурации: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

