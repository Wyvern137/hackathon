"""
Обработчики генерации текста
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.inline import (
    get_text_generation_types_keyboard, get_style_keyboard, get_post_actions_keyboard,
    get_event_type_keyboard, get_yes_no_keyboard
)
from bot.keyboards.main_menu import get_main_menu_keyboard, get_back_keyboard
from bot.services.ai.openrouter import openrouter_api
from bot.services.ai.speech_recognition import speech_recognition_service
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
        context.user_data['text_gen_mode'] = 'structured'
        context.user_data['structured_data'] = {}
        context.user_data['_conversation_active'] = True
        
        await query.edit_message_text(
            "📋 **Структурированная форма**\n\n"
            "Я задам тебе несколько вопросов, чтобы создать идеальный пост.\n\n"
            "**Шаг 1 из 6:**\n"
            "Выбери тип события:",
            parse_mode="Markdown",
            reply_markup=get_event_type_keyboard()
        )
        
        return "waiting_event_type"
    
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
    """Обработка свободного текста для генерации (текст или голосовое)"""
    user_text = None
    
    # Проверяем, это текстовое или голосовое сообщение
    if update.message.voice:
        # Голосовое сообщение
        logger.info(f"Получено голосовое сообщение для генерации текста")
        
        # Показываем индикатор обработки
        processing_msg = await update.message.reply_text(
            "🎤 Распознаю голосовое сообщение...\n\n"
            "Это может занять несколько секунд."
        )
        
        try:
            # Распознаем речь
            transcribed_text = await speech_recognition_service.transcribe_voice_message(
                voice_file_id=update.message.voice.file_id,
                bot=context.bot
            )
            
            if not transcribed_text or len(transcribed_text.strip()) < 5:
                await processing_msg.edit_text(
                    "❌ Не удалось распознать голосовое сообщение или текст слишком короткий.\n\n"
                    "Попробуй еще раз или отправь текст:"
                )
                return "waiting_free_text"
            
            user_text = transcribed_text.strip()
            
            # Показываем транскрипцию пользователю
            await processing_msg.edit_text(
                f"✅ Распознано:\n\n*{user_text}*\n\n"
                "Если нужно исправить, отправь текст вручную.",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.exception(f"Ошибка при распознавании голосового сообщения: {e}")
            await processing_msg.edit_text(
                "❌ Ошибка при распознавании голосового сообщения.\n\n"
                "Попробуй отправить текст вручную:"
            )
            return "waiting_free_text"
    
    elif update.message.text:
        # Текстовое сообщение
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
    
    # Пытаемся извлечь стиль из текста
    extracted_style = speech_recognition_service.extract_style_from_text(user_text)
    
    if extracted_style:
        # Стиль найден в тексте, пропускаем выбор стиля
        context.user_data['style'] = extracted_style
        emoji_allowed_styles = ["разговорный", "дружелюбный", "художественный"]
        context.user_data['emoji_allowed'] = extracted_style in emoji_allowed_styles
        
        # Переходим сразу к генерации
        processing_msg = await update.message.reply_text(
            f"✅ Стиль определен: {extracted_style}\n\n"
            "⏳ Генерирую пост в этом стиле...\n\n"
            "Это может занять несколько секунд."
        )
        
        # Вызываем генерацию напрямую
        return await _generate_text_from_free_input(update, context, processing_msg, extracted_style)
    
    # Стиль не найден, предлагаем выбрать
    await update.message.reply_text(
        "✅ Текст принят!\n\n"
        "Выбери стиль написания поста:",
        reply_markup=get_style_keyboard()
    )
    
    return "waiting_style"


async def _generate_text_from_free_input(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    processing_msg,
    style: str
):
    """
    Вспомогательная функция для генерации текста из свободного ввода
    
    Args:
        update: Update объект
        context: Context объект
        processing_msg: Сообщение для обновления статуса
        style: Выбранный стиль
    """
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
            if hasattr(processing_msg, 'edit_text'):
                await processing_msg.edit_text(
                    f"✅ **Готово!** Вот твой пост:\n\n{final_text}",
                    reply_markup=get_post_actions_keyboard(),
                    parse_mode="Markdown"
                )
            else:
                await processing_msg.reply_text(
                    f"✅ **Готово!** Вот твой пост:\n\n{final_text}",
                    reply_markup=get_post_actions_keyboard(),
                    parse_mode="Markdown"
                )
            
            return "post_ready"
        else:
            error_msg = "❌ Ошибка при генерации текста. Попробуй еще раз или выбери другой способ генерации."
            if hasattr(processing_msg, 'edit_text'):
                await processing_msg.edit_text(error_msg, reply_markup=get_text_generation_types_keyboard())
            else:
                await processing_msg.reply_text(error_msg, reply_markup=get_text_generation_types_keyboard())
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации текста: {e}")
        error_msg = "❌ Произошла ошибка при генерации. Попробуй еще раз."
        if hasattr(processing_msg, 'edit_text'):
            await processing_msg.edit_text(error_msg, reply_markup=get_text_generation_types_keyboard())
        else:
            await processing_msg.reply_text(error_msg, reply_markup=get_text_generation_types_keyboard())
        return END


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
    
    return await _generate_text_from_free_input(update, context, processing_msg, style)


async def handle_examples_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка примеров постов"""
    text = update.message.text.strip()
    
    if not text or len(text) < 10:
        await update.message.reply_text(
            "❌ Пример слишком короткий. Напиши хотя бы 10 символов:"
        )
        return "waiting_examples"
    
    examples = context.user_data.setdefault('examples', [])
    examples.append(text)
    
    if len(examples) < 3:
        await update.message.reply_text(
            f"✅ Пример {len(examples)} принят!\n\n"
            f"Можешь прислать еще {3 - len(examples)} пример(а) или напиши 'готово' для начала генерации:"
        )
        return "waiting_examples"
    else:
        await update.message.reply_text(
            "✅ Примеры приняты (3 из 3)! Теперь опиши, какой пост нужно создать на основе этих примеров:",
            reply_markup=None
        )
        return "waiting_examples_prompt"


