"""
Обработчики шаблонов постов
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.helpers import get_or_create_user
from bot.database.models import PostTemplate, ContentHistory
from bot.database.database import get_db
from bot.services.ai.openrouter import openrouter_api
from bot.services.content.hashtag_generator import hashtag_generator
from bot.services.content.text_processor import text_processor
from bot.states.conversation import END

logger = logging.getLogger(__name__)


# Предустановленные шаблоны
PREDEFINED_TEMPLATES = {
    "thanks_volunteers": {
        "name": "Благодарность волонтерам",
        "category": "благодарность",
        "prompt": "Создай пост с благодарностью волонтерам за их помощь и поддержку. Пост должен быть теплым и искренним."
    },
    "event_announcement": {
        "name": "Анонс мероприятия",
        "category": "анонс",
        "prompt": "Создай анонс мероприятия. Включи призыв к участию, важную информацию о событии."
    },
    "event_report": {
        "name": "Отчет о мероприятии",
        "category": "отчет",
        "prompt": "Создай отчет о прошедшем мероприятии. Опиши что происходило, кто участвовал, какие были результаты."
    },
    "call_for_help": {
        "name": "Призыв к помощи",
        "category": "призыв",
        "prompt": "Создай призыв к помощи. Объясни ситуацию и как люди могут помочь. Будь конкретным и убедительным."
    },
    "holiday_congratulation": {
        "name": "Поздравление с праздником",
        "category": "поздравление",
        "prompt": "Создай поздравление с праздником. Пост должен быть теплым, праздничным и связанным с деятельностью НКО."
    },
    "educational_post": {
        "name": "Образовательный пост",
        "category": "образование",
        "prompt": "Создай образовательный пост. Поделись полезной информацией, связанной с деятельностью НКО."
    }
}


def get_templates_keyboard(templates, user_templates=None):
    """Клавиатура выбора шаблона"""
    if user_templates is None:
        user_templates = []
    
    keyboard = []
    
    # Предустановленные шаблоны
    keyboard.append([InlineKeyboardButton("📋 Предустановленные шаблоны", callback_data="templates_predefined")])
    
    # Пользовательские шаблоны
    if user_templates:
        keyboard.append([InlineKeyboardButton("⭐ Мои шаблоны", callback_data="templates_user")])
    
    # Создать новый шаблон
    keyboard.append([InlineKeyboardButton("➕ Создать шаблон", callback_data="template_create")])
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)


def get_predefined_templates_keyboard():
    """Клавиатура предустановленных шаблонов"""
    keyboard = []
    
    for key, template in PREDEFINED_TEMPLATES.items():
        keyboard.append([
            InlineKeyboardButton(template["name"], callback_data=f"template_use_{key}")
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="templates_back")])
    
    return InlineKeyboardMarkup(keyboard)


def get_user_templates_keyboard(templates):
    """Клавиатура пользовательских шаблонов"""
    keyboard = []
    
    for template in templates:
        keyboard.append([
            InlineKeyboardButton(
                f"⭐ {template.template_name} ({template.usage_count} раз)",
                callback_data=f"template_use_user_{template.id}"
            )
        ])
    
    keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="templates_back")])
    
    return InlineKeyboardMarkup(keyboard)


async def show_templates_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню шаблонов"""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    # Получаем пользовательские шаблоны
    user_templates = []
    with get_db() as db:
        user_templates = db.query(PostTemplate).filter(
            PostTemplate.user_id == user_id
        ).order_by(PostTemplate.usage_count.desc()).limit(10).all()
    
    text = (
        "📋 **Шаблоны постов**\n\n"
        "Используй готовые шаблоны для быстрого создания постов.\n\n"
        "• Предустановленные шаблоны - готовые решения для типичных ситуаций\n"
        "• Мои шаблоны - созданные тобой шаблоны\n"
        "• Создать шаблон - сохрани часто используемый формат поста"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_templates_keyboard(PREDEFINED_TEMPLATES, user_templates),
        parse_mode="Markdown"
    )


