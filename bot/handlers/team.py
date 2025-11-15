"""
Обработчики командной работы (базовая реализация)
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory
from bot.database.database import get_db

logger = logging.getLogger(__name__)


async def show_team_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню командной работы"""
    # Используем расширенное меню
    from bot.handlers.team_advanced import show_team_advanced_menu
    await show_team_advanced_menu(update, context)


async def team_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback командной работы"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "team_my_posts":
        user_id = update.effective_user.id
        
        with get_db() as db:
            posts = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == "text"
            ).order_by(ContentHistory.generated_at.desc()).limit(10).all()
        
        if not posts:
            await query.edit_message_text(
                "📋 **Мои посты**\n\n"
                "У тебя пока нет сохраненных постов.\n\n"
                "Создай пост через генерацию текста!",
                parse_mode="Markdown"
            )
        else:
            text = "📋 **Мои последние посты**\n\n"
            for i, post in enumerate(posts[:5], 1):
                date_str = post.generated_at.strftime("%d.%m.%Y")
                content_data = post.content_data if isinstance(post.content_data, dict) else {}
                post_text = content_data.get("text", str(post.content_data))[:50]
                text += f"{i}. {date_str}: {post_text}...\n\n"
            
            await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "team_comments":
        await query.edit_message_text(
            "💬 **Комментарии**\n\n"
            "Функция комментариев будет доступна в следующих версиях.\n\n"
            "Сейчас ты можешь использовать редактор текста для улучшения постов.",
            parse_mode="Markdown"
        )
    
    elif callback_data == "main_menu":
        await query.edit_message_text("Возврат в главное меню")
        return
    
    return


def setup_team_handlers(application):
    """Настройка обработчиков командной работы"""
    from telegram.ext import CallbackQueryHandler
    
    application.add_handler(
        CallbackQueryHandler(team_callback, pattern="^team_")
    )