async def handle_examples_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания нового поста и генерация на основе примеров"""
    prompt_text = update.message.text.strip()
    
    if not prompt_text or len(prompt_text) < 5:
        await update.message.reply_text(
            "❌ Описание слишком короткое. Напиши хотя бы 5 символов:"
        )
        return "waiting_examples_prompt"
    
    examples = context.user_data.get('examples', [])
    
    if not examples:
        await update.message.reply_text(
            "❌ Примеры не найдены. Начни заново.",
            reply_markup=get_text_generation_types_keyboard()
        )
        context.user_data.pop('_conversation_active', None)
        return END
    
    # Отправляем сообщение о генерации
    processing_msg = await update.message.reply_text(
        "⏳ Анализирую стиль примеров и создаю похожий пост...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        user_id = update.effective_user.id
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        # Формируем промпт для анализа стиля и генерации
        examples_text = "\n\n---\n\n".join([f"Пример {i+1}:\n{ex}" for i, ex in enumerate(examples)])
        
        nko_info = ""
        if nko_profile:
            if nko_profile.organization_name:
                nko_info += f"\nНКО: {nko_profile.organization_name}\n"
            if nko_profile.description:
                nko_info += f"Деятельность: {nko_profile.description}\n"
        
        system_prompt = """Ты — эксперт по анализу стиля текстов и созданию похожих постов.

ТРЕБОВАНИЯ К ТЕКСТУ:
- Живой, естественный язык (как человек разговаривает с другом)
- Абзацы - ОБЯЗАТЕЛЬНО! Разделяй абзацы пустой строкой
- Краткость (80-120 слов)
- Фокус на одной теме
- Естественные переходы между предложениями
- Эмоции - уместные, без перебора
- Простота - избегай сложных конструкций и канцелярита

ИЗБЕГАЙ:
- Шаблонных фраз ("теперь имеют возможность", "в рамках мероприятия", "не остаются без внимания")
- Машинного языка
- Длинных предложений без абзацев
- Скачков с темы на тему
- Пафоса и высокопарности"""

        prompt = f"""Проанализируй стиль следующих примеров постов и создай новый пост в похожем стиле.

ПРИМЕРЫ:
{examples_text}

{nko_info}

ТЕМА НОВОГО ПОСТА:
{prompt_text}

Создай пост, который:
1. Похож по стилю на приведенные примеры (тон, длина предложений, использование эмодзи, структура)
2. Соответствует теме: {prompt_text}
3. Подходит для некоммерческой организации
4. Содержит 80-120 слов
5. Разделен на абзацы (пустой строкой между абзацами)