async def templates_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback для шаблонов"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "templates_predefined":
        await query.edit_message_text(
            "📋 **Предустановленные шаблоны**\n\n"
            "Выбери шаблон:",
            reply_markup=get_predefined_templates_keyboard(),
            parse_mode="Markdown"
        )
    
    elif callback_data == "templates_user":
        user_id = update.effective_user.id
        with get_db() as db:
            user_templates = db.query(PostTemplate).filter(
                PostTemplate.user_id == user_id
            ).order_by(PostTemplate.usage_count.desc()).all()
        
        if not user_templates:
            await query.edit_message_text(
                "⭐ **Мои шаблоны**\n\n"
                "У тебя пока нет своих шаблонов.\n\n"
                "Создай шаблон из любого сгенерированного поста!",
                reply_markup=get_predefined_templates_keyboard()
            )
        else:
            await query.edit_message_text(
                "⭐ **Мои шаблоны**\n\n"
                "Выбери шаблон:",
                reply_markup=get_user_templates_keyboard(user_templates),
                parse_mode="Markdown"
            )
    
    elif callback_data.startswith("template_use_"):
        # Использование шаблона
        template_key = callback_data.replace("template_use_", "")
        
        if template_key.startswith("user_"):
            # Пользовательский шаблон
            template_id = int(template_key.replace("user_", ""))
            user_id = update.effective_user.id
            
            with get_db() as db:
                template = db.query(PostTemplate).filter(
                    PostTemplate.id == template_id,
                    PostTemplate.user_id == user_id
                ).first()
                
                if template:
                    template.usage_count += 1
                    db.commit()
                    
                    # Генерируем пост из шаблона
                    await generate_from_template(update, context, template.content_structure)
                else:
                    await query.answer("Шаблон не найден", show_alert=True)
        else:
            # Предустановленный шаблон
            if template_key in PREDEFINED_TEMPLATES:
                template = PREDEFINED_TEMPLATES[template_key]
                await generate_from_predefined_template(update, context, template)
    
    elif callback_data == "template_create":
        context.user_data['template_create'] = True
        context.user_data['_conversation_active'] = True
        
        await query.edit_message_text(
            "➕ **Создание шаблона**\n\n"
            "Отправь текст поста, который хочешь использовать как шаблон.\n\n"
            "Этот пост будет сохранен, и ты сможешь использовать его для генерации похожих постов:",
            parse_mode="Markdown"
        )
        
        return "waiting_template_text"
    
    elif callback_data == "templates_back":
        user_id = update.effective_user.id
        with get_db() as db:
            user_templates = db.query(PostTemplate).filter(
                PostTemplate.user_id == user_id
            ).all()
        
        await query.edit_message_text(
            "📋 **Шаблоны постов**\n\n"
            "Выбери действие:",
            reply_markup=get_templates_keyboard(PREDEFINED_TEMPLATES, user_templates),
            parse_mode="Markdown"
        )
    
    elif callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    return END


async def handle_template_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для создания шаблона"""
    text = update.message.text.strip()
    
    if not text or len(text) < 10:
        await update.message.reply_text(
            "❌ Текст слишком короткий. Напиши хотя бы 10 символов:"
        )
        return "waiting_template_text"
    
    # Предлагаем ввести название шаблона
    context.user_data['template_text'] = text
    
    await update.message.reply_text(
        "✅ Текст принят!\n\n"
        "📝 Как назвать этот шаблон?\n"
        "(Например: 'Отчет о мероприятии', 'Призыв к помощи'):"
    )
    
    return "waiting_template_name"


async def handle_template_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия шаблона и сохранение"""
    template_name = update.message.text.strip()
    
    if not template_name or len(template_name) < 3:
        await update.message.reply_text(
            "❌ Название слишком короткое. Напиши хотя бы 3 символа:"
        )
        return "waiting_template_name"
    
    user_id = update.effective_user.id
    template_text = context.user_data.get('template_text', '')
    
    # Сохраняем шаблон
    with get_db() as db:
        template = PostTemplate(
            user_id=user_id,
            template_name=template_name,
            category="пользовательский",
            content_structure={
                "text": template_text,
                "type": "custom"
            }
        )
        db.add(template)
        db.commit()
    
    await update.message.reply_text(
        f"✅ Шаблон '{template_name}' создан!\n\n"
        "Теперь ты можешь использовать его для генерации похожих постов.",
        reply_markup=None
    )
    
    context.user_data.pop('template_create', None)
    context.user_data.pop('template_text', None)
    context.user_data.pop('_conversation_active', None)
    
    return END


