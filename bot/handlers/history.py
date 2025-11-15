"""
Обработчики истории контента
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory
from bot.database.database import get_db
from bot.utils.export import export_history_to_txt, export_texts_to_csv

logger = logging.getLogger(__name__)


async def show_history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню истории"""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    with get_db() as db:
        history_items = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id
        ).order_by(ContentHistory.generated_at.desc()).limit(10).all()
    
    if not history_items:
        await update.message.reply_text(
            "📊 **История**\n\n"
            "У тебя пока нет сохраненного контента.\n\n"
            "Сгенерируй текст или изображение, чтобы увидеть их здесь.",
            parse_mode="Markdown"
        )
        return
    
    text = "📊 **История контента**\n\n"
    
    for i, item in enumerate(history_items[:5], 1):
        date_str = item.generated_at.strftime("%d.%m.%Y %H:%M")
        item_text = "📝 Текст" if item.content_type == "text" else "🎨 Изображение"
        preview = ""
        
        if item.content_type == "text":
            content_text = item.content_data.get("text", "") if isinstance(item.content_data, dict) else str(item.content_data)
            preview = content_text[:50] + "..." if len(content_text) > 50 else content_text
        
        text += f"{i}. {item_text} - {date_str}\n"
        if preview:
            text += f"   {preview}\n"
        text += "\n"
    
    if len(history_items) > 5:
        text += f"\n... и еще {len(history_items) - 5} элементов"
    
    # Кнопки экспорта
    export_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📥 Экспорт TXT", callback_data="export_history_txt"),
            InlineKeyboardButton("📊 Экспорт CSV", callback_data="export_history_csv")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=export_keyboard, parse_mode="Markdown")


async def handle_export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка экспорта истории"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    if callback_data == "export_history_txt":
        await query.edit_message_text("⏳ Экспортирую историю в TXT...")
        
        file_path = await export_history_to_txt(user_id)
        
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption="✅ История экспортирована в TXT файл"
                )
            await query.edit_message_text("✅ Экспорт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при экспорте. Попробуй еще раз.")
    
    elif callback_data == "export_history_csv":
        await query.edit_message_text("⏳ Экспортирую тексты в CSV...")
        
        file_path = await export_texts_to_csv(user_id)
        
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption="✅ Тексты экспортированы в CSV файл"
                )
            await query.edit_message_text("✅ Экспорт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при экспорте. Попробуй еще раз.")


def setup_history_handlers(application):
    """Настройка обработчиков истории"""
    from telegram.ext import CallbackQueryHandler
    # Callback для экспорта
    application.add_handler(
        CallbackQueryHandler(handle_export_callback, pattern="^export_history_")
    )

