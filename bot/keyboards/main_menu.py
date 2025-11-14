"""
Главное меню и основные клавиатуры бота
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру главного меню"""
    keyboard = [
        [
            KeyboardButton("📝 Генерация текста"),
            KeyboardButton("🎨 Генерация изображения")
        ],
        [
            KeyboardButton("✏️ Редактор текста"),
            KeyboardButton("📅 Контент-план")
        ],
        [
            KeyboardButton("📊 История"),
            KeyboardButton("⚙️ Настройки")
        ],
        [
            KeyboardButton("ℹ️ О боте"),
            KeyboardButton("❓ Помощь")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


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

