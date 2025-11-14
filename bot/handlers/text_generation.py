"""
Обработчики генерации текста
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.inline import (
    get_text_generation_types_keyboard, get_style_keyboard, get_post_actions_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard, get_back_keyboard
from bot.services.ai.openrouter import openrouter_api
from bot.services.content.hashtag_generator import hashtag_generator
from bot.services.content.text_processor import text_processor
from bot.database.models import ContentHistory, NKOProfile
from bot.database.database import get_db
from bot.utils.helpers import get_or_create_user
from bot.states.conversation import END
from telegram.ext import ConversationHandler

logger = logging.getLogger(__name__)


async def show_text_generation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню выбора типа генерации текста"""
    text = (
        "📝 **Генерация текста**\n\n"
        "Выбери способ генерации:\n\n"
        "• **Свободный текст** - введи идею, я перепишу её в готовый пост\n"
        "• **Структурированная форма** - отвечай на вопросы, я создам пост\n"
        "• **На основе примеров** - пришли примеры постов, я создам похожий стиль"
    )
    
    await update.message.reply_text(
        text,
        reply_markup=get_text_generation_types_keyboard(),
        parse_mode="Markdown"
    )


async def text_generation_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа генерации текста"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "text_gen_free":
        # Сохраняем режим перед отправкой сообщения
        context.user_data['text_gen_mode'] = 'free'
        context.user_data['_conversation_active'] = True  # Отмечаем, что ConversationHandler активен
        
        logger.info(f"Начало генерации свободного текста для пользователя {update.effective_user.id}")
        
        await query.edit_message_text(
            "📝 **Свободный текст**\n\n"
            "Напиши свою идею для поста. Я перепишу её в готовый пост с учетом твоего стиля и профиля НКО.\n\n"
            "Просто отправь текст своей идеи:",
            parse_mode="Markdown",
            reply_markup=None
        )
        
        logger.info(f"Состояние ConversationHandler установлено: waiting_free_text")
        return "waiting_free_text"
    
    elif callback_data == "text_gen_structured":
        await query.edit_message_text(
            "📋 **Структурированная форма**\n\n"
            "Я задам тебе несколько вопросов, чтобы создать идеальный пост.\n\n"
            "Начнем?",
            parse_mode="Markdown",
            reply_markup=None
        )
        # TODO: Реализовать структурированную форму
        context.user_data.pop('_conversation_active', None)
        return END
    
    elif callback_data == "text_gen_examples":
        await query.edit_message_text(
            "📚 **На основе примеров**\n\n"
            "Пришли 1-3 примера постов, которые тебе нравятся. Я проанализирую их стиль и создам похожий пост.\n\n"
            "Отправь примеры постов одним или несколькими сообщениями:",
            parse_mode="Markdown",
            reply_markup=None
        )
        context.user_data['text_gen_mode'] = 'examples'
        context.user_data['examples'] = []
        context.user_data['_conversation_active'] = True
        return "waiting_examples"
    
    elif callback_data == "main_menu":
        await query.edit_message_text("Возврат в главное меню")
        context.user_data.pop('_conversation_active', None)
        return END
    
    context.user_data.pop('_conversation_active', None)
    return END


