"""
Обработчики A/B тестирования постов
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


async def show_ab_testing_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню A/B тестирования"""
    text = (
        "🔬 **A/B тестирование**\n\n"
        "Создам несколько вариантов одного поста для сравнения.\n\n"
        "Опиши, какой пост нужно создать:"
    )
    
    context.user_data['ab_testing'] = {'variants': []}
    context.user_data['_conversation_active'] = True
    
    await update.message.reply_text(text, parse_mode="Markdown")
    return "waiting_ab_prompt"


async def handle_ab_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания поста для A/B теста"""
    prompt_text = update.message.text.strip()
    
    if not prompt_text or len(prompt_text) < 5:
        await update.message.reply_text(
            "❌ Описание слишком короткое. Напиши хотя бы 5 символов:"
        )
        return "waiting_ab_prompt"
    
    context.user_data['ab_testing']['prompt'] = prompt_text
    
    # Отправляем сообщение о генерации
    processing_msg = await update.message.reply_text(
        "⏳ Генерирую варианты поста...\n\n"
        "Создаю 3 разных варианта для сравнения. Это может занять некоторое время."
    )
    
    try:
        user_id = update.effective_user.id
        
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
        
        variants = []
        variant_styles = [
            ("разговорный", "Живой, разговорный стиль, как дружеская беседа"),
            ("официальный", "Официально-деловой стиль, сдержанный и профессиональный"),
            ("дружелюбный", "Дружелюбный стиль, теплый и эмоциональный")
        ]
        
        for style, style_desc in variant_styles:
            prompt = f"""Создай пост для некоммерческой организации.

Тема поста: {prompt_text}

{nko_info}

Стиль: {style_desc}

ТРЕБОВАНИЯ:
- Стиль: {style}
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
                text = result.get("content", "")
                
                # Генерируем хештеги
                hashtags = await hashtag_generator.generate_hashtags(
                    text=text,
                    nko_profile=nko_profile,
                    count=5,
                    use_ai=True
                )
                
                # Форматируем текст
                formatted_text = text_processor.format_for_telegram(text)
                if hashtags:
                    formatted_text = text_processor.add_hashtags(formatted_text, hashtags)
                
                variants.append({
                    "style": style,
                    "text": formatted_text,
                    "hashtags": hashtags,
                    "original": text
                })
        
        if len(variants) >= 3:
            context.user_data['ab_testing']['variants'] = variants
            
            # Отправляем варианты
            response_text = "✅ **Создано 3 варианта поста:**\n\n"
            
            for i, variant in enumerate(variants, 1):
                response_text += f"**Вариант {i} ({variant['style']}):**\n\n"
                response_text += f"{variant['text'][:500]}\n\n"
                response_text += "---\n\n"
            
            # Создаем клавиатуру для выбора
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Вариант 1", callback_data="ab_select_0"),
                    InlineKeyboardButton("✅ Вариант 2", callback_data="ab_select_1")
                ],
                [
                    InlineKeyboardButton("✅ Вариант 3", callback_data="ab_select_2")
                ],
                [
                    InlineKeyboardButton("💾 Сохранить все", callback_data="ab_save_all"),
                    InlineKeyboardButton("◀️ Назад", callback_data="main_menu")
                ]
            ])
            
            await processing_msg.edit_text(
                response_text[:4000],  # Ограничение Telegram
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            
            return "waiting_ab_selection"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при генерации вариантов. Попробуй еще раз."
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при A/B тестировании: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка. Попробуй еще раз."
        )
        context.user_data.pop('_conversation_active', None)
        return END


async def handle_ab_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора варианта A/B теста"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data.startswith("ab_select_"):
        variant_index = int(callback_data.replace("ab_select_", ""))
        variants = context.user_data.get('ab_testing', {}).get('variants', [])
        
        if 0 <= variant_index < len(variants):
            variant = variants[variant_index]
            
            # Сохраняем выбранный вариант
            user_id = update.effective_user.id
            get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
            
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": variant['original'],
                        "hashtags": variant['hashtags'],
                        "style": variant['style'],
                        "type": "ab_test_winner",
                        "ab_test": True
                    },
                    tags=variant['hashtags']
                )
                db.add(history_entry)
                db.commit()
            
            await query.edit_message_text(
                f"✅ **Вариант {variant_index + 1} сохранен!**\n\n{variant['text']}",
                parse_mode="Markdown"
            )
    
    elif callback_data == "ab_save_all":
        # Сохраняем все варианты
        user_id = update.effective_user.id
        variants = context.user_data.get('ab_testing', {}).get('variants', [])
        
        get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
        
        with get_db() as db:
            for i, variant in enumerate(variants):
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "text": variant['original'],
                        "hashtags": variant['hashtags'],
                        "style": variant['style'],
                        "type": "ab_test_variant",
                        "variant_number": i + 1,
                        "ab_test": True
                    },
                    tags=variant['hashtags']
                )
                db.add(history_entry)
            db.commit()
        
        await query.answer("✅ Все варианты сохранены!", show_alert=True)
    
    elif callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    context.user_data.pop('_conversation_active', None)
    return END


def setup_ab_testing_handlers(application):
    """Настройка обработчиков A/B тестирования"""
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔬 A/B тест$"), show_ab_testing_menu),
        ],
        states={
            "waiting_ab_prompt": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ab_prompt)
            ],
            "waiting_ab_selection": [
                CallbackQueryHandler(handle_ab_selection, pattern="^ab_")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)

