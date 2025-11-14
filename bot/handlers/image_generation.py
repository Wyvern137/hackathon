"""
Обработчики генерации изображений
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def show_image_generation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню генерации изображений"""
    text = (
        "🎨 **Генерация изображения**\n\n"
        "Опиши изображение, которое хочешь создать, или прикрепи референсные изображения.\n\n"
        "Отправь описание изображения:"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data['image_gen'] = {}
    return "waiting_image_description"


async def handle_image_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания изображения"""
    description = update.message.text
    context.user_data['image_gen']['description'] = description
    
    await update.message.reply_text(
        f"✅ Описание принято!\n\n"
        f"⚠️ Генерация изображений временно недоступна.\n"
        f"Функция будет добавлена в ближайшее время."
    )
    
    from telegram.ext import ConversationHandler
    return ConversationHandler.END


def setup_image_generation_handlers(application):
    """Настройка обработчиков генерации изображений"""
    # TODO: Реализовать полную функциональность генерации изображений
    pass

