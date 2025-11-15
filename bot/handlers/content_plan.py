"""
Обработчики контент-плана
"""
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.inline import (
    get_content_plan_period_keyboard, get_yes_no_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard
from bot.services.ai.openrouter import openrouter_api
from bot.utils.helpers import get_or_create_user, calculate_content_plan_dates
from bot.utils.holidays import get_relevant_dates
from bot.utils.template_loader import get_content_plan_template_by_category
from bot.utils.export import export_plan_to_excel, export_to_ical, export_content_plan_to_csv
from bot.services.content.smart_planning import smart_planning_service
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bot.database.models import ContentPlan, ContentHistory, NKOProfile
from bot.database.database import get_db
from bot.states.conversation import END

logger = logging.getLogger(__name__)


# Состояния для контент-плана
WAITING_PERIOD, WAITING_FREQUENCY, WAITING_DAYS, WAITING_TIME, WAITING_TOPICS = range(5)


async def show_content_plan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню контент-плана"""
    text = (
        "📅 **Контент-план**\n\n"
        "Создам план публикаций на заданный период.\n\n"
        "Выбери период для контент-плана:"
    )
    
    context.user_data['content_plan'] = {}
    context.user_data['_conversation_active'] = True
    
    await update.message.reply_text(
        text,
        reply_markup=get_content_plan_period_keyboard(),
        parse_mode="Markdown"
    )
    
    return WAITING_PERIOD


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
    
    if callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    if callback_data in period_map:
        period_days = period_map[callback_data]
        context.user_data['content_plan']['period_days'] = period_days
        
        await query.edit_message_text(
            f"✅ Период выбран: {period_days} дней\n\n"
            "📊 Сколько раз в неделю ты хочешь публиковать посты?\n"
            "(Введи число от 1 до 7):"
        )
        
        return WAITING_FREQUENCY


async def handle_frequency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода частоты публикаций"""
    try:
        frequency = int(update.message.text.strip())
        
        if frequency < 1 or frequency > 7:
            await update.message.reply_text(
                "❌ Частота должна быть от 1 до 7 раз в неделю.\n"
                "Попробуй еще раз:"
            )
            return WAITING_FREQUENCY
        
        context.user_data['content_plan']['frequency'] = frequency
        
        text = (
            f"✅ Частота: {frequency} раз(а) в неделю\n\n"
            "📆 В какие дни недели публиковать?\n"
            "(Например: понедельник, среда, пятница или 1, 3, 5)\n\n"
            "Можешь написать названия дней или номера (1-понедельник, 7-воскресенье):"
        )
        
        await update.message.reply_text(text)
        return WAITING_DAYS
    
    except ValueError:
        await update.message.reply_text(
            "❌ Введи число от 1 до 7. Попробуй еще раз:"
        )
        return WAITING_FREQUENCY


async def handle_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода дней недели"""
    days_input = update.message.text.strip().lower()
    
    # Парсим дни недели
    day_names = {
        'понедельник': 1, 'пн': 1, '1': 1,
        'вторник': 2, 'вт': 2, '2': 2,
        'среда': 3, 'ср': 3, '3': 3,
        'четверг': 4, 'чт': 4, '4': 4,
        'пятница': 5, 'пт': 5, '5': 5,
        'суббота': 6, 'сб': 6, '6': 6,
        'воскресенье': 7, 'вс': 7, '7': 7
    }
    
    selected_days = []
    for word in days_input.replace(',', ' ').split():
        word = word.strip()
        if word in day_names:
            day_num = day_names[word]
            if day_num not in selected_days:
                selected_days.append(day_num)
    
    if not selected_days:
        await update.message.reply_text(
            "❌ Не удалось распознать дни недели.\n"
            "Напиши, например: понедельник, среда, пятница\n"
            "Или: 1, 3, 5\n"
            "Попробуй еще раз:"
        )
        return WAITING_DAYS
    
    # Сортируем дни
    selected_days.sort()
    context.user_data['content_plan']['days'] = selected_days
    
    days_names_list = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
    days_str = ', '.join([days_names_list[d-1] for d in selected_days])
    
    text = (
        f"✅ Дни недели: {days_str}\n\n"
        "⏰ Во сколько публиковать посты?\n"
        "(Например: утро, день, вечер или 10:00, 14:00, 18:00)\n\n"
        "Можешь указать время словами или конкретное время:"
    )
    
    await update.message.reply_text(text)
    return WAITING_TIME


async def handle_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода времени публикаций"""
    time_input = update.message.text.strip().lower()
    
    # Сохраняем время как строку, можно расширить парсинг
    context.user_data['content_plan']['time'] = time_input
    
    text = (
        f"✅ Время публикаций: {time_input}\n\n"
        "📝 Какие тематики постов ты хочешь видеть в плане?\n"
        "(Например: благодарности, отчеты, анонсы, образовательный контент)\n\n"
        "Опиши несколько тем или просто напиши 'любые':"
    )
    
    await update.message.reply_text(text)
    return WAITING_TOPICS


async def handle_topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка ввода тематик и генерация контент-плана"""
    topics = update.message.text.strip()
    context.user_data['content_plan']['topics'] = topics
    
    # Получаем данные плана
    plan_data = context.user_data.get('content_plan', {})
    period_days = plan_data.get('period_days', 7)
    frequency = plan_data.get('frequency', 3)
    days = plan_data.get('days', [1, 3, 5])
    time_str = plan_data.get('time', 'утро')
    
    # Вычисляем даты
    start_date, end_date, schedule_dates = calculate_content_plan_dates(
        period_days, frequency, days
    )
    
    # Анализируем лучшее время для публикаций
    time_analysis = await smart_planning_service.analyze_best_posting_times(user_id)
    if time_analysis.get("success") and time_analysis.get("recommended_times"):
        recommended_time = time_analysis["recommended_times"][0]
        if not time_str or time_str.lower() in ["утро", "день", "вечер"]:
            time_str = recommended_time
    
    # Отправляем сообщение о генерации
    processing_msg = await update.message.reply_text("⏳ Генерирую контент-план...")
    
    try:
        # Получаем профиль НКО, если есть
        user_id = update.effective_user.id
        get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
        
        nko_info = ""
        with get_db() as db:
            from bot.database.models import NKOProfile
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_info = f"\nОрганизация: {profile.organization_name or 'не указано'}\n"
                if profile.description:
                    nko_info += f"Деятельность: {profile.description[:200]}\n"
        
        # Получаем релевантные праздничные даты
        holidays_info = ""
        activity_types = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile and profile.activity_types:
                activity_types = profile.activity_types
        
        relevant_holidays = get_relevant_dates(start_date, end_date, activity_types)
        if relevant_holidays:
            holidays_info = "\n\n📅 Важные даты в этом периоде:\n"
            for holiday in relevant_holidays[:5]:  # Ограничиваем до 5 праздников
                holidays_info += f"- {holiday['date'].strftime('%d.%m.%Y')}: {holiday['name']}\n"
        
        # Формируем промпт для генерации плана
        days_names_list = ['понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье']
        days_str = ', '.join([days_names_list[d-1] for d in days])
        
        prompt = f"""Создай контент-план для некоммерческой организации на {period_days} дней.
{holidays_info}

Параметры:
- Период: {period_days} дней (с {start_date.strftime('%d.%m.%Y')} по {end_date.strftime('%d.%m.%Y')})
- Частота: {frequency} публикаций в неделю
- Дни публикаций: {days_str}
- Время публикаций: {time_str}
- Тематики: {topics}
{nko_info}

Создай детальный контент-план с конкретными идеями для постов на каждый день из расписания.

Формат ответа:
ДАТА (День недели)
📌 Категория: [тип поста]
💡 Идея: [краткое описание темы поста]
📝 Примерное содержание: [1-2 предложения]

Разделяй дни пустой строкой. Будь конкретным и релевантным для НКО."""

        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию контент-планов для некоммерческих организаций. Создавай релевантные, интересные и полезные идеи для постов.",
            temperature=0.7,
            max_tokens=2000
        )
        
        if result and result.get("success"):
            plan_content = result.get("content", "")
            
            # Сохраняем план в БД
            with get_db() as db:
                content_plan = ContentPlan(
                    user_id=user_id,
                    plan_name=f"План на {period_days} дней",
                    start_date=start_date,
                    end_date=end_date,
                    frequency=frequency,
                    schedule={
                        "days": days,
                        "time": time_str,
                        "dates": [d.isoformat() for d in schedule_dates],
                        "topics": topics,
                        "content": plan_content
                    },
                    is_active=True
                )
                db.add(content_plan)
                db.commit()
                
                # Сохраняем в историю
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="plan",
                    content_data={
                        "plan_id": content_plan.id,
                        "period_days": period_days,
                        "frequency": frequency,
                        "topics": topics
                    }
                )
                db.add(history_entry)
                db.commit()
            
            # Форматируем ответ
            response_text = (
                f"✅ **Контент-план создан!**\n\n"
                f"📅 Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}\n"
                f"📊 Частота: {frequency} раз(а) в неделю\n"
                f"📆 Дни: {days_str}\n"
                f"⏰ Время: {time_str}\n\n"
                f"📝 **Идеи для постов:**\n\n"
                f"{plan_content[:3000]}"  # Ограничиваем длину для Telegram
            )
            
            if len(plan_content) > 3000:
                response_text += "\n\n... (план обрезан, полная версия сохранена)"
            
            # Кнопки экспорта и дополнительных функций
            export_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📊 CSV", callback_data=f"export_plan_csv_{content_plan.id}"),
                    InlineKeyboardButton("📈 Excel", callback_data=f"export_plan_excel_{content_plan.id}")
                ],
                [
                    InlineKeyboardButton("📅 iCal", callback_data=f"export_plan_ical_{content_plan.id}")
                ],
                [
                    InlineKeyboardButton("🤖 Автогенерация постов", callback_data=f"plan_auto_generate_{content_plan.id}"),
                    InlineKeyboardButton("📊 Анализ эффективности", callback_data=f"plan_analyze_{content_plan.id}")
                ]
            ])
            
            await processing_msg.edit_text(
                response_text,
                reply_markup=export_keyboard,
                parse_mode="Markdown"
            )
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации контент-плана. Попробуй еще раз."
            )
    
    except Exception as e:
        logger.exception(f"Ошибка при создании контент-плана: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при создании контент-плана. Попробуй еще раз."
        )
    
    # Очищаем данные
    context.user_data.pop('content_plan', None)
    context.user_data.pop('_conversation_active', None)
    
    return END


async def cancel_content_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена создания контент-плана"""
    context.user_data.pop('content_plan', None)
    context.user_data.pop('_conversation_active', None)
    await update.message.reply_text(
        "❌ Создание контент-плана отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    return END


async def handle_plan_export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка экспорта контент-плана и дополнительных функций"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    
    # Обработка автогенерации
    if callback_data.startswith("plan_auto_generate_"):
        plan_id = int(callback_data.replace("plan_auto_generate_", ""))
        await query.edit_message_text("⏳ Автоматически генерирую посты для всех дат в плане...\n\nЭто может занять некоторое время.")
        
        # Получаем профиль НКО
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = {
                    "organization_name": profile.organization_name,
                    "description": profile.description
                }
        
        result = await smart_planning_service.auto_generate_plan_content(plan_id, user_id, nko_profile)
        
        if result.get("success"):
            generated_count = result.get("generated_count", 0)
            total_count = result.get("total_count", 0)
            await query.edit_message_text(
                f"✅ Автогенерация завершена!\n\n"
                f"Сгенерировано постов: {generated_count} из {total_count}\n\n"
                f"Все посты сохранены в истории контента."
            )
        else:
            await query.edit_message_text(
                f"❌ Ошибка при автогенерации: {result.get('error', 'Неизвестная ошибка')}"
            )
        return
    
    # Обработка анализа эффективности
    if callback_data.startswith("plan_analyze_"):
        plan_id = int(callback_data.replace("plan_analyze_", ""))
        await query.edit_message_text("⏳ Анализирую эффективность плана...")
        
        analysis = await smart_planning_service.analyze_plan_effectiveness(plan_id, user_id)
        
        if analysis.get("success"):
            text = (
                f"📊 **Анализ эффективности плана**\n\n"
                f"**Выполнение:**\n"
                f"• Всего постов: {analysis['total_posts']}\n"
                f"• Выполнено: {analysis['completed_posts']}\n"
                f"• Осталось: {analysis['remaining_posts']}\n"
                f"• Процент выполнения: {analysis['completion_percentage']}%\n\n"
            )
            
            if analysis.get("content_diversity"):
                diversity = analysis["content_diversity"]
                text += f"**Разнообразие контента:**\n"
                text += f"• Типов контента: {diversity['types_count']}\n"
                if diversity.get("types_distribution"):
                    text += "• Распределение:\n"
                    for ctype, count in diversity["types_distribution"].items():
                        text += f"  - {ctype}: {count}\n"
                text += "\n"
            
            if analysis.get("recommendations"):
                text += "**Рекомендации:**\n"
                for rec in analysis["recommendations"]:
                    text += f"{rec}\n"
            
            await query.edit_message_text(text, parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"❌ Ошибка при анализе: {analysis.get('error', 'Неизвестная ошибка')}"
            )
        return
    
    # Парсим callback_data: export_plan_csv_123, export_plan_excel_123, export_plan_ical_123
    if callback_data.startswith("export_plan_csv_"):
        plan_id = int(callback_data.replace("export_plan_csv_", ""))
        await query.edit_message_text("⏳ Экспортирую контент-план в CSV...")
        
        file_path = await export_content_plan_to_csv(user_id, plan_id)
        
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption="✅ Контент-план экспортирован в CSV файл"
                )
            await query.edit_message_text("✅ Экспорт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при экспорте. Попробуй еще раз.")
    
    elif callback_data.startswith("export_plan_excel_"):
        plan_id = int(callback_data.replace("export_plan_excel_", ""))
        await query.edit_message_text("⏳ Экспортирую контент-план в Excel...")
        
        file_path = await export_plan_to_excel(user_id, plan_id)
        
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption="✅ Контент-план экспортирован в Excel файл"
                )
            await query.edit_message_text("✅ Экспорт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при экспорте или библиотека openpyxl не установлена.")
    
    elif callback_data.startswith("export_plan_ical_"):
        plan_id = int(callback_data.replace("export_plan_ical_", ""))
        await query.edit_message_text("⏳ Экспортирую контент-план в iCal...")
        
        file_path = await export_to_ical(user_id, plan_id)
        
        if file_path and file_path.exists():
            with open(file_path, 'rb') as f:
                await query.message.reply_document(
                    document=f,
                    filename=file_path.name,
                    caption="✅ Контент-план экспортирован в iCal файл"
                )
            await query.edit_message_text("✅ Экспорт завершен!")
        else:
            await query.edit_message_text("❌ Ошибка при экспорте или библиотека icalendar не установлена.")


