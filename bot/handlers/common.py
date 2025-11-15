"""
Общие обработчики (кнопки, навигация и т.д.)
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.main_menu import get_main_menu_keyboard, get_back_keyboard, get_cancel_keyboard
from telegram.ext import ConversationHandler
from bot.services.ai.speech_recognition import speech_recognition_service

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


async def handle_voice_in_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработка голосовых сообщений в главном меню
    
    Распознает голосовое сообщение, определяет намерение и переходит к соответствующей функции
    """
    if not update.message.voice:
        return None
    
    # Проверяем, нет ли активной беседы (ConversationHandler)
    if context.user_data.get('_conversation_active'):
        logger.info("ConversationHandler активен, пропускаем обработку голосового в главном меню")
        return None
    
    # Проверяем, не был ли недавно отправлен /start (это обрабатывается отдельным обработчиком)
    if context.user_data.get('_started_recently'):
        logger.info("Недавно был /start, пропускаем обработку голосового в главном меню")
        return None
    
    user = update.effective_user
    logger.info(f"Получено голосовое сообщение в главном меню от пользователя {user.id}")
    
    # Показываем индикатор обработки
    processing_msg = await update.message.reply_text(
        "🎤 Распознаю голосовое сообщение...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Распознаем речь
        transcribed_text = await speech_recognition_service.transcribe_voice_message(
            voice_file_id=update.message.voice.file_id,
            bot=context.bot
        )
        
        if not transcribed_text or len(transcribed_text.strip()) < 3:
            await processing_msg.edit_text(
                "❌ Не удалось распознать голосовое сообщение.\n\n"
                "Попробуй еще раз или используй кнопки меню.",
                reply_markup=get_main_menu_keyboard()
            )
            return None
        
        transcribed_text = transcribed_text.strip()
        
        # Показываем транскрипцию
        await processing_msg.edit_text(
            f"✅ Распознано: *{transcribed_text}*\n\n"
            "Определяю намерение...",
            parse_mode="Markdown"
        )
        
        # Определяем намерение
        intent_result = await speech_recognition_service.detect_intent(transcribed_text)
        intent = intent_result.get('intent', 'other')
        
        logger.info(f"Определено намерение: {intent}")
        
        # Переходим к соответствующей функции
        if intent == "text_generation":
            await processing_msg.edit_text(
                f"✅ Понял! Ты хочешь создать текст.\n\n"
                f"Распознано: *{transcribed_text}*",
                parse_mode="Markdown"
            )
            
            # Сохраняем распознанный текст для использования
            context.user_data['free_text'] = transcribed_text
            context.user_data['text_gen_mode'] = 'free'
            context.user_data['_conversation_active'] = True
            
            # Показываем меню генерации текста и автоматически выбираем свободный текст
            from bot.handlers.text_generation import text_generation_type_callback
            from telegram import CallbackQuery
            
            # Создаем фиктивный callback query
            fake_query = type('obj', (object,), {
                'data': 'text_gen_free',
                'answer': lambda: None,
                'edit_message_text': lambda text, **kwargs: update.message.reply_text(text, **kwargs)
            })()
            
            fake_update = type('obj', (object,), {
                'callback_query': fake_query,
                'effective_user': update.effective_user
            })()
            
            return await text_generation_type_callback(fake_update, context)
            
        elif intent == "image_generation":
            await processing_msg.edit_text(
                f"✅ Понял! Ты хочешь создать изображение.\n\n"
                f"Распознано: *{transcribed_text}*",
                parse_mode="Markdown"
            )
            
            # Сохраняем описание
            context.user_data['image_gen'] = {'description': transcribed_text}
            context.user_data['_conversation_active'] = True
            
            # Вызываем обработчик описания напрямую
            from bot.handlers.image_generation import handle_image_description
            return await handle_image_description(update, context)
            
        else:
            await processing_msg.edit_text(
                f"✅ Распознано: *{transcribed_text}*\n\n"
                "Не совсем понял, что ты хочешь сделать.\n\n"
                "Используй кнопки меню или скажи:\n"
                "• \"хочу создать текст\" или \"сгенерируй текст\"\n"
                "• \"хочу создать изображение\" или \"сгенерируй изображение\"",
                parse_mode="Markdown",
                reply_markup=get_main_menu_keyboard()
            )
            return None
            
    except Exception as e:
        logger.exception(f"Ошибка при обработке голосового в главном меню: {e}")
        await processing_msg.edit_text(
            "❌ Ошибка при обработке голосового сообщения.\n\n"
            "Попробуй использовать кнопки меню.",
            reply_markup=get_main_menu_keyboard()
        )
        return None


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
        
        # Проверяем активную генерацию изображений
        image_gen = context.user_data.get('image_gen')
        if image_gen and not image_gen.get('description'):
            logger.info(f"⚠️ ConversationHandler активен (image generation, ожидаем описание), пропускаем обработку в button_handler")
            return None
        
        # Проверяем активное создание контент-плана
        content_plan = context.user_data.get('content_plan')
        if content_plan:
            logger.info(f"⚠️ ConversationHandler активен (content plan), пропускаем обработку в button_handler")
            return None
        
        # Проверяем активный редактор текста
        # Редактор текста использует ConversationHandler с состоянием "waiting_text"
        # Проверяем наличие этого состояния в user_data
        if any(state in str(context.user_data) for state in ["waiting_text", "text_editor"]):
            logger.info(f"⚠️ ConversationHandler активен (text editor), пропускаем обработку в button_handler")
            return None
        
        # Проверяем активную структурированную форму
        if context.user_data.get('text_gen_mode') == 'structured':
            structured_data = context.user_data.get('structured_data')
            if structured_data:
                logger.info(f"⚠️ ConversationHandler активен (structured form), пропускаем обработку в button_handler")
                return None
    
    query = update.message.text
    logger.info(f"Обработка текста в button_handler: {query[:50]}")
    
    # Импортируем обработчики здесь, чтобы избежать циклических импортов
    if query == "📝 Генерация текста":
        from bot.handlers.text_generation import show_text_generation_menu
        return await show_text_generation_menu(update, context)
    
    elif query == "🎨 Генерация изображения":
        # НЕ вызываем show_image_generation_menu здесь напрямую,
        # так как это может конфликтовать с ConversationHandler
        # ConversationHandler сам обработает это через entry_points
        # Но нужно активировать ConversationHandler явно
        from bot.handlers.image_generation import show_image_generation_menu
        result = await show_image_generation_menu(update, context)
        return result
    
    elif query == "✏️ Редактор текста":
        from bot.handlers.text_editor import show_text_editor_menu
        return await show_text_editor_menu(update, context)
    
    elif query == "📅 Контент-план":
        from bot.handlers.content_plan import show_content_plan_menu
        return await show_content_plan_menu(update, context)
    
    elif query == "📊 История":
        from bot.handlers.history import show_history_menu
        return await show_history_menu(update, context)
    
    elif query == "📋 Шаблоны":
        from bot.handlers.templates import show_templates_menu
        await show_templates_menu(update, context)
        return None
    
    elif query == "📈 Статистика":
        from bot.handlers.analytics import show_statistics
        await show_statistics(update, context)
        return None
    
    elif query == "🔬 A/B тест":
        from bot.handlers.ab_testing import show_ab_testing_menu
        return await show_ab_testing_menu(update, context)
    
    elif query == "📅 Календарь":
        from bot.handlers.calendar import show_calendar_menu
        await show_calendar_menu(update, context)
        return None
    
    elif query == "👥 Команда":
        from bot.handlers.team import show_team_menu
        await show_team_menu(update, context)
        return None
    
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

