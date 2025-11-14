"""
Обработчики истории контента
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory
from bot.database.database import get_db

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
    
    await update.message.reply_text(text, parse_mode="Markdown")


def setup_history_handlers(application):
    """Настройка обработчиков истории"""
    pass

