"""
Inline клавиатуры для бота
"""
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from typing import Optional, List


def get_text_generation_types_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа генерации текста"""
    keyboard = [
        [
            InlineKeyboardButton("📝 Свободный текст", callback_data="text_gen_free"),
            InlineKeyboardButton("📋 Структурированная форма", callback_data="text_gen_structured")
        ],
        [
            InlineKeyboardButton("📚 На основе примеров", callback_data="text_gen_examples")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_style_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора стиля написания"""
    keyboard = [
        [
            InlineKeyboardButton("💬 Разговорный", callback_data="style_conversational"),
            InlineKeyboardButton("📄 Официальный", callback_data="style_formal")
        ],
        [
            InlineKeyboardButton("✨ Художественный", callback_data="style_artistic"),
            InlineKeyboardButton("📊 Нейтральный", callback_data="style_neutral")
        ],
        [
            InlineKeyboardButton("😊 Дружелюбный", callback_data="style_friendly")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_post_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура действий с готовым постом"""
    keyboard = [
        [
            InlineKeyboardButton("💾 Сохранить", callback_data="save_post"),
            InlineKeyboardButton("✏️ Редактировать", callback_data="edit_post")
        ],
        [
            InlineKeyboardButton("🔄 Перегенерировать", callback_data="regenerate_post"),
            InlineKeyboardButton("📝 В редактор", callback_data="to_editor")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_image_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек генерации изображения"""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Реалистичное", callback_data="img_style_realistic"),
            InlineKeyboardButton("🖼️ Иллюстрация", callback_data="img_style_illustration")
        ],
        [
            InlineKeyboardButton("📐 Графика", callback_data="img_style_graphics"),
            InlineKeyboardButton("📷 Фотография", callback_data="img_style_photo")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_image_aspect_ratio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора соотношения сторон изображения"""
    keyboard = [
        [
            InlineKeyboardButton("⬜ 1:1 (Квадрат)", callback_data="aspect_1_1"),
            InlineKeyboardButton("⬛ 16:9 (Горизонтальное)", callback_data="aspect_16_9")
        ],
        [
            InlineKeyboardButton("▫️ 9:16 (Вертикальное)", callback_data="aspect_9_16")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="img_settings")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_image_actions_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура действий с готовым изображением"""
    keyboard = [
        [
            InlineKeyboardButton("💾 Сохранить", callback_data="save_image"),
            InlineKeyboardButton("🔄 Перегенерировать", callback_data="regenerate_image")
        ],
        [
            InlineKeyboardButton("📝 Использовать для поста", callback_data="use_for_post")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_event_type_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа события для структурированной формы"""
    keyboard = [
        [
            InlineKeyboardButton("📰 Новость", callback_data="event_news"),
            InlineKeyboardButton("📅 Анонс", callback_data="event_announcement")
        ],
        [
            InlineKeyboardButton("📊 Отчет", callback_data="event_report"),
            InlineKeyboardButton("🙏 Благодарность", callback_data="event_thanks")
        ],
        [
            InlineKeyboardButton("🎉 Поздравление", callback_data="event_congratulations"),
            InlineKeyboardButton("📢 Объявление", callback_data="event_announcement")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="text_gen_types")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_content_plan_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода для контент-плана"""
    keyboard = [
        [
            InlineKeyboardButton("📅 1 неделя", callback_data="plan_period_1w"),
            InlineKeyboardButton("📅 2 недели", callback_data="plan_period_2w")
        ],
        [
            InlineKeyboardButton("📅 1 месяц", callback_data="plan_period_1m"),
            InlineKeyboardButton("📅 3 месяца", callback_data="plan_period_3m")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_yes_no_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура Да/Нет"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да", callback_data="yes"),
            InlineKeyboardButton("❌ Нет", callback_data="no")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_history_pagination_keyboard(page: int, total_pages: int, callback_prefix: str = "history") -> InlineKeyboardMarkup:
    """Клавиатура пагинации для истории"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    if page > 1:
        nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"{callback_prefix}_page_{page-1}"))
    nav_buttons.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"{callback_prefix}_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_nko_setup_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура начала настройки профиля НКО"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, создать профиль", callback_data="nko_setup_start"),
            InlineKeyboardButton("⏭️ Пропустить", callback_data="nko_setup_skip")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_activity_types_keyboard(selected: Optional[List[str]] = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора типов деятельности НКО"""
    if selected is None:
        selected = []
    
    activity_types = [
        ("🌱 Экология", "activity_environmental"),
        ("🐾 Помощь животным", "activity_animal_welfare"),
        ("👥 Помощь людям", "activity_humanitarian"),
        ("📚 Образование", "activity_education"),
        ("🎭 Культура", "activity_culture"),
        ("🏥 Здоровье", "activity_health"),
        ("🤝 Социальная помощь", "activity_social"),
    ]
    
    keyboard = []
    for name, callback_data in activity_types:
        is_selected = callback_data in selected
        prefix = "✅ " if is_selected else ""
        keyboard.append([
            InlineKeyboardButton(
                f"{prefix}{name}",
                callback_data=f"toggle_{callback_data}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("✅ Готово", callback_data="activity_types_done"),
        InlineKeyboardButton("◀️ Назад", callback_data="nko_setup_back")
    ])
    
    return InlineKeyboardMarkup(keyboard)