ВАЖНО: Воспроизведи стиль примеров, но создай новый уникальный текст на заданную тему."""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,
            max_tokens=400
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
            db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
            
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": generated_text,
                        "hashtags": hashtags,
                        "examples_used": examples,
                        "prompt": prompt_text,
                        "type": "examples_based"
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
            
            # Отправляем результат
            await processing_msg.edit_text(
                f"✅ **Готово!** Вот твой пост в стиле примеров:\n\n{final_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
            
            return "post_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации текста. Попробуй еще раз.",
                reply_markup=get_text_generation_types_keyboard()
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации текста на основе примеров: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз.",
            reply_markup=get_text_generation_types_keyboard()
        )
        context.user_data.pop('_conversation_active', None)
        return END


async def handle_event_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа события"""
    query = update.callback_query
    await query.answer()
    
    event_type_map = {
        "event_news": "новость",
        "event_announcement": "анонс",
        "event_report": "отчет",
        "event_thanks": "благодарность",
        "event_congratulations": "поздравление"
    }
    
    callback_data = query.data
    
    if callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    if callback_data not in event_type_map:
        await query.answer("Неверный выбор типа события")
        return "waiting_event_type"
    
    event_type = event_type_map[callback_data]
    context.user_data['structured_data']['event_type'] = event_type
    
    await query.edit_message_text(
        f"✅ Тип события: {event_type}\n\n"
        "**Шаг 2 из 6:**\n"
        "📝 Как называется событие или тема поста?\n"
        "(Например: 'Открытие нового приюта' или 'Благодарность волонтерам'):",
        parse_mode="Markdown"
    )
    
    return "waiting_event_name"


async def handle_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия события"""
    event_name = update.message.text.strip()
    
    if not event_name or len(event_name) < 3:
        await update.message.reply_text(
            "❌ Название слишком короткое. Напиши хотя бы 3 символа:"
        )
        return "waiting_event_name"
    
    context.user_data['structured_data']['event_name'] = event_name
    
    await update.message.reply_text(
        f"✅ Название: {event_name}\n\n"
        "**Шаг 3 из 6:**\n"
        "📅 Есть ли дата и время события?\n"
        "(Напиши дату и время или 'нет', если не применимо):"
    )
    
    return "waiting_event_date"


async def handle_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка даты события"""
    event_date = update.message.text.strip()
    
    context.user_data['structured_data']['event_date'] = event_date if event_date.lower() not in ['нет', 'no', 'н'] else None
    
    await update.message.reply_text(
        f"✅ Дата: {event_date if context.user_data['structured_data']['event_date'] else 'не указана'}\n\n"
        "**Шаг 4 из 6:**\n"
        "📍 Где происходит событие?\n"
        "(Напиши место проведения или 'нет', если не применимо):"
    )
    
    return "waiting_event_place"