async def handle_free_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка свободного текста для генерации"""
    user_text = update.message.text.strip()
    
    logger.info(f"✅ ConversationHandler перехватил сообщение! Получен текст для генерации: {user_text[:50]}... (длина: {len(user_text)})")
    
    if not user_text or len(user_text) < 5:
        await update.message.reply_text(
            "❌ Текст слишком короткий. Напиши хотя бы 5 символов:"
        )
        return "waiting_free_text"
    
    # Сохраняем текст
    context.user_data['free_text'] = user_text
    logger.info(f"Текст сохранен в user_data: {user_text[:30]}...")
    
    # Предлагаем выбрать стиль
    await update.message.reply_text(
        "✅ Текст принят!\n\n"
        "Выбери стиль написания поста:",
        reply_markup=get_style_keyboard()
    )
    
    return "waiting_style"


async def handle_style_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора стиля"""
    query = update.callback_query
    await query.answer()
    
    style_map = {
        "style_conversational": "разговорный",
        "style_formal": "официально-деловой",
        "style_artistic": "художественный",
        "style_neutral": "нейтральный",
        "style_friendly": "дружелюбный"
    }
    
    # Определяем, можно ли использовать эмодзи для этого стиля
    emoji_allowed_styles = ["разговорный", "дружелюбный", "художественный"]
    
    callback_data = query.data
    if callback_data not in style_map:
        await query.answer("Неверный выбор стиля")
        return "waiting_style"
    
    style = style_map[callback_data]
    context.user_data['style'] = style
    context.user_data['emoji_allowed'] = style in emoji_allowed_styles
    
    # Отправляем сообщение о генерации
    processing_msg = await query.edit_message_text(
        f"⏳ Генерирую пост в {style} стиле...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Получаем профиль НКО
        user_id = update.effective_user.id
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile and profile.is_complete:
                nko_profile = profile
        
        # Формируем промпт для генерации
        user_text = context.user_data.get('free_text', '')
        emoji_allowed = context.user_data.get('emoji_allowed', False)
        
        system_prompt = "Ты эксперт по созданию живого, естественного контента для некоммерческих организаций в социальных сетях. Твои тексты звучат искренне, по-человечески, без шаблонов и канцелярита. Ты умеешь создавать короткие, структурированные посты с абзацами, которые легко читать и которые вызывают эмоции."
        
        context_prompt = ""
        if nko_profile:
            if nko_profile.organization_name:
                context_prompt += f"Организация: {nko_profile.organization_name}. "
            if nko_profile.description:
                context_prompt += f"Деятельность: {nko_profile.description}. "
            if nko_profile.tone_of_voice:
                style_from_profile = {
                    "conversational": "разговорный",
                    "formal": "официально-деловой",
                    "artistic": "художественный",
                    "neutral": "нейтральный",
                    "friendly": "дружелюбный"
                }.get(nko_profile.tone_of_voice, style)
                style = style_from_profile
                # Обновляем разрешение на эмодзи на основе стиля из профиля
                emoji_allowed_styles = ["разговорный", "дружелюбный", "художественный"]
                emoji_allowed = style_from_profile in emoji_allowed_styles
        
        emoji_instruction = ""
        if emoji_allowed:
            emoji_instruction = "\n\n🎨 **ЭМОДЗИ:** Можно использовать эмодзи! Добавь 2-4 эмодзи для придания живости и эмоциональности тексту. Используй их естественно, не перебарщивай. Примеры: 🐾 🐕 ❤️ 🏠 🎉"
        else:
            emoji_instruction = "\n\n⚠️ **ЭМОДЗИ:** Для этого стиля эмодзи не используй. Текст должен быть без эмодзи."
        
        prompt = f"""{context_prompt}

Перепиши следующую идею в готовый пост для социальных сетей в {style} стиле:

{user_text}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. **АБЗАЦЫ - ОБЯЗАТЕЛЬНО!** Текст ДОЛЖЕН быть разбит на абзацы. Каждый абзац - отдельная мысль (2-3 предложения). Между абзацами должна быть пустая строка. Никогда не пиши текст одним блоком без абзацев!
2. **Живой, естественный язык** - избегай шаблонных фраз типа "теперь имеют возможность", "напоминаем, что", "в рамках нашего проекта". Пиши так, как говоришь вживую.
3. **Краткость** - пост должен быть 80-120 слов (короткие предложения, по делу).
4. **Фокус на одной теме** - не перескакивай с темы на тему, придерживайся основной идеи.
5. **Естественные переходы** - мысль должна течь плавно, без резких скачков.
6. **Эмоции** - используй естественные эмоции, но не перебарщивай. Пусть это звучит искренне.
7. **Простота** - избегай сложных конструкций, длинных предложений, канцелярита.
8. **Стиль {style}** - адаптируй под указанный стиль, но сохраняй естественность.{emoji_instruction}

Пример хорошего стиля (естественный, живой, С АБЗАЦАМИ{f", с эмодзи" if emoji_allowed else ", без эмодзи"}):
{'"Сегодня у нас важная новость! 🎉 В приюте появились новые жильцы - несколько собак нашли свой дом. 🐾\n\nЭто не просто животные. Это новые члены нашей большой семьи ❤️. Мы уже начали заботиться о них: ветеринарный осмотр, уютное место для жизни, внимание и ласка.\n\nЕсли хочешь поддержать - заходи в гости. Будем рады! 🏠"' if emoji_allowed else '"Сегодня у нас важная новость! В приюте появились новые жильцы - несколько собак нашли свой дом.\n\nЭто не просто животные. Это новые члены нашей большой семьи. Мы уже начали заботиться о них: ветеринарный осмотр, уютное место для жизни, внимание и ласка.\n\nЕсли хочешь поддержать - заходи в гости. Будем рады!"'}

ВАЖНО: Обрати внимание - между абзацами есть пустые строки! Твой текст ДОЛЖЕН быть так же структурирован.

Плохой пример (избегай):
"Или расскажите о нас своим знакомым — вместе мы сможем подарить этим собакам шанс на новую жизнь!"
(Слишком навязчиво, шаблонно, пафосно)

Избегай:
- "Теперь наши подопечные имеют возможность..."
- "В рамках нашего проекта мы осуществили..."
- "Мы рады сообщить вам о том, что..."
- "Или расскажите о нас своим знакомым..."
- "Вместе мы сможем..."
- "Подарите шанс на новую жизнь"
- Навязчивых призывов к действию (если нужен призыв - сделай его мягким и естественным)
- Длинных абзацев без разбивки
- Повторов одной и той же мысли
- Шаблонных фраз про "шанс на новую жизнь", "подарить счастье" и т.п.

ВАЖНО: Если нужен призыв к действию, сделай его:
- Естественным и ненавязчивым
- Коротким (1 предложение)
- Без пафоса и шаблонов
- Например: "Если хочешь помочь - заходи в гости" вместо "Вместе мы сможем подарить шанс на новую жизнь!"

Пиши просто, живо, с душой!"""
        
        # Генерируем текст с повышенной температурой для более живого текста
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,  # Увеличена температура для более живого и творческого текста
            max_tokens=300  # Уменьшено до 300 токенов для более коротких постов
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
            user_id = update.effective_user.id
            db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
            
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": generated_text,
                        "hashtags": hashtags,
                        "style": style,
                        "original_text": user_text
                    },
                    tags=hashtags
                )
                db.add(history_entry)
                db.commit()
            
            context.user_data['last_generated_text'] = final_text
            context.user_data['last_text_data'] = {
                "text": generated_text,
                "hashtags": hashtags
            }
            context.user_data['_conversation_active'] = True  # Продолжаем ConversationHandler
            
            # Отправляем результат
            await processing_msg.edit_text(
                f"✅ **Готово!** Вот твой пост:\n\n{final_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
            
            return "post_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации текста. Попробуй еще раз или выбери другой способ генерации.",
                reply_markup=get_text_generation_types_keyboard()
            )
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации текста: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз.",
            reply_markup=get_text_generation_types_keyboard()
        )
        return END


