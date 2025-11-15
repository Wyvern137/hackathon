"""
Умное меню с категориями и быстрым доступом
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, Dict, List
from bot.database.models import ContentHistory
from bot.database.database import get_db
from datetime import datetime, timedelta


def get_smart_menu_keyboard(user_id: Optional[int] = None, compact: bool = False) -> ReplyKeyboardMarkup:
    """
    Возвращает умное меню с категориями
    
    Args:
        user_id: ID пользователя для персонализации
        compact: Компактный режим (меньше кнопок)
    """
    if compact:
        # Компактное меню - только основные функции
        keyboard = [
            [
                KeyboardButton("📝 Текст"),
                KeyboardButton("🎨 Изображение")
            ],
            [
                KeyboardButton("📅 План"),
                KeyboardButton("📊 Статистика")
            ],
            [
                KeyboardButton("📂 Категории"),
                KeyboardButton("⚙️ Настройки")
            ]
        ]
    else:
        # Полное меню с категориями
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
                KeyboardButton("📋 Шаблоны")
            ],
            [
                KeyboardButton("📈 Статистика"),
                KeyboardButton("🔬 A/B тест")
            ],
            [
                KeyboardButton("📂 Категории"),
                KeyboardButton("⚙️ Настройки")
            ]
        ]
    
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_category_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает меню категорий для навигации
    """
    keyboard = [
        [
            InlineKeyboardButton("🎨 Создание контента", callback_data="category_content")
        ],
        [
            InlineKeyboardButton("📅 Планирование", callback_data="category_planning")
        ],
        [
            InlineKeyboardButton("📊 Аналитика", callback_data="category_analytics")
        ],
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="category_settings")
        ],
        [
            InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_content_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура категории 'Создание контента'"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Генерация текста", callback_data="menu_text_gen"),
            InlineKeyboardButton("🎨 Генерация изображения", callback_data="menu_image_gen")
        ],
        [
            InlineKeyboardButton("✏️ Редактор текста", callback_data="menu_text_editor"),
            InlineKeyboardButton("📋 Шаблоны", callback_data="menu_templates")
        ],
        [
            InlineKeyboardButton("🔬 A/B тест", callback_data="menu_ab_test"),
            InlineKeyboardButton("📚 Серия постов", callback_data="menu_post_series")
        ],
        [
            InlineKeyboardButton("◀️ Назад к категориям", callback_data="category_back"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_planning_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура категории 'Планирование'"""
    keyboard = [
        [
            InlineKeyboardButton("📅 Контент-план", callback_data="menu_content_plan"),
            InlineKeyboardButton("📆 Календарь", callback_data="menu_calendar")
        ],
        [
            InlineKeyboardButton("📊 История", callback_data="menu_history"),
            InlineKeyboardButton("👥 Команда", callback_data="menu_team")
        ],
        [
            InlineKeyboardButton("◀️ Назад к категориям", callback_data="category_back"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_analytics_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура категории 'Аналитика'"""
    keyboard = [
        [
            InlineKeyboardButton("📈 Статистика", callback_data="menu_statistics"),
            InlineKeyboardButton("📊 Анализ эффективности", callback_data="menu_effectiveness")
        ],
        [
            InlineKeyboardButton("💡 Рекомендации", callback_data="menu_recommendations"),
            InlineKeyboardButton("📉 Графики", callback_data="menu_charts")
        ],
        [
            InlineKeyboardButton("◀️ Назад к категориям", callback_data="category_back"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_settings_category_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура категории 'Настройки'"""
    keyboard = [
        [
            InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings"),
            InlineKeyboardButton("🏢 Профиль НКО", callback_data="menu_nko_profile")
        ],
        [
            InlineKeyboardButton("🔔 Уведомления", callback_data="menu_notifications"),
            InlineKeyboardButton("ℹ️ О боте", callback_data="menu_about")
        ],
        [
            InlineKeyboardButton("❓ Помощь", callback_data="menu_help")
        ],
        [
            InlineKeyboardButton("◀️ Назад к категориям", callback_data="category_back"),
            InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_quick_access_keyboard(user_id: Optional[int] = None) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру быстрого доступа к часто используемым функциям
    
    Args:
        user_id: ID пользователя для анализа предпочтений
    """
    # Анализируем предпочтения пользователя
    frequent_functions = []
    if user_id:
        with get_db() as db:
            # Получаем статистику использования за последние 30 дней
            month_ago = datetime.now() - timedelta(days=30)
            recent_content = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.generated_at >= month_ago
            ).all()
            
            # Подсчитываем частоту использования функций
            function_usage = {}
            for item in recent_content:
                func_name = "text" if item.content_type == "text" else "image" if item.content_type == "image" else "plan"
                function_usage[func_name] = function_usage.get(func_name, 0) + 1
            
            # Сортируем по частоте использования
            sorted_functions = sorted(function_usage.items(), key=lambda x: x[1], reverse=True)
            frequent_functions = [func[0] for func in sorted_functions[:3]]
    
    # Создаем клавиатуру с учетом предпочтений
    keyboard = []
    
    # Всегда показываем основные функции
    if not frequent_functions or "text" in frequent_functions:
        keyboard.append([InlineKeyboardButton("📝 Быстрый текст", callback_data="quick_text")])
    if not frequent_functions or "image" in frequent_functions:
        keyboard.append([InlineKeyboardButton("🎨 Быстрое изображение", callback_data="quick_image")])
    if not frequent_functions or "plan" in frequent_functions:
        keyboard.append([InlineKeyboardButton("📅 Быстрый план", callback_data="quick_plan")])
    
    keyboard.append([
        InlineKeyboardButton("📊 Статистика", callback_data="quick_stats"),
        InlineKeyboardButton("📂 Все функции", callback_data="show_categories")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def get_breadcrumbs_keyboard(current_location: str, previous_locations: List[str] = None) -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру с хлебными крошками для навигации
    
    Args:
        current_location: Текущее местоположение
        previous_locations: Список предыдущих местоположений
    """
    keyboard = []
    
    if previous_locations:
        # Показываем путь навигации
        breadcrumbs_text = " > ".join(previous_locations[-2:] + [current_location])
        keyboard.append([InlineKeyboardButton(f"📍 {breadcrumbs_text}", callback_data="breadcrumb_info")])
    
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="nav_back"),
        InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)