def setup_content_plan_handlers(application):
    """Настройка обработчиков контент-плана"""
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📅 Контент-план$"), show_content_plan_menu),
        ],
        states={
            WAITING_PERIOD: [
                CallbackQueryHandler(content_plan_period_callback, pattern="^plan_period_|^main_menu")
            ],
            WAITING_FREQUENCY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_frequency)
            ],
            WAITING_DAYS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_days)
            ],
            WAITING_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_time)
            ],
            WAITING_TOPICS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topics)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), cancel_content_plan),
            MessageHandler(filters.Regex("^◀️ Назад$"), cancel_content_plan),
            CallbackQueryHandler(lambda u, c: END, pattern="^main_menu")
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Обработчик экспорта контент-плана
    from telegram.ext import CallbackQueryHandler
    application.add_handler(
        CallbackQueryHandler(handle_plan_export_callback, pattern="^export_plan_")
    )


async def auto_generate_plan_texts(plan_id: int, user_id: int) -> Dict[str, Any]:
    """
    Автоматически генерирует тексты для всех постов в контент-плане
    
    Args:
        plan_id: ID контент-плана
        user_id: ID пользователя
    
    Returns:
        Dict с результатами генерации
    """
    try:
        with get_db() as db:
            plan = db.query(ContentPlan).filter(
                ContentPlan.id == plan_id,
                ContentPlan.user_id == user_id
            ).first()
            
            if not plan:
                return {"success": False, "error": "План не найден"}
            
            schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
            dates = schedule.get("dates", [])
            topics = schedule.get("topics", [])
            
            # Получаем профиль НКО
            nko_profile = None
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        generated_texts = []
        
        # Генерируем тексты для каждой даты
        for i, date_str in enumerate(dates, 1):
            try:
                from datetime import datetime
                post_date = datetime.fromisoformat(date_str).date() if isinstance(date_str, str) else date_str
                
                # Тема поста
                topic = topics[i % len(topics)] if topics else "Пост для НКО"
                
                # Формируем промпт для генерации
                nko_info = ""
                if nko_profile:
                    if nko_profile.organization_name:
                        nko_info += f"Организация: {nko_profile.organization_name}. "
                    if nko_profile.description:
                        nko_info += f"Деятельность: {nko_profile.description[:200]}. "
                
                prompt = f"""Создай пост для некоммерческой организации на тему: {topic}
                
{nko_info}

Требования:
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна тема
- Естественные переходы
- Уместные эмоции
- Простота языка

Создай готовый пост с хештегами."""
                
                result = await openrouter_api.generate_text(
                    prompt=prompt,
                    system_prompt="Ты эксперт по созданию контента для некоммерческих организаций.",
                    temperature=0.8,
                    max_tokens=300
                )
                
                if result and result.get("success"):
                    text = result.get("content", "")
                    generated_texts.append({
                        "date": post_date.isoformat(),
                        "topic": topic,
                        "text": text
                    })
                
                # Небольшая задержка между генерациями
                import asyncio
                await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Ошибка при генерации текста для даты {date_str}: {e}")
                continue
        
        return {
            "success": True,
            "generated_count": len(generated_texts),
            "texts": generated_texts
        }
    
    except Exception as e:
        logger.exception(f"Ошибка при автоматической генерации текстов: {e}")
        return {"success": False, "error": str(e)}


