"""
Клавиатуры для выбора платформы
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.content.platform_optimizer import Platform


def get_platform_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора платформы для генерации текста"""
    keyboard = [
        [
            InlineKeyboardButton("✈️ Telegram", callback_data="platform_telegram"),
            InlineKeyboardButton("👥 ВКонтакте", callback_data="platform_vk")
        ],
        [
            InlineKeyboardButton("📷 Instagram", callback_data="platform_instagram"),
            InlineKeyboardButton("📘 Facebook", callback_data="platform_facebook")
        ],
        [
            InlineKeyboardButton("🐦 Twitter/X", callback_data="platform_twitter"),
            InlineKeyboardButton("👤 Одноклассники", callback_data="platform_ok")
        ],
        [
            InlineKeyboardButton("⏭️ Пропустить", callback_data="platform_skip"),
            InlineKeyboardButton("◀️ Назад", callback_data="platform_back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_platform_optimization_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для оптимизации готового текста под платформу"""
    keyboard = [
        [
            InlineKeyboardButton("✈️ Telegram", callback_data="optimize_telegram"),
            InlineKeyboardButton("👥 ВКонтакте", callback_data="optimize_vk")
        ],
        [
            InlineKeyboardButton("📷 Instagram", callback_data="optimize_instagram"),
            InlineKeyboardButton("📘 Facebook", callback_data="optimize_facebook")
        ],
        [
            InlineKeyboardButton("🐦 Twitter/X", callback_data="optimize_twitter"),
            InlineKeyboardButton("👤 Одноклассники", callback_data="optimize_ok")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="optimize_back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def parse_platform_callback(callback_data: str) -> Platform:
    """Парсит callback_data и возвращает Platform enum"""
    platform_map = {
        "platform_telegram": Platform.TELEGRAM,
        "platform_vk": Platform.VK,
        "platform_instagram": Platform.INSTAGRAM,
        "platform_facebook": Platform.FACEBOOK,
        "platform_twitter": Platform.TWITTER,
        "platform_ok": Platform.OK,
        "optimize_telegram": Platform.TELEGRAM,
        "optimize_vk": Platform.VK,
        "optimize_instagram": Platform.INSTAGRAM,
        "optimize_facebook": Platform.FACEBOOK,
        "optimize_twitter": Platform.TWITTER,
        "optimize_ok": Platform.OK
    }
    return platform_map.get(callback_data, Platform.TELEGRAM)

