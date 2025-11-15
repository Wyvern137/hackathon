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
from bot.handlers.start import (
    start_command, 
    help_command, 
    about_command,
    quick_start_callback,
    show_demo_examples,
    show_achievements_callback,
    handle_voice_after_start
)
from bot.handlers.common import button_handler, error_handler, cancel_conversation, back_to_menu, handle_voice_in_main_menu
from bot.handlers.nko_setup import setup_nko_handlers
from bot.handlers.text_generation import setup_text_generation_handlers
from bot.handlers.image_generation import setup_image_generation_handlers
from bot.handlers.text_editor import setup_text_editor_handlers
from bot.handlers.content_plan import setup_content_plan_handlers
from bot.handlers.history import setup_history_handlers
from bot.handlers.settings import setup_settings_handlers
from bot.handlers.templates import setup_templates_handlers
from bot.handlers.analytics import setup_analytics_handlers
from bot.handlers.ab_testing import setup_ab_testing_handlers
from bot.handlers.calendar import setup_calendar_handlers
from bot.handlers.team import setup_team_handlers
from bot.handlers.team_advanced import setup_team_advanced_handlers
from bot.handlers.smart_menu import setup_smart_menu_handlers
from bot.handlers.quick_commands import setup_quick_commands_handlers
from bot.handlers.platform_optimization import setup_platform_optimization_handlers
from bot.handlers.post_series import setup_post_series_handlers
from bot.services.scheduler import start_scheduler

logger = logging.getLogger(__name__)


def setup_handlers(application: Application):
    """Настройка всех обработчиков бота"""
    
    # Команды
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Обработчик голосовых сообщений после /start (должен быть до других обработчиков)
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_after_start))
    
    # Обработчики быстрого старта и примеров
    application.add_handler(CallbackQueryHandler(quick_start_callback, pattern="^(quick_start_guide|how_it_works)$"))
    application.add_handler(CallbackQueryHandler(show_demo_examples, pattern="^(show_demo_examples|show_more_examples)$"))
    application.add_handler(CallbackQueryHandler(show_achievements_callback, pattern="^(show_achievements|show_all_achievements)$"))
    
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
    
    # Шаблоны
    setup_templates_handlers(application)
    
    # Статистика
    setup_analytics_handlers(application)
    
    # A/B тестирование
    setup_ab_testing_handlers(application)
    
    # Календарь событий
    setup_calendar_handlers(application)
    
    # Командная работа
    setup_team_handlers(application)
    setup_team_advanced_handlers(application)
    
    # Умное меню с категориями
    setup_smart_menu_handlers(application)
    
    # Команды быстрого доступа
    setup_quick_commands_handlers(application)
    
    # Оптимизация под платформы
    setup_platform_optimization_handlers(application)
    
    # Генерация серий постов
    setup_post_series_handlers(application)
    
    # Настройки
    setup_settings_handlers(application)
    
    # Обработчик голосовых сообщений в главном меню (должен быть после ConversationHandler, но до button_handler)
    application.add_handler(MessageHandler(filters.VOICE, handle_voice_in_main_menu))
    
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
        
        # Интеграция bot экземпляра с планировщиком для отправки напоминаний
        from bot.services.scheduler import set_bot_instance
        set_bot_instance(application.bot)
        
        # Запуск планировщика для напоминаний
        start_scheduler()
        logger.info("Планировщик запущен")
        
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

