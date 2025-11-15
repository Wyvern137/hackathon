"""
Обработчики календаря событий
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentPlan, NKOProfile
from bot.database.database import get_db
from bot.services.ai.openrouter import openrouter_api
from bot.states.conversation import END

logger = logging.getLogger(__name__)


WAITING_EVENT_NAME, WAITING_EVENT_DATE, WAITING_EVENT_DESCRIPTION = range(3)


async def show_calendar_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню календаря событий"""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    # Проверяем активные планы и предстоящие даты
    with get_db() as db:
        active_plans = db.query(ContentPlan).filter(
            ContentPlan.user_id == user_id,
            ContentPlan.is_active == True
        ).all()
    
    upcoming_events = []
    today = datetime.now().date()
    
    for plan in active_plans:
        schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
        dates = schedule.get("dates", [])
        
        for date_str in dates:
            try:
                event_date = datetime.fromisoformat(date_str).date()
                if event_date >= today:
                    upcoming_events.append({
                        "date": event_date,
                        "plan": plan
                    })
            except:
                pass
    
    # Сортируем по дате
    upcoming_events.sort(key=lambda x: x["date"])
    upcoming_events = upcoming_events[:10]  # Берем ближайшие 10
    
    text = "📅 **Календарь событий**\n\n"
    
    if upcoming_events:
        text += "**Ближайшие публикации:**\n\n"
        for event in upcoming_events:
            date_str = event["date"].strftime("%d.%m.%Y (%A)")
            plan_name = event["plan"].plan_name
            days_left = (event["date"] - today).days
            
            if days_left == 0:
                text += f"📌 **Сегодня** - {plan_name}\n"
            elif days_left == 1:
                text += f"📌 **Завтра** - {plan_name}\n"
            else:
                text += f"📌 {date_str} ({days_left} дней) - {plan_name}\n"
        
        text += "\n"
    else:
        text += "Нет запланированных публикаций.\n\n"
    
    text += "**Доступные действия:**\n"
    text += "• Создать событие - добавить новое событие в календарь\n"
    text += "• Сгенерировать анонс - создать анонс для предстоящего события"
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Создать событие", callback_data="calendar_create_event"),
            InlineKeyboardButton("📢 Сгенерировать анонс", callback_data="calendar_generate_announcement")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
        ]
    ])
    
    # Исправление: проверяем, является ли update сообщением или callback
    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    elif update.callback_query:
        # Это callback, редактируем сообщение
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def calendar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback календаря"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "calendar_create_event":
        context.user_data['calendar_event'] = {}
        context.user_data['_conversation_active'] = True
        
        await query.edit_message_text(
            "➕ **Создание события**\n\n"
            "Введи название события:",
            parse_mode="Markdown"
        )
        
        return WAITING_EVENT_NAME
    
    elif callback_data == "calendar_generate_announcement":
        # Получаем ближайшее событие из планов
        user_id = update.effective_user.id
        
        with get_db() as db:
            active_plans = db.query(ContentPlan).filter(
                ContentPlan.user_id == user_id,
                ContentPlan.is_active == True
            ).all()
        
        upcoming_events = []
        today = datetime.now().date()
        
        for plan in active_plans:
            schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
            dates = schedule.get("dates", [])
            
            for date_str in dates:
                try:
                    event_date = datetime.fromisoformat(date_str).date()
                    if event_date >= today:
                        upcoming_events.append({
                            "date": event_date,
                            "plan": plan
                        })
                except:
                    pass
        
        if not upcoming_events:
            await query.edit_message_text(
                "❌ Нет предстоящих событий для анонса.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Назад", callback_data="calendar_back")]
                ])
            )
            return END
        
        # Берем ближайшее событие
        upcoming_events.sort(key=lambda x: x["date"])
        nearest_event = upcoming_events[0]
        
        # Генерируем анонс
        await generate_event_announcement(update, context, nearest_event)
        return END
    
    elif callback_data == "calendar_back":
        await show_calendar_menu(update, context)
        return END
    
    elif callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    return END


