"""
Главное меню и основные клавиатуры бота
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton
from bot.keyboards.smart_menu import get_smart_menu_keyboard


def get_main_menu_keyboard(user_id=None, compact=False) -> ReplyKeyboardMarkup:
    """
    Возвращает клавиатуру главного меню
    
    Args:
        user_id: ID пользователя для персонализации
        compact: Компактный режим
    """
    return get_smart_menu_keyboard(user_id=user_id, compact=compact)


def get_back_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Назад'"""
    keyboard = [[KeyboardButton("◀️ Назад")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Отмена'"""
    keyboard = [[KeyboardButton("❌ Отмена")]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_skip_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру с кнопкой 'Пропустить'"""
    keyboard = [
        [KeyboardButton("⏭️ Пропустить")],
        [KeyboardButton("❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