async def handle_event_place(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка места события"""
    event_place = update.message.text.strip()
    
    context.user_data['structured_data']['event_place'] = event_place if event_place.lower() not in ['нет', 'no', 'н'] else None
    
    await update.message.reply_text(
        f"✅ Место: {event_place if context.user_data['structured_data']['event_place'] else 'не указано'}\n\n"
        "**Шаг 5 из 6:**\n"
        "👥 Кто участвует или кому адресован пост?\n"
        "(Например: 'волонтеры', 'дети из приюта' или просто опиши целевую аудиторию):"
    )
    
    return "waiting_participants"


async def handle_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка участников/аудитории"""
    participants = update.message.text.strip()
    
    context.user_data['structured_data']['participants'] = participants
    
    await update.message.reply_text(
        f"✅ Участники/Аудитория: {participants}\n\n"
        "**Шаг 6 из 6:**\n"
        "📝 Дополнительные детали (опционально):\n"
        "(Напиши любую дополнительную информацию или 'пропустить'):"
    )
    
    return "waiting_details"


async def handle_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка дополнительных деталей и генерация поста"""
    details = update.message.text.strip()
    
    if details.lower() not in ['пропустить', 'skip', 'пропустить']:
        context.user_data['structured_data']['details'] = details
    else:
        context.user_data['structured_data']['details'] = None
    
    # Предлагаем выбрать стиль
    await update.message.reply_text(
        "✅ Все данные собраны!\n\n"
        "Выбери стиль написания поста:",
        reply_markup=get_style_keyboard()
    )
    
    return "waiting_structured_style"


async def handle_structured_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора стиля для структурированной формы и генерация"""
    query = update.callback_query
    await query.answer()
    
    style_map = {
        "style_conversational": "разговорный",
        "style_formal": "официально-деловой",
        "style_artistic": "художественный",
        "style_neutral": "нейтральный",
        "style_friendly": "дружелюбный"
    }
    
    callback_data = query.data
    if callback_data not in style_map:
        await query.answer("Неверный выбор стиля")
        return "waiting_structured_style"
    
    style = style_map[callback_data]
    emoji_allowed_styles = ["разговорный", "дружелюбный", "художественный"]
    context.user_data['style'] = style
    context.user_data['emoji_allowed'] = style in emoji_allowed_styles
    
    # Отправляем сообщение о генерации
    processing_msg = await query.edit_message_text(
        f"⏳ Генерирую пост в {style} стиле...\n\n"
        "Это может занять несколько секунд."
    )
    
    try:
        structured_data = context.user_data.get('structured_data', {})
        
        # Получаем профиль НКО
        user_id = update.effective_user.id
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        # Формируем промпт для генерации
        event_info = f"Тип события: {structured_data.get('event_type', 'пост')}\n"
        event_info += f"Название: {structured_data.get('event_name', '')}\n"
        if structured_data.get('event_date'):
            event_info += f"Дата: {structured_data.get('event_date')}\n"
        if structured_data.get('event_place'):
            event_info += f"Место: {structured_data.get('event_place')}\n"
        event_info += f"Участники/Аудитория: {structured_data.get('participants', '')}\n"
        if structured_data.get('details'):
            event_info += f"Дополнительные детали: {structured_data.get('details')}\n"
        
        nko_info = ""
        if nko_profile:
            if nko_profile.organization_name:
                nko_info += f"\nНКО: {nko_profile.organization_name}\n"
            if nko_profile.description:
                nko_info += f"Деятельность: {nko_profile.description}\n"
        
        # Определяем инструкции по эмодзи
        emoji_instruction = ""
        if context.user_data.get('emoji_allowed'):
            emoji_instruction = "\n- Используй 2-4 эмодзи естественно, там где уместно (НЕ в каждом предложении!)"
        else:
            emoji_instruction = "\n- НЕ используй эмодзи"
        
        system_prompt = f"""Ты — эксперт по написанию постов для некоммерческих организаций в {style} стиле.

ТРЕБОВАНИЯ К ТЕКСТУ:
- Живой, естественный язык (как человек разговаривает с другом)
- Абзацы - ОБЯЗАТЕЛЬНО! Разделяй абзацы пустой строкой
- Краткость (80-120 слов)
- Фокус на одной теме
- Естественные переходы между предложениями
- Эмоции - уместные, без перебора
- Простота - избегай сложных конструкций и канцелярита
{emoji_instruction}

ИЗБЕГАЙ:
- Шаблонных фраз ("теперь имеют возможность", "в рамках мероприятия", "не остаются без внимания")
- Машинного языка
- Длинных предложений без абзацев
- Скачков с темы на тему
- Пафоса и высокопарности"""

        prompt = f"""Создай пост для некоммерческой организации на основе следующих данных:

{event_info}{nko_info}

ТРЕБОВАНИЯ:
- Стиль: {style}
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна тема
- Естественные переходы
- Уместные эмоции
- Простота языка"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt=system_prompt,
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
            db_user = get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
            
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": generated_text,
                        "hashtags": hashtags,
                        "style": style,
                        "structured_data": structured_data
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
            
            # Отправляем результат
            await processing_msg.edit_text(
                f"✅ **Готово!** Вот твой пост:\n\n{final_text}",
                reply_markup=get_post_actions_keyboard(),
                parse_mode="Markdown"
            )
            
            return "post_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации текста. Попробуй еще раз.",
                reply_markup=get_text_generation_types_keyboard()
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации структурированного текста: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз.",
            reply_markup=get_text_generation_types_keyboard()
        )
        context.user_data.pop('_conversation_active', None)
        return END


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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_free_text),
                MessageHandler(filters.VOICE, handle_free_text)
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_examples_prompt)
            ],
            "post_ready": [
                CallbackQueryHandler(lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1], pattern="^main_menu$")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(examples_handler)
    
    # Conversation handler для структурированной формы
    structured_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(text_generation_type_callback, pattern="^text_gen_structured$"),
        ],
        states={
            "waiting_event_type": [
                CallbackQueryHandler(handle_event_type, pattern="^event_|^main_menu$")
            ],
            "waiting_event_name": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_name)
            ],
            "waiting_event_date": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_date)
            ],
            "waiting_event_place": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_place)
            ],
            "waiting_participants": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_participants)
            ],
            "waiting_details": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_details)
            ],
            "waiting_structured_style": [
                CallbackQueryHandler(handle_structured_style, pattern="^style_")
            ],
            "post_ready": [
                CallbackQueryHandler(lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1], pattern="^main_menu$")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(structured_handler)