async def handle_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия события"""
    event_name = update.message.text.strip()
    
    if not event_name or len(event_name) < 3:
        await update.message.reply_text(
            "❌ Название слишком короткое. Напиши хотя бы 3 символа:"
        )
        return WAITING_EVENT_NAME
    
    context.user_data['calendar_event']['name'] = event_name
    
    await update.message.reply_text(
        f"✅ Название: {event_name}\n\n"
        "📅 Введи дату события (например: 25.12.2024 или 2024-12-25):"
    )
    
    return WAITING_EVENT_DATE


async def handle_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка даты события"""
    date_str = update.message.text.strip()
    
    # Парсим дату
    event_date = None
    for fmt in ["%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            event_date = datetime.strptime(date_str, fmt).date()
            break
        except:
            continue
    
    if not event_date:
        await update.message.reply_text(
            "❌ Неверный формат даты. Используй формат: 25.12.2024"
        )
        return WAITING_EVENT_DATE
    
    context.user_data['calendar_event']['date'] = event_date.isoformat()
    
    await update.message.reply_text(
        f"✅ Дата: {event_date.strftime('%d.%m.%Y')}\n\n"
        "📝 Введи описание события (опционально, можно написать 'пропустить'):"
    )
    
    return WAITING_EVENT_DESCRIPTION


async def handle_event_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания события"""
    description = update.message.text.strip()
    
    if description.lower() not in ['пропустить', 'skip', 'пропустить']:
        context.user_data['calendar_event']['description'] = description
    else:
        context.user_data['calendar_event']['description'] = None
    
    # Сохраняем событие в ближайший активный план или создаем заметку
    user_id = update.effective_user.id
    event_data = context.user_data.get('calendar_event', {})
    
    # Добавляем событие в ближайший активный план или создаем запись
    with get_db() as db:
        # Ищем активный план, который охватывает эту дату
        plans = db.query(ContentPlan).filter(
            ContentPlan.user_id == user_id,
            ContentPlan.is_active == True
        ).all()
        
        event_date = datetime.fromisoformat(event_data['date']).date()
        
        # Обновляем schedule с событием
        for plan in plans:
            if plan.start_date <= event_date <= plan.end_date:
                schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
                events = schedule.get("events", [])
                
                events.append({
                    "name": event_data['name'],
                    "date": event_data['date'],
                    "description": event_data.get('description')
                })
                
                schedule["events"] = events
                plan.schedule = schedule
                db.commit()
                break
    
    await update.message.reply_text(
        f"✅ Событие '{event_data['name']}' добавлено в календарь!\n\n"
        f"Дата: {event_date.strftime('%d.%m.%Y')}"
    )
    
    context.user_data.pop('calendar_event', None)
    context.user_data.pop('_conversation_active', None)
    
    return END


async def generate_event_announcement(update: Update, context: ContextTypes.DEFAULT_TYPE, event: dict):
    """Генерирует анонс для события"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    if query:
        await query.edit_message_text("⏳ Генерирую анонс события...")
    
    try:
        user_id = update.effective_user.id
        plan = event["plan"]
        event_date = event["date"]
        
        # Получаем профиль НКО
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        nko_info = ""
        if nko_profile:
            if nko_profile.organization_name:
                nko_info += f"\nНКО: {nko_profile.organization_name}\n"
            if nko_profile.description:
                nko_info += f"Деятельность: {nko_profile.description}\n"
        
        days_left = (event_date - datetime.now().date()).days
        
        prompt = f"""Создай анонс для предстоящего события.

Событие: {plan.plan_name}
Дата: {event_date.strftime('%d.%m.%Y')}
Осталось дней: {days_left}
{nko_info}

Создай привлекательный анонс, который заинтересует аудиторию. 
Включи призыв к участию или вниманию."""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию анонсов для некоммерческих организаций.",
            temperature=0.8,
            max_tokens=300
        )
        
        if result and result.get("success"):
            announcement = result.get("content", "")
            
            if query:
                await query.edit_message_text(
                    f"✅ **Анонс готов!**\n\n{announcement}",
                    parse_mode="Markdown"
                )
            else:
                await update.message.reply_text(
                    f"✅ **Анонс готов!**\n\n{announcement}",
                    parse_mode="Markdown"
                )
        else:
            error_msg = "❌ Ошибка при генерации анонса."
            if query:
                await query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации анонса: {e}")
        error_msg = "❌ Произошла ошибка при генерации анонса."
        if query:
            await query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


def setup_calendar_handlers(application):
    """Настройка обработчиков календаря"""
    from telegram.ext import CallbackQueryHandler
    
    # ConversationHandler для создания события
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(calendar_callback, pattern="^calendar_create_event$"),
        ],
        states={
            WAITING_EVENT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_name)
            ],
            WAITING_EVENT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_date)
            ],
            WAITING_EVENT_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_description)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Обработчик callback для календаря
    application.add_handler(
        CallbackQueryHandler(calendar_callback, pattern="^calendar_")
    )

