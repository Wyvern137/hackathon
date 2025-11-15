"""
Обработчики генерации серий связанных постов
"""
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.services.ai.openrouter import openrouter_api
from bot.services.content.hashtag_generator import hashtag_generator
from bot.services.content.text_processor import text_processor
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory, NKOProfile
from bot.database.database import get_db
from bot.states.conversation import END

logger = logging.getLogger(__name__)


async def show_post_series_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню генерации серии постов"""
    text = (
        "📚 **Генерация серии постов**\n\n"
        "Создам серию связанных постов (3-5 постов) на одну тему.\n\n"
        "Опиши тему серии или основную идею:"
    )
    
    context.user_data['post_series'] = {}
    context.user_data['_conversation_active'] = True
    
    await update.message.reply_text(text, parse_mode="Markdown")
    return "waiting_series_topic"


async def handle_series_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка темы серии"""
    topic = update.message.text.strip()
    
    if not topic or len(topic) < 5:
        await update.message.reply_text(
            "❌ Тема слишком короткая. Напиши хотя бы 5 символов:"
        )
        return "waiting_series_topic"
    
    context.user_data['post_series']['topic'] = topic
    
    # Предлагаем выбрать количество постов
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("3 поста", callback_data="series_count_3"),
            InlineKeyboardButton("4 поста", callback_data="series_count_4"),
            InlineKeyboardButton("5 постов", callback_data="series_count_5")
        ],
        [
            InlineKeyboardButton("◀️ Назад", callback_data="series_back")
        ]
    ])
    
    await update.message.reply_text(
        f"✅ Тема: {topic}\n\n"
        "Сколько постов создать в серии?",
        reply_markup=keyboard
    )
    
    return "waiting_series_count"


async def handle_series_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора количества постов"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "series_back":
        await query.edit_message_text(
            "📚 **Генерация серии постов**\n\n"
            "Опиши тему серии:",
            parse_mode="Markdown"
        )
        return "waiting_series_topic"
    
    if query.data.startswith("series_count_"):
        count = int(query.data.replace("series_count_", ""))
        context.user_data['post_series']['count'] = count
        
        # Начинаем генерацию
        await query.edit_message_text(
            f"⏳ Генерирую серию из {count} постов...\n\n"
            "Это может занять некоторое время."
        )
        
        return await generate_post_series(update, context, count)


async def generate_post_series(update: Update, context: ContextTypes.DEFAULT_TYPE, count: int):
    """Генерирует серию постов"""
    try:
        user_id = update.effective_user.id
        topic = context.user_data['post_series'].get('topic', '')
        
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
        
        # Генерируем план серии
        series_plan_prompt = f"""Создай план серии из {count} связанных постов на тему: {topic}

{nko_info}

Каждый пост должен:
- Быть частью общей истории/темы
- Логически переходить к следующему посту
- Быть самостоятельным (можно читать отдельно)
- Иметь свою подтему в рамках общей темы

Верни только план в формате:
1. [Название поста 1] - [краткое описание]
2. [Название поста 2] - [краткое описание]
...
"""
        
        plan_result = await openrouter_api.generate_text(
            prompt=series_plan_prompt,
            system_prompt="Ты эксперт по созданию контент-планов для социальных сетей.",
            temperature=0.7,
            max_tokens=500
        )
        
        if not plan_result or not plan_result.get("success"):
            await update.callback_query.edit_message_text(
                "❌ Ошибка при создании плана серии. Попробуй еще раз."
            )
            context.user_data.pop('_conversation_active', None)
            return END
        
        series_plan = plan_result.get("content", "")
        context.user_data['post_series']['plan'] = series_plan
        
        # Генерируем каждый пост
        generated_posts = []
        query = update.callback_query if hasattr(update, 'callback_query') else None
        
        for i in range(count):
            if query:
                await query.edit_message_text(
                    f"⏳ Генерирую пост {i+1} из {count}...\n\n"
                    f"План серии:\n{series_plan[:200]}..."
                )
            
            # Формируем промпт для поста
            post_prompt = f"""Создай пост {i+1} из {count} для серии постов.

Тема серии: {topic}

План серии:
{series_plan}

{nko_info}

Это пост {i+1} из {count}. Он должен:
- Быть частью общей истории
- Логически связан с предыдущими постами (если не первый)
- Подготавливать к следующим постам (если не последний)
- Быть самостоятельным и понятным

ТРЕБОВАНИЯ:
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна подтема
- Естественные переходы"""
            
            result = await openrouter_api.generate_text(
                prompt=post_prompt,
                system_prompt="Ты эксперт по созданию постов для некоммерческих организаций.",
                temperature=0.8,
                max_tokens=300
            )
            
            if result and result.get("success"):
                text = result.get("content", "")
                
                # Генерируем хештеги
                hashtags = await hashtag_generator.generate_hashtags(
                    text=text,
                    nko_profile=nko_profile,
                    count=5,
                    use_ai=True
                )
                
                # Форматируем
                formatted_text = text_processor.format_for_telegram(text)
                if hashtags:
                    formatted_text = text_processor.add_hashtags(formatted_text, hashtags)
                
                generated_posts.append({
                    "number": i + 1,
                    "text": formatted_text,
                    "original": text,
                    "hashtags": hashtags
                })
        
        # Сохраняем серию в историю
        get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
        
        with get_db() as db:
            for post in generated_posts:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": post["original"],
                        "hashtags": post["hashtags"],
                        "series_number": post["number"],
                        "series_total": count,
                        "series_topic": topic,
                        "type": "series"
                    },
                    tags=post["hashtags"]
                )
                db.add(history_entry)
            db.commit()
        
        # Отправляем результаты
        response_text = f"✅ **Серия из {count} постов создана!**\n\n"
        response_text += f"**Тема:** {topic}\n\n"
        response_text += "**Посты:**\n\n"
        
        for post in generated_posts:
            response_text += f"**Пост {post['number']}:**\n{post['text'][:200]}...\n\n"
            response_text += "---\n\n"
        
        # Клавиатура для просмотра постов
        keyboard_buttons = []
        for i in range(count):
            keyboard_buttons.append([
                InlineKeyboardButton(f"📝 Пост {i+1}", callback_data=f"series_view_{i}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton("💾 Сохранить все", callback_data="series_save_all"),
            InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")
        ])
        
        keyboard = InlineKeyboardMarkup(keyboard_buttons)
        
        if query:
            await query.edit_message_text(
                response_text[:4000],  # Ограничение Telegram
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                response_text[:4000],
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
        
        context.user_data['post_series']['posts'] = generated_posts
        context.user_data.pop('_conversation_active', None)
        
        return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации серии постов: {e}")
        error_msg = "❌ Произошла ошибка при генерации серии. Попробуй еще раз."
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        context.user_data.pop('_conversation_active', None)
        return END


def setup_post_series_handlers(application):
    """Настройка обработчиков генерации серий постов"""
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📚 Серия постов$"), show_post_series_menu),
        ],
        states={
            "waiting_series_topic": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_series_topic)
            ],
            "waiting_series_count": [
                CallbackQueryHandler(handle_series_count, pattern="^series_")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)