async def handle_examples_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка примеров постов"""
    text = update.message.text
    examples = context.user_data.setdefault('examples', [])
    
    examples.append(text)
    
    if len(examples) < 3:
        await update.message.reply_text(
            f"✅ Пример {len(examples)} принят!\n\n"
            f"Можешь прислать еще {3 - len(examples)} пример(а) или нажми 'Готово' для начала генерации.",
            reply_markup=None  # TODO: Добавить кнопку "Готово"
        )
        return "waiting_examples"
    else:
        await update.message.reply_text(
            "✅ Примеры приняты! Теперь опиши, какой пост нужно создать на основе этих примеров:",
            reply_markup=None
        )
        return "waiting_examples_prompt"


# TODO: Реализовать остальные функции генерации текста


def setup_text_generation_handlers(application):
    """Настройка обработчиков генерации текста"""
    # ВАЖНО: НЕ регистрируем отдельный CallbackQueryHandler для text_gen_,
    # так как это будет конфликтовать с ConversationHandler!
    # ConversationHandler сам обработает callback через entry_points
    
    # Conversation handler для свободного текста
    # Важно: ConversationHandler отслеживает состояние автоматически через context.user_data
    # После callback query состояние устанавливается, и следующий Message должен обработаться
    free_text_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(text_generation_type_callback, pattern="^text_gen_free$"),
        ],
        states={
            "waiting_free_text": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text)
            ],
            "waiting_style": [
                CallbackQueryHandler(handle_style_selection, pattern="^style_")
            ],
            "post_ready": [
                CallbackQueryHandler(lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1], pattern="^main_menu$")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True
        # per_message по умолчанию False - это правильно для отслеживания состояния между сообщениями
    )
    
    application.add_handler(free_text_handler)
    
    # Conversation handler для примеров
    examples_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(text_generation_type_callback, pattern="^text_gen_examples$"),
        ],
        states={
            "waiting_examples": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_examples_text)
            ],
            "waiting_examples_prompt": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: END)  # TODO: Реализовать
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(examples_handler)

