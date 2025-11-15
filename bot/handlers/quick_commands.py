"""
Обработчики команд быстрого доступа
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from bot.handlers.text_generation import show_text_generation_menu, handle_free_text
from bot.handlers.image_generation import show_image_generation_menu, handle_image_description
from bot.handlers.content_plan import show_content_plan_menu
from bot.handlers.analytics import show_statistics

logger = logging.getLogger(__name__)


async def quick_text_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /текст [идея] - быстрая генерация текста
    
    Использование:
    /текст хочу написать пост о новом приюте
    """
    user_text = " ".join(context.args) if context.args else None
    
    if user_text:
        # Сохраняем текст для обработки
        context.user_data['free_text'] = user_text
        context.user_data['text_gen_mode'] = 'free'
        context.user_data['_conversation_active'] = True
        
        # Показываем меню выбора стиля или сразу генерируем
        from bot.keyboards.inline import get_style_keyboard
        await update.message.reply_text(
            f"📝 **Быстрая генерация текста**\n\n"
            f"Твоя идея: *{user_text}*\n\n"
            f"Выбери стиль написания:",
            reply_markup=get_style_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Если текст не указан, показываем меню генерации
        await show_text_generation_menu(update, context)


async def quick_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /изображение [описание] - быстрая генерация изображения
    
    Использование:
    /изображение красивая природа с животными
    """
    description = " ".join(context.args) if context.args else None
    
    if description:
        # Сохраняем описание для обработки
        context.user_data['image_gen'] = {'description': description}
        context.user_data['_conversation_active'] = True
        
        # Вызываем обработчик описания
        await handle_image_description(update, context)
    else:
        # Если описание не указано, показываем меню генерации
        await show_image_generation_menu(update, context)


async def quick_plan_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /план - быстрый доступ к контент-плану
    """
    await show_content_plan_menu(update, context)


async def quick_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /статистика - быстрый просмотр статистики
    """
    await show_statistics(update, context)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /поиск [запрос] - поиск функций и контента
    
    Использование:
    /поиск текст
    /поиск история
    """
    search_query = " ".join(context.args) if context.args else None
    
    if not search_query:
        await update.message.reply_text(
            "🔍 **Поиск**\n\n"
            "Использование: /поиск [запрос]\n\n"
            "Примеры:\n"
            "• /поиск текст - найти функции генерации текста\n"
            "• /поиск история - найти историю контента\n"
            "• /поиск план - найти функции планирования",
            parse_mode="Markdown"
        )
        return
    
    # Простой поиск по ключевым словам
    search_query_lower = search_query.lower()
    
    results = []
    
    # Поиск функций
    function_keywords = {
        "текст": ["📝 Генерация текста", "✏️ Редактор текста"],
        "изображение": ["🎨 Генерация изображения"],
        "план": ["📅 Контент-план", "📅 Календарь"],
        "история": ["📊 История"],
        "шаблон": ["📋 Шаблоны"],
        "статистика": ["📈 Статистика"],
        "аналитика": ["📈 Статистика", "📊 Анализ"],
        "настройки": ["⚙️ Настройки"],
        "команда": ["👥 Команда"],
        "тест": ["🔬 A/B тест"]
    }
    
    for keyword, functions in function_keywords.items():
        if keyword in search_query_lower:
            results.extend(functions)
    
    if results:
        # Убираем дубликаты
        results = list(set(results))
        
        from telegram import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        for func in results[:5]:  # Ограничиваем до 5 результатов
            # Создаем callback_data на основе функции
            callback_map = {
                "📝 Генерация текста": "menu_text_gen",
                "✏️ Редактор текста": "menu_text_editor",
                "🎨 Генерация изображения": "menu_image_gen",
                "📅 Контент-план": "menu_content_plan",
                "📅 Календарь": "menu_calendar",
                "📊 История": "menu_history",
                "📋 Шаблоны": "menu_templates",
                "📈 Статистика": "menu_statistics",
                "⚙️ Настройки": "menu_settings",
                "👥 Команда": "menu_team",
                "🔬 A/B тест": "menu_ab_test"
            }
            callback = callback_map.get(func, "main_menu")
            keyboard.append([InlineKeyboardButton(func, callback_data=callback)])
        
        keyboard.append([InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")])
        
        await update.message.reply_text(
            f"🔍 **Результаты поиска:** '{search_query}'\n\n"
            f"Найдено функций: {len(results)}\n\n"
            f"Выбери функцию:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ По запросу '{search_query}' ничего не найдено.\n\n"
            f"Попробуй другие ключевые слова:\n"
            f"• текст, изображение, план\n"
            f"• история, шаблоны, статистика\n"
            f"• настройки, команда, тест"
        )


def setup_quick_commands_handlers(application):
    """Настройка обработчиков команд быстрого доступа"""
    application.add_handler(CommandHandler("текст", quick_text_command))
    application.add_handler(CommandHandler("text", quick_text_command))  # Английская версия
    application.add_handler(CommandHandler("изображение", quick_image_command))
    application.add_handler(CommandHandler("image", quick_image_command))  # Английская версия
    application.add_handler(CommandHandler("план", quick_plan_command))
    application.add_handler(CommandHandler("plan", quick_plan_command))  # Английская версия
    application.add_handler(CommandHandler("статистика", quick_stats_command))
    application.add_handler(CommandHandler("stats", quick_stats_command))  # Английская версия
    application.add_handler(CommandHandler("поиск", search_command))
    application.add_handler(CommandHandler("search", search_command))  # Английская версия