def get_plan_statistics(plan_id: int, user_id: int) -> Dict[str, Any]:
    """
    Получает статистику выполнения контент-плана
    
    Args:
        plan_id: ID контент-плана
        user_id: ID пользователя
    
    Returns:
        Dict со статистикой
    """
    try:
        with get_db() as db:
            plan = db.query(ContentPlan).filter(
                ContentPlan.id == plan_id,
                ContentPlan.user_id == user_id
            ).first()
            
            if not plan:
                return {"success": False, "error": "План не найден"}
            
            schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
            dates = schedule.get("dates", [])
            
            # Подсчитываем выполненные посты (посты в истории с датами из плана)
            from datetime import datetime, timedelta
            completed_count = 0
            if dates:
                plan_start = plan.start_date
                plan_end = plan.end_date
                
                completed = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.content_type == "text",
                    ContentHistory.generated_at >= datetime.combine(plan_start, datetime.min.time()),
                    ContentHistory.generated_at <= datetime.combine(plan_end, datetime.min.time()) + timedelta(days=1)
                ).count()
                
                completed_count = completed
            
            total_posts = len(dates) if dates else 0
            completion_percentage = (completed_count / total_posts * 100) if total_posts > 0 else 0
            
            return {
                "success": True,
                "plan_id": plan_id,
                "total_posts": total_posts,
                "completed_posts": completed_count,
                "remaining_posts": total_posts - completed_count,
                "completion_percentage": round(completion_percentage, 1)
            }
    
    except Exception as e:
        logger.exception(f"Ошибка при получении статистики плана: {e}")
        return {"success": False, "error": str(e)}


def balance_content_types(content_types: List[str], count: int) -> List[str]:
    """
    Балансирует типы контента для равномерного распределения
    
    Args:
        content_types: Список типов контента
        count: Количество постов
    
    Returns:
        Сбалансированный список типов контента
    """
    if not content_types:
        return []
    
    balanced = []
    types_count = len(content_types)
    
    # Равномерно распределяем типы
    for i in range(count):
        balanced.append(content_types[i % types_count])
    
    return balanced
