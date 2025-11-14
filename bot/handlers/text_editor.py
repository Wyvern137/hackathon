"""
Обработчики редактора текста
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from bot.services.ai.openrouter import openrouter_api
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory
from bot.database.database import get_db

logger = logging.getLogger(__name__)


async def show_text_editor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню редактора текста"""
    text = (
        "✏️ **Редактор текста**\n\n"
        "Отправь текст для редактирования. Я проверю его на:\n"
        "• Орфографические ошибки\n"
        "• Грамматические ошибки\n"
        "• Стилистические недочеты\n"
        "• Логические несоответствия\n\n"
        "И предложу рекомендации по улучшению."
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    return "waiting_text"


async def handle_text_for_editing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для редактирования"""
    text = update.message.text
    
    if not text or len(text.strip()) < 10:
        await update.message.reply_text(
            "❌ Текст слишком короткий. Напиши хотя бы 10 символов:"
        )
        return "waiting_text"
    
    # Отправляем сообщение о обработке
    processing_msg = await update.message.reply_text("⏳ Анализирую текст...")
    
    try:
        # Формируем промпт для редактирования
        prompt = f"""Проанализируй следующий текст поста для социальных сетей и исправь его:

{text}

Проанализируй:
1. Орфографические ошибки
2. Грамматические ошибки
3. Пунктуационные ошибки
4. Стилистические недочеты
5. Логические несоответствия
6. Читаемость текста

Предоставь:
1. Исправленный текст
2. Список исправлений с пояснениями
3. Рекомендации по улучшению текста
4. Оценку качества текста (1-10)

Формат ответа:
ИСПРАВЛЕННЫЙ ТЕКСТ:
[исправленный текст]

ИСПРАВЛЕНИЯ:
- [описание исправления 1]
- [описание исправления 2]

РЕКОМЕНДАЦИИ:
- [рекомендация 1]
- [рекомендация 2]

ОЦЕНКА: [оценка]/10"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по редактированию текстов и корректуре.",
            temperature=0.3,
            max_tokens=800
        )
        
        if result and result.get("success"):
            edited_content = result.get("content", "")
            
            # Сохраняем в историю
            user_id = update.effective_user.id
            get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
            
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "original_text": text,
                        "edited_text": edited_content,
                        "type": "edited"
                    }
                )
                db.add(history_entry)
                db.commit()
            
            await processing_msg.edit_text(
                f"✅ **Редактирование завершено!**\n\n{edited_content}",
                parse_mode="Markdown"
            )
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при редактировании текста. Попробуй еще раз."
            )
    
    except Exception as e:
        logger.exception(f"Ошибка при редактировании текста: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при редактировании. Попробуй еще раз."
        )
    
    from telegram.ext import ConversationHandler
    return ConversationHandler.END


def setup_text_editor_handlers(application):
    """Настройка обработчиков редактора текста"""
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^✏️ Редактор текста$"), show_text_editor_menu),
        ],
        states={
            "waiting_text": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_editing)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)

