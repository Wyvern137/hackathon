"""
Обработчики оптимизации контента под платформы
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler
from bot.services.content.platform_optimizer import platform_optimizer, Platform
from bot.keyboards.platform_keyboard import get_platform_optimization_keyboard, parse_platform_callback
from bot.keyboards.inline import get_post_actions_keyboard

logger = logging.getLogger(__name__)


async def handle_platform_optimization_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора платформы для оптимизации"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "optimize_platform":
        # Показываем меню выбора платформы
        await query.edit_message_text(
            "📱 **Оптимизация под платформу**\n\n"
            "Выбери платформу для оптимизации текста:",
            reply_markup=get_platform_optimization_keyboard(),
            parse_mode="Markdown"
        )
        return
    
    if callback_data == "optimize_back":
        # Возвращаемся к посту
        last_text = context.user_data.get('last_generated_text', '')
        if last_text:
            await query.edit_message_text(
                f"✅ **Готово!** Вот твой пост:\n\n{last_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
        return
    
    if callback_data.startswith("optimize_"):
        # Оптимизируем текст под выбранную платформу
        platform = parse_platform_callback(callback_data)
        last_text = context.user_data.get('last_generated_text', '')
        
        if not last_text:
            await query.answer("Текст не найден", show_alert=True)
            return
        
        await query.edit_message_text(
            f"⏳ Оптимизирую текст под {platform.value}...",
            parse_mode="Markdown"
        )
        
        # Оптимизируем
        optimized = platform_optimizer.optimize_text(last_text, platform)
        optimized_text = optimized["text"]
        
        # Сохраняем информацию о платформе
        context.user_data['platform_optimized'] = True
        context.user_data['selected_platform'] = platform
        context.user_data['platform_info'] = optimized
        context.user_data['last_generated_text'] = optimized_text
        
        platform_names = {
            Platform.TELEGRAM: "Telegram",
            Platform.VK: "ВКонтакте",
            Platform.INSTAGRAM: "Instagram",
            Platform.FACEBOOK: "Facebook",
            Platform.TWITTER: "Twitter/X",
            Platform.OK: "Одноклассники"
        }
        
        await query.edit_message_text(
            f"✅ **Текст оптимизирован под {platform_names.get(platform, platform.value)}**\n\n"
            f"{optimized_text}\n\n"
            f"📊 *Статистика:*\n"
            f"• Исходная длина: {optimized['original_length']} символов\n"
            f"• Оптимизированная длина: {optimized['optimized_length']} символов\n"
            f"• Хештегов: {optimized['hashtags_count']}",
            reply_markup=get_post_actions_keyboard(show_platform_optimize=False),
            parse_mode="Markdown"
        )


def setup_platform_optimization_handlers(application):
    """Настройка обработчиков оптимизации под платформы"""
    application.add_handler(
        CallbackQueryHandler(handle_platform_optimization_callback, pattern="^(optimize_|platform_)")
    )