async def generate_from_template(update: Update, context: ContextTypes.DEFAULT_TYPE, template_structure: dict):
    """Генерация поста из шаблона"""
    query = update.callback_query if hasattr(update, 'callback_query') else None
    
    processing_msg = await (query.edit_message_text if query else update.message.reply_text)(
        "⏳ Генерирую пост из шаблона...\n\n"
        "Это может занять несколько секунд."
    ) if query else await update.message.reply_text(
        "⏳ Генерирую пост из шаблона...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        user_id = update.effective_user.id if hasattr(update, 'effective_user') else query.from_user.id
        template_text = template_structure.get('text', '')
        
        # Получаем профиль НКО
        from bot.database.models import NKOProfile
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        # Генерируем похожий пост
        nko_info = ""
        if nko_profile:
            if nko_profile.organization_name:
                nko_info += f"\nНКО: {nko_profile.organization_name}\n"
            if nko_profile.description:
                nko_info += f"Деятельность: {nko_profile.description}\n"
        
        prompt = f"""Создай новый пост на основе этого шаблона:

ШАБЛОН:
{template_text}

{nko_info}

Создай новый пост в похожем стиле и формате, но с новым содержанием. 
Пост должен быть актуальным и подходящим для некоммерческой организации."""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию постов для некоммерческих организаций.",
            temperature=0.7,
            max_tokens=300
        )
        
        if result and result.get("success"):
            generated_text = result.get("content", "")
            
            # Генерируем хештеги
            hashtags = await hashtag_generator.generate_hashtags(
                text=generated_text,
                nko_profile=nko_profile,
                count=5,
                use_ai=True
            )
            
            # Форматируем финальный текст
            final_text = text_processor.format_for_telegram(generated_text)
            if hashtags:
                final_text = text_processor.add_hashtags(final_text, hashtags)
            
            # Сохраняем в историю
            get_or_create_user(user_id, None, "")
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": generated_text,
                        "hashtags": hashtags,
                        "type": "template_based"
                    },
                    tags=hashtags
                )
                db.add(history_entry)
                db.commit()
            
            from bot.keyboards.inline import get_post_actions_keyboard
            await processing_msg.edit_text(
                f"✅ **Готово!** Вот пост из шаблона:\n\n{final_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации поста. Попробуй еще раз."
            )
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации из шаблона: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз."
        )
    
    context.user_data.pop('_conversation_active', None)
    return END


async def generate_from_predefined_template(update: Update, context: ContextTypes.DEFAULT_TYPE, template: dict):
    """Генерация поста из предустановленного шаблона"""
    query = update.callback_query
    
    processing_msg = await query.edit_message_text(
        f"⏳ Генерирую пост из шаблона '{template['name']}'...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        user_id = update.effective_user.id
        
        # Получаем профиль НКО
        from bot.database.models import NKOProfile
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
        
        prompt = f"""{template['prompt']}

{nko_info}

ТРЕБОВАНИЯ:
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна тема
- Естественные переходы"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию постов для некоммерческих организаций.",
            temperature=0.8,
            max_tokens=300
        )
        
        if result and result.get("success"):
            generated_text = result.get("content", "")
            
            # Генерируем хештеги
            hashtags = await hashtag_generator.generate_hashtags(
                text=generated_text,
                nko_profile=nko_profile,
                count=5,
                use_ai=True
            )
            
            # Форматируем финальный текст
            final_text = text_processor.format_for_telegram(generated_text)
            if hashtags:
                final_text = text_processor.add_hashtags(final_text, hashtags)
            
            # Сохраняем в историю
            get_or_create_user(user_id, None, "")
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": generated_text,
                        "hashtags": hashtags,
                        "type": "template_based",
                        "template_category": template['category']
                    },
                    tags=hashtags
                )
                db.add(history_entry)
                db.commit()
            
            from bot.keyboards.inline import get_post_actions_keyboard
            await processing_msg.edit_text(
                f"✅ **Готово!** Вот твой пост:\n\n{final_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации поста. Попробуй еще раз."
            )
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации из предустановленного шаблона: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз."
        )
    
    return END


def setup_templates_handlers(application):
    """Настройка обработчиков шаблонов"""
    # ConversationHandler для создания шаблона
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(templates_callback, pattern="^template_create$"),
        ],
        states={
            "waiting_template_text": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template_text)
            ],
            "waiting_template_name": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_template_name)
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)
    
    # Callback handler для шаблонов
    application.add_handler(
        CallbackQueryHandler(templates_callback, pattern="^templates_|^template_")
    )

