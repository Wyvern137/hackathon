"""
Общие обработчики (кнопки, навигация и т.д.)
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.main_menu import get_main_menu_keyboard, get_back_keyboard, get_cancel_keyboard
from telegram.ext import ConversationHandler

logger = logging.getLogger(__name__)


async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    menu_text = "🏠 Главное меню"
    await update.message.reply_text(
        menu_text,
        reply_markup=get_main_menu_keyboard()
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущего диалога"""
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    # Очищаем данные контекста
    if context.user_data:
        context.user_data.clear()
    return ConversationHandler.END


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатий кнопок главного меню
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Важно: этот обработчик должен быть ПОСЛЕДНИМ, чтобы ConversationHandler обрабатывали сообщения первыми
    # Но на всякий случай проверяем, есть ли активное состояние ConversationHandler
    # ConversationHandler автоматически отслеживает состояние через context.user_data
    
    # Проверяем, есть ли активная беседа через флаг
    if context.user_data:
        conversation_active = context.user_data.get('_conversation_active')
        if conversation_active:
            logger.info(f"⚠️ ConversationHandler активен (флаг), пропускаем обработку в button_handler. Текст: {update.message.text[:30] if update.message else 'N/A'}")
            return None  # Возвращаем None, чтобы пропустить обработку
        
        # Также проверяем наличие признаков активной беседы через ConversationHandler
        # ConversationHandler хранит состояние в context.user_data под ключом с состоянием
        # Проверяем явные признаки активной беседы
        text_gen_mode = context.user_data.get('text_gen_mode')
        if text_gen_mode == 'free':
            # Если режим 'free', но текст еще не получен, значит ждем текст
            if not context.user_data.get('free_text'):
                logger.info(f"⚠️ ConversationHandler активен (free text, ожидаем текст), пропускаем обработку в button_handler. Текст: {update.message.text[:30] if update.message else 'N/A'}")
                return None  # Возвращаем None, чтобы пропустить обработку
        
        if text_gen_mode == 'examples':
            logger.info(f"⚠️ ConversationHandler активен (examples), пропускаем обработку в button_handler")
            return None
    
    query = update.message.text
    logger.info(f"Обработка текста в button_handler: {query[:50]}")
    
    # Импортируем обработчики здесь, чтобы избежать циклических импортов
    if query == "📝 Генерация текста":
        from bot.handlers.text_generation import show_text_generation_menu
        return await show_text_generation_menu(update, context)
    
    elif query == "🎨 Генерация изображения":
        from bot.handlers.image_generation import show_image_generation_menu
        return await show_image_generation_menu(update, context)
    
    elif query == "✏️ Редактор текста":
        from bot.handlers.text_editor import show_text_editor_menu
        return await show_text_editor_menu(update, context)
    
    elif query == "📅 Контент-план":
        from bot.handlers.content_plan import show_content_plan_menu
        return await show_content_plan_menu(update, context)
    
    elif query == "📊 История":
        from bot.handlers.history import show_history_menu
        return await show_history_menu(update, context)
    
    elif query == "⚙️ Настройки":
        from bot.handlers.settings import show_settings_menu
        return await show_settings_menu(update, context)
    
    elif query == "ℹ️ О боте":
        from bot.handlers.start import about_command
        return await about_command(update, context)
    
    elif query == "❓ Помощь":
        from bot.handlers.start import help_command
        return await help_command(update, context)
    
    elif query == "◀️ Назад":
        return await back_to_menu(update, context)
    
    elif query == "❌ Отмена":
        return await cancel_conversation(update, context)
    
    else:
        await update.message.reply_text(
            "Не понимаю эту команду. Используй кнопки меню или /start",
            reply_markup=get_main_menu_keyboard()
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ошибок бота
    """
    logger.error(f"Ошибка при обработке обновления: {context.error}", exc_info=context.error)
    
    if isinstance(update, Update) and update.effective_message:
        error_text = (
            "😔 Произошла ошибка при обработке запроса.\n\n"
            "Попробуй еще раз или используй команду /start для возврата в главное меню."
        )
        await update.effective_message.reply_text(error_text)

