"""
Обработчик настройки профиля НКО
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.database.models import NKOProfile, ActivityType
from bot.database.database import get_db
from bot.keyboards.main_menu import get_main_menu_keyboard, get_skip_keyboard
from bot.keyboards.inline import get_activity_types_keyboard
from bot.states.conversation import NKO_SETUP, END
from bot.utils.validators import validators
from bot.utils.helpers import get_or_create_user

logger = logging.getLogger(__name__)


async def nko_setup_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало процесса настройки профиля НКО"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    # Проверяем, есть ли уже профиль
    with get_db() as db:
        existing_profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
        if existing_profile:
            await query.edit_message_text(
                "У тебя уже есть профиль НКО. Хочешь обновить его?",
                reply_markup=None
            )
            context.user_data['nko_setup'] = {'update_existing': True, 'profile_id': existing_profile.id}
    
    await query.edit_message_text(
        "Отлично! Давай настроим профиль твоей НКО.\n\n"
        "Шаг 1/7: Как называется твоя организация?\n\n"
        "Введи название или нажми 'Пропустить'."
    )
    
    return NKO_SETUP["org_name"]


async def nko_setup_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пропустить настройку профиля НКО"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Хорошо, ты можешь создать профиль позже в настройках.",
        reply_markup=None
    )
    
    return END


async def nko_setup_org_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия организации"""
    text = update.message.text.strip()
    
    if text == "⏭️ Пропустить":
        context.user_data.setdefault('nko_setup', {})['org_name'] = None
        await update.message.reply_text(
            "Шаг 2/7: Расскажи о деятельности организации.\n\n"
            "Опиши, чем занимается твоя НКО (или нажми 'Пропустить')."
        )
        return NKO_SETUP["description"]
    
    # Валидация
    is_valid, error = validators.validate_organization_name(text)
    if not is_valid:
        await update.message.reply_text(f"❌ {error}\n\nПопробуй еще раз:")
        return NKO_SETUP["org_name"]
    
    context.user_data.setdefault('nko_setup', {})['org_name'] = text
    
    await update.message.reply_text(
        f"✅ Название сохранено: {text}\n\n"
        "Шаг 2/7: Расскажи о деятельности организации.\n\n"
        "Опиши, чем занимается твоя НКО (или нажми 'Пропустить')."
    )
    return NKO_SETUP["description"]


async def nko_setup_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания деятельности"""
    text = update.message.text.strip()
    
    if text == "⏭️ Пропустить":
        context.user_data['nko_setup']['description'] = None
    else:
        is_valid, error = validators.validate_text(text, min_length=10, max_length=2000)
        if not is_valid:
            await update.message.reply_text(f"❌ {error}\n\nПопробуй еще раз:")
            return NKO_SETUP["description"]
        
        context.user_data['nko_setup']['description'] = text
    
    await update.message.reply_text(
        "Шаг 3/7: Выбери типы деятельности твоей НКО.\n\n"
        "Можно выбрать несколько вариантов:",
        reply_markup=get_activity_types_keyboard([])
    )
    return NKO_SETUP["activity_types"]


async def nko_setup_activity_types_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типов деятельности"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "activity_types_done":
        selected = context.user_data.get('nko_setup', {}).get('activity_types', [])
        if not selected:
            await query.edit_message_text(
                "❌ Выбери хотя бы один тип деятельности:",
                reply_markup=get_activity_types_keyboard([])
            )
            return NKO_SETUP["activity_types"]
        
        await query.edit_message_text(
            f"✅ Выбрано типов деятельности: {len(selected)}\n\n"
            "Шаг 4/7: Кто твоя целевая аудитория?\n\n"
            "Опиши, для кого предназначены твои посты (например: 'родители с детьми', 'волонтеры', 'люди, интересующиеся экологией').",
            reply_markup=get_skip_keyboard()
        )
        return NKO_SETUP["target_audience"]
    
    elif callback_data.startswith("toggle_"):
        activity_type = callback_data.replace("toggle_activity_", "")
        selected = context.user_data.setdefault('nko_setup', {}).setdefault('activity_types', [])
        
        if activity_type in selected:
            selected.remove(activity_type)
        else:
            selected.append(activity_type)
        
        # Обновляем клавиатуру
        await query.edit_message_reply_markup(
            reply_markup=get_activity_types_keyboard(selected)
        )
        return NKO_SETUP["activity_types"]
    
    return NKO_SETUP["activity_types"]


async def nko_setup_target_audience(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка целевой аудитории"""
    text = update.message.text.strip()
    
    if text == "⏭️ Пропустить":
        context.user_data['nko_setup']['target_audience'] = None
    else:
        is_valid, error = validators.validate_text(text, min_length=5, max_length=500)
        if not is_valid:
            await update.message.reply_text(f"❌ {error}\n\nПопробуй еще раз:")
            return NKO_SETUP["target_audience"]
        
        context.user_data['nko_setup']['target_audience'] = text
    
    from bot.keyboards.inline import get_style_keyboard
    await update.message.reply_text(
        "Шаг 5/7: Выбери стиль повествования для постов:\n\n"
        "Как ты хочешь, чтобы звучали твои посты?",
        reply_markup=get_style_keyboard()
    )
    return NKO_SETUP["tone_of_voice"]


