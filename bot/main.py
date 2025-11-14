"""
Главный файл бота - точка входа и настройка приложения
"""
import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters
)

from bot.config import config
from bot.database.database import init_db
from bot.handlers.start import start_command, help_command, about_command
from bot.handlers.common import button_handler, error_handler, cancel_conversation, back_to_menu
from bot.handlers.nko_setup import setup_nko_handlers
from bot.handlers.text_generation import setup_text_generation_handlers
from bot.handlers.image_generation import setup_image_generation_handlers
from bot.handlers.text_editor import setup_text_editor_handlers
from bot.handlers.content_plan import setup_content_plan_handlers
from bot.handlers.history import setup_history_handlers
from bot.handlers.settings import setup_settings_handlers

logger = logging.getLogger(__name__)


def setup_handlers(application: Application):
    """Настройка всех обработчиков бота"""
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Настройка профиля НКО
    setup_nko_handlers(application)
    
    # Генерация текста
    setup_text_generation_handlers(application)
    
    # Генерация изображений
    setup_image_generation_handlers(application)
    
    # Редактор текста
    setup_text_editor_handlers(application)
    
    # Контент-план
    setup_content_plan_handlers(application)
    
    # История
    setup_history_handlers(application)
    
    # Настройки
    setup_settings_handlers(application)
    
    # Обработчик кнопок главного меню (должен быть ПОСЛЕ всех ConversationHandler)
    # Это важно, чтобы ConversationHandler обрабатывали сообщения первыми
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    # Обработчик ошибок (должен быть последним)
    application.add_error_handler(error_handler)
    
    logger.info("Обработчики настроены")


async def run_bot():
    """Запуск бота"""
    try:
        # Валидация конфигурации
        config.validate()
        logger.info("Конфигурация проверена")
        
        # Инициализация БД
        init_db()
        logger.info("База данных инициализирована")
        
        # Создание приложения
        application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
        
        # Настройка обработчиков
        setup_handlers(application)
        
        # Запуск бота
        logger.info("Бот запускается...")
        logger.info("Бот успешно запущен и готов к работе!")
        
        # Запускаем polling - бот будет работать до получения сигнала остановки
        async with application:
            await application.start()
            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            await asyncio.Event().wait()  # Бесконечное ожидание
        
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.exception(f"Ошибка при запуске бота: {e}")
        raise


if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    )
    
    asyncio.run(run_bot())

