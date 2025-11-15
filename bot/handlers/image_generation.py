"""
Обработчики генерации изображений
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.main_menu import get_main_menu_keyboard
from bot.services.ai.image_ai import image_ai_service
from bot.services.ai.speech_recognition import speech_recognition_service

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
END = ConversationHandler.END


async def show_image_generation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню генерации изображений"""
    logger.info(f"show_image_generation_menu вызван для пользователя {update.effective_user.id}")
    
    text = (
        "🎨 **Генерация изображения**\n\n"
        "Опиши изображение, которое хочешь создать, или прикрепи референсные изображения.\n\n"
        "Отправь описание изображения:"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data['image_gen'] = {}
    context.user_data['_conversation_active'] = True
    
    logger.info(f"Установлено состояние: waiting_image_description для пользователя {update.effective_user.id}")
    return "waiting_image_description"


async def handle_image_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания изображения (текст или голосовое)"""
    description = None
    processing_msg = None
    
    # Проверяем, это текстовое или голосовое сообщение
    if update.message.voice:
        # Голосовое сообщение
        logger.info(f"Получено голосовое сообщение для генерации изображения")
        
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
                    "❌ Не удалось распознать голосовое сообщение или описание слишком короткое.\n\n"
                    "Попробуй еще раз или отправь описание текстом:"
                )
                return "waiting_image_description"
            
            description = transcribed_text.strip()
            
            # Показываем транскрипцию пользователю
            await processing_msg.edit_text(
                f"✅ Распознано:\n\n*{description}*\n\n"
                "Если нужно исправить, отправь описание текстом.\n\n"
                "⏳ Генерирую изображение...\n"
                "Это может занять некоторое время.",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.exception(f"Ошибка при распознавании голосового сообщения: {e}")
            await processing_msg.edit_text(
                "❌ Ошибка при распознавании голосового сообщения.\n\n"
                "Попробуй отправить описание текстом:"
            )
            return "waiting_image_description"
    
    elif update.message.text:
        # Текстовое сообщение
        description = update.message.text.strip()
        logger.info(f"✅ ConversationHandler перехватил сообщение для генерации изображения! Получен текст: {description[:50]}... (длина: {len(description)})")
        
        # Отправляем сообщение о генерации
        processing_msg = await update.message.reply_text(
            f"✅ Описание принято: {description}\n\n"
            f"⏳ Генерирую изображение...\n"
            f"Это может занять некоторое время."
        )
    
    if not description or len(description) < 3:
        await update.message.reply_text(
            "❌ Описание слишком короткое. Напиши хотя бы 3 символа:"
        )
        return "waiting_image_description"
    
    context.user_data['image_gen']['description'] = description
    context.user_data['_conversation_active'] = True
    
    logger.info(f"Описание сохранено в user_data: {description[:30]}...")
    
    # Если processing_msg не был создан (для текстового сообщения), создаем его
    if processing_msg is None:
        processing_msg = await update.message.reply_text(
            f"⏳ Генерирую изображение...\n"
            f"Это может занять некоторое время."
        )
    
    try:
        user_id = update.effective_user.id
        
        # Генерируем изображение
        result = await image_ai_service.generate_image(
            prompt=description,
            style="realistic",
            aspect_ratio="1:1",
            user_id=user_id
        )
        
        if result and result.get("success"):
            file_path = result.get("file_path")
            
            # Отправляем изображение пользователю
            from pathlib import Path
            image_path = Path(file_path)
            
            if image_path.exists():
                with open(image_path, 'rb') as photo:
                    await processing_msg.delete()
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"✅ **Готово!** Вот твоё изображение:\n\n*{description}*",
                        parse_mode="Markdown"
                    )
                
                context.user_data.pop('_conversation_active', None)
                await update.message.reply_text(
                    "Изображение готово! Можешь использовать его для поста или сохранить.",
                    reply_markup=get_main_menu_keyboard()
                )
                return END
            else:
                await processing_msg.edit_text(
                    "❌ Файл изображения не найден. Попробуй еще раз."
                )
                context.user_data.pop('_conversation_active', None)
                return END
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Ошибка генерации'
            await processing_msg.edit_text(
                f"❌ Ошибка при генерации изображения: {error_msg}\n\n"
                f"Попробуй изменить описание или проверь настройки API."
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации изображения: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз."
        )
        context.user_data.pop('_conversation_active', None)
        return END


def setup_image_generation_handlers(application):
    """Настройка обработчиков генерации изображений"""
    # ConversationHandler для генерации изображений
    image_gen_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^🎨 Генерация изображения$"),
                show_image_generation_menu
            ),
        ],
        states={
            "waiting_image_description": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image_description),
                MessageHandler(filters.VOICE, handle_image_description)
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True
    )
    
    application.add_handler(image_gen_handler)
    logger.info("Обработчики генерации изображений настроены")

