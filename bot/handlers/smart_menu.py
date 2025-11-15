"""
Обработчики умного меню с категориями
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.keyboards.smart_menu import (
    get_category_menu_keyboard,
    get_content_category_keyboard,
    get_planning_category_keyboard,
    get_analytics_category_keyboard,
    get_settings_category_keyboard,
    get_quick_access_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def show_categories_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню категорий"""
    user_id = update.effective_user.id
    
    text = (
        "📂 **Категории функций**\n\n"
        "Выбери категорию для быстрого доступа к функциям:\n\n"
        "• 🎨 **Создание контента** - генерация текстов и изображений\n"
        "• 📅 **Планирование** - контент-планы и календарь\n"
        "• 📊 **Аналитика** - статистика и анализ\n"
        "• ⚙️ **Настройки** - профиль и настройки бота"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_category_menu_keyboard(),
        parse_mode="Markdown"
    )


async def handle_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = update.effective_user.id
    
    if callback_data == "category_content":
        text = (
            "🎨 **Создание контента**\n\n"
            "Выбери функцию для создания контента:"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_content_category_keyboard(),
            parse_mode="Markdown"
        )
    
    elif callback_data == "category_planning":
        text = (
            "📅 **Планирование**\n\n"
            "Выбери функцию для планирования контента:"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_planning_category_keyboard(),
            parse_mode="Markdown"
        )
    
    elif callback_data == "category_analytics":
        text = (
            "📊 **Аналитика**\n\n"
            "Выбери функцию для анализа контента:"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_analytics_category_keyboard(),
            parse_mode="Markdown"
        )
    
    elif callback_data == "category_settings":
        text = (
            "⚙️ **Настройки**\n\n"
            "Выбери настройку:"
        )
        await query.edit_message_text(
            text,
            reply_markup=get_settings_category_keyboard(),
            parse_mode="Markdown"
        )
    
    elif callback_data == "category_back":
        await show_categories_menu(update, context)
    
    elif callback_data == "main_menu":
        await query.edit_message_text("🏠 Главное меню")
        # Отправляем новое сообщение с главным меню
        await query.message.reply_text(
            "Выбери действие:",
            reply_markup=get_main_menu_keyboard()
        )
    
    # Обработка выбора функций из категорий
    elif callback_data == "menu_text_gen":
        from bot.handlers.text_generation import show_text_generation_menu
        await query.edit_message_text("Переход к генерации текста...")
        await show_text_generation_menu(update, context)
    
    elif callback_data == "menu_image_gen":
        from bot.handlers.image_generation import show_image_generation_menu
        await query.edit_message_text("Переход к генерации изображения...")
        await show_image_generation_menu(update, context)
    
    elif callback_data == "menu_text_editor":
        from bot.handlers.text_editor import show_text_editor_menu
        await query.edit_message_text("Переход к редактору текста...")
        await show_text_editor_menu(update, context)
    
    elif callback_data == "menu_templates":
        from bot.handlers.templates import show_templates_menu
        await query.edit_message_text("Переход к шаблонам...")
        await show_templates_menu(update, context)
    
    elif callback_data == "menu_ab_test":
        from bot.handlers.ab_testing import show_ab_testing_menu
        await query.edit_message_text("Переход к A/B тестированию...")
        await show_ab_testing_menu(update, context)
    
    elif callback_data == "menu_post_series":
        from bot.handlers.post_series import show_post_series_menu
        await query.edit_message_text("Переход к генерации серии постов...")
        await show_post_series_menu(update, context)
    
    elif callback_data == "menu_content_plan":
        from bot.handlers.content_plan import show_content_plan_menu
        await query.edit_message_text("Переход к контент-плану...")
        await show_content_plan_menu(update, context)
    
    elif callback_data == "menu_calendar":
        from bot.handlers.calendar import show_calendar_menu
        await query.edit_message_text("Переход к календарю...")
        await show_calendar_menu(update, context)
    
    elif callback_data == "menu_history":
        from bot.handlers.history import show_history_menu
        await query.edit_message_text("Переход к истории...")
        await show_history_menu(update, context)
    
    elif callback_data == "menu_team":
        from bot.handlers.team import show_team_menu
        await query.edit_message_text("Переход к команде...")
        await show_team_menu(update, context)
    
    elif callback_data == "menu_statistics":
        from bot.handlers.analytics import show_statistics
        await query.edit_message_text("Переход к статистике...")
        await show_statistics(update, context)
    
    elif callback_data == "menu_settings":
        from bot.handlers.settings import show_settings_menu
        await query.edit_message_text("Переход к настройкам...")
        await show_settings_menu(update, context)
    
    elif callback_data == "menu_about":
        from bot.handlers.start import about_command
        await query.edit_message_text("Переход к информации о боте...")
        await about_command(update, context)
    
    elif callback_data == "menu_help":
        from bot.handlers.start import help_command
        await query.edit_message_text("Переход к справке...")
        await help_command(update, context)
    
    elif callback_data == "show_categories":
        await show_categories_menu(update, context)
    
    elif callback_data.startswith("quick_"):
        # Быстрый доступ
        if callback_data == "quick_text":
            from bot.handlers.text_generation import show_text_generation_menu
            await query.edit_message_text("Переход к генерации текста...")
            await show_text_generation_menu(update, context)
        elif callback_data == "quick_image":
            from bot.handlers.image_generation import show_image_generation_menu
            await query.edit_message_text("Переход к генерации изображения...")
            await show_image_generation_menu(update, context)
        elif callback_data == "quick_plan":
            from bot.handlers.content_plan import show_content_plan_menu
            await query.edit_message_text("Переход к контент-плану...")
            await show_content_plan_menu(update, context)
        elif callback_data == "quick_stats":
            from bot.handlers.analytics import show_statistics
            await query.edit_message_text("Переход к статистике...")
            await show_statistics(update, context)


def setup_smart_menu_handlers(application):
    """Настройка обработчиков умного меню"""
    # Обработчик кнопки "Категории"
    from telegram.ext import MessageHandler, filters
    application.add_handler(
        MessageHandler(filters.Regex("^📂 Категории$"), show_categories_menu)
    )
    
    # Обработчик callback для категорий
    application.add_handler(
        CallbackQueryHandler(handle_category_callback, pattern="^(category_|menu_|quick_|show_categories|main_menu)$")
    )

