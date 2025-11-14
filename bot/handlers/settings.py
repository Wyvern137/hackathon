"""
Обработчики настроек
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.helpers import get_or_create_user
from bot.database.models import NKOProfile
from bot.database.database import get_db
from bot.keyboards.inline import get_nko_setup_start_keyboard

logger = logging.getLogger(__name__)


async def show_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню настроек"""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    with get_db() as db:
        nko_profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
    
    text = "⚙️ **Настройки**\n\n"
    
    if nko_profile and nko_profile.is_complete:
        text += f"✅ Профиль НКО настроен\n"
        if nko_profile.organization_name:
            text += f"Организация: {nko_profile.organization_name}\n"
        text += "\nТы можешь обновить профиль, нажав кнопку ниже."
        await update.message.reply_text(
            text,
            reply_markup=get_nko_setup_start_keyboard(),
            parse_mode="Markdown"
        )
    else:
        text += "❌ Профиль НКО не настроен\n\n"
        text += "Создай профиль, чтобы я мог генерировать более релевантный контент."
        await update.message.reply_text(
            text,
            reply_markup=get_nko_setup_start_keyboard(),
            parse_mode="Markdown"
        )


def setup_settings_handlers(application):
    """Настройка обработчиков настроек"""
    pass

