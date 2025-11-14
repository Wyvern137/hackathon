"""
Обработчики контент-плана
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.inline import get_content_plan_period_keyboard
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def show_content_plan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню контент-плана"""
    text = (
        "📅 **Контент-план**\n\n"
        "Создам план публикаций на заданный период.\n\n"
        "Выбери период для контент-плана:"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_content_plan_period_keyboard(),
        parse_mode="Markdown"
    )


async def content_plan_period_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора периода контент-плана"""
    query = update.callback_query
    await query.answer()
    
    period_map = {
        "plan_period_1w": 7,
        "plan_period_2w": 14,
        "plan_period_1m": 30,
        "plan_period_3m": 90
    }
    
    callback_data = query.data
    
    if callback_data in period_map:
        period_days = period_map[callback_data]
        context.user_data['content_plan'] = {'period_days': period_days}
        
        await query.edit_message_text(
            f"✅ Период выбран: {period_days} дней\n\n"
            f"⚠️ Создание контент-плана временно недоступно.\n"
            f"Функция будет добавлена в ближайшее время."
        )
    
    from telegram.ext import ConversationHandler
    return ConversationHandler.END


def setup_content_plan_handlers(application):
    """Настройка обработчиков контент-плана"""
    application.add_handler(
        CallbackQueryHandler(
            content_plan_period_callback,
            pattern="^plan_period_"
        )
    )