async def nko_setup_tone_of_voice_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора стиля повествования"""
    query = update.callback_query
    await query.answer()
    
    style_map = {
        "style_conversational": "conversational",
        "style_formal": "formal",
        "style_artistic": "artistic",
        "style_neutral": "neutral",
        "style_friendly": "friendly"
    }
    
    callback_data = query.data
    if callback_data in style_map:
        tone = style_map[callback_data]
        context.user_data.setdefault('nko_setup', {})['tone_of_voice'] = tone
        
        tone_names = {
            "conversational": "Разговорный",
            "formal": "Официальный",
            "artistic": "Художественный",
            "neutral": "Нейтральный",
            "friendly": "Дружелюбный"
        }
        
        await query.edit_message_text(
            f"✅ Стиль сохранен: {tone_names.get(tone, tone)}\n\n"
            "Шаг 6/7: Контактная информация (необязательно).\n\n"
            "Введи контакты организации (email, телефон, сайт) или нажми 'Пропустить'.",
            reply_markup=get_skip_keyboard()
        )
        return NKO_SETUP["contact_info"]
    
    return NKO_SETUP["tone_of_voice"]


async def nko_setup_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка контактной информации"""
    text = update.message.text.strip()
    
    if text == "⏭️ Пропустить":
        context.user_data['nko_setup']['contact_info'] = None
    else:
        # Парсим контакты (упрощенная версия)
        contact_info = {"text": text}
        # Можно добавить более сложный парсинг email, телефона, URL
        
        context.user_data['nko_setup']['contact_info'] = contact_info
    
    await update.message.reply_text(
        "Шаг 7/7: Брендинг (необязательно).\n\n"
        "Укажи цвета бренда для генерации изображений (например: '#FF5733, #33C3F0') или нажми 'Пропустить'.",
        reply_markup=get_skip_keyboard()
    )
    return NKO_SETUP["brand_colors"]


async def nko_setup_brand_colors(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка цветов бренда"""
    text = update.message.text.strip()
    
    if text == "⏭️ Пропустить":
        context.user_data['nko_setup']['brand_colors'] = None
    else:
        # Парсим цвета
        colors = [c.strip() for c in text.split(',') if c.strip().startswith('#')]
        context.user_data['nko_setup']['brand_colors'] = colors if colors else None
    
    # Сохраняем профиль в БД
    user_id = update.effective_user.id
    setup_data = context.user_data.get('nko_setup', {})
    
    with get_db() as db:
        db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
        
        # Проверяем, есть ли уже профиль
        existing_profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
        
        if existing_profile and setup_data.get('update_existing'):
            # Обновляем существующий профиль
            profile = existing_profile
        else:
            profile = NKOProfile(user_id=user_id)
            db.add(profile)
        
        # Заполняем данные
        profile.organization_name = setup_data.get('org_name')
        profile.description = setup_data.get('description')
        profile.activity_types = setup_data.get('activity_types', [])
        profile.target_audience = setup_data.get('target_audience')
        profile.tone_of_voice = setup_data.get('tone_of_voice')
        profile.contact_info = setup_data.get('contact_info')
        profile.brand_colors = setup_data.get('brand_colors')
        profile.is_complete = True
        
        db.commit()
    
    # Очищаем данные контекста
    context.user_data.pop('nko_setup', None)
    
    org_name = setup_data.get('org_name', 'НКО')
    await update.message.reply_text(
        f"✅ Профиль НКО '{org_name}' успешно создан!\n\n"
        "Теперь я смогу генерировать более релевантный контент для твоей организации.",
        reply_markup=get_main_menu_keyboard()
    )
    
    return END


def setup_nko_handlers(application):
    """Настройка обработчиков для настройки профиля НКО"""
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(nko_setup_start_callback, pattern="^nko_setup_start$"),
        ],
        states={
            NKO_SETUP["org_name"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nko_setup_org_name)
            ],
            NKO_SETUP["description"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nko_setup_description)
            ],
            NKO_SETUP["activity_types"]: [
                CallbackQueryHandler(nko_setup_activity_types_callback, pattern="^(toggle_activity_|activity_types_)")
            ],
            NKO_SETUP["target_audience"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nko_setup_target_audience)
            ],
            NKO_SETUP["tone_of_voice"]: [
                CallbackQueryHandler(nko_setup_tone_of_voice_callback, pattern="^style_")
            ],
            NKO_SETUP["contact_info"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nko_setup_contact_info)
            ],
            NKO_SETUP["brand_colors"]: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, nko_setup_brand_colors)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(nko_setup_skip_callback, pattern="^nko_setup_skip$"),
            MessageHandler(filters.Regex("^❌ Отмена$"), nko_setup_skip_callback),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(nko_setup_start_callback, pattern="^nko_setup_start$"))
    application.add_handler(CallbackQueryHandler(nko_setup_skip_callback, pattern="^nko_setup_skip$"))

