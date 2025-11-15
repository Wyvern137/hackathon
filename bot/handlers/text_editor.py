"""
Обработчики редактора текста
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters
from bot.services.ai.openrouter import openrouter_api
from bot.services.content.text_processor import (
    text_processor,
    analyze_target_audience,
    suggest_seo_improvements,
    suggest_structure,
    compare_texts,
    check_tonality
)
from bot.services.content.style_checker import style_checker
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory, NKOProfile
from bot.database.database import get_db
from bot.keyboards.inline import get_text_editor_actions_keyboard
from bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def show_text_editor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню редактора текста"""
    text = (
        "✏️ **Редактор текста**\n\n"
        "Отправь текст для редактирования. Я проверю его на:\n"
        "• Орфографические ошибки\n"
        "• Грамматические ошибки\n"
        "• Стилистические недочеты\n"
        "• Логические несоответствия\n\n"
        "И предложу рекомендации по улучшению."
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    return "waiting_text"


async def handle_text_for_editing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для редактирования"""
    text = update.message.text
    
    if not text or len(text.strip()) < 10:
        await update.message.reply_text(
            "❌ Текст слишком короткий. Напиши хотя бы 10 символов:"
        )
        return "waiting_text"
    
    # Отправляем сообщение о обработке
    processing_msg = await update.message.reply_text("⏳ Анализирую текст...")
    
    try:
        user_id = update.effective_user.id
        get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
        
        # Получаем профиль НКО для проверки стиля
        nko_profile = None
        with get_db() as db:
            profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            if profile:
                nko_profile = profile
        
        # Расширенный анализ текста
        readability = text_processor.calculate_readability(text)
        sentiment = text_processor.analyze_sentiment(text)
        repetitions = text_processor.check_repetitions(text)
        length_check = text_processor.check_length_for_format(text, "post")
        
        # Проверка на соответствие стилю НКО (если есть профиль)
        style_check = None
        if nko_profile and nko_profile.is_complete:
            style_check = await style_checker.check_style(text, nko_profile)
        
        # Анализ целевой аудитории (если есть профиль)
        audience_analysis = None
        if nko_profile and nko_profile.target_audience:
            audience_analysis = await analyze_target_audience(text, nko_profile.target_audience)
        
        # Формируем промпт для редактирования с учетом всех данных
        style_info = ""
        if style_check:
            style_info = f"\nСтиль НКО: {nko_profile.tone_of_voice}\n"
            style_info += f"Результат проверки стиля: {'Соответствует' if style_check.get('matches_style') else 'Не соответствует'}\n"
        
        prompt = f"""Проанализируй следующий текст поста для социальных сетей и исправь его:

{text}
{style_info}

Проанализируй:
1. Орфографические ошибки
2. Грамматические ошибки
3. Пунктуационные ошибки
4. Стилистические недочеты
5. Логические несоответствия
6. Читаемость текста
7. Соответствие стилю НКО (если указано выше)

Предоставь:
1. Исправленный текст
2. Список исправлений с пояснениями
3. Рекомендации по улучшению текста
4. Оценку качества текста (1-10)

Формат ответа:
ИСПРАВЛЕННЫЙ ТЕКСТ:
[исправленный текст]

ИСПРАВЛЕНИЯ:
- [описание исправления 1]
- [описание исправления 2]

РЕКОМЕНДАЦИИ:
- [рекомендация 1]
- [рекомендация 2]

ОЦЕНКА: [оценка]/10"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по редактированию текстов и корректуре.",
            temperature=0.3,
            max_tokens=800
        )
        
        if result and result.get("success"):
            edited_content = result.get("content", "")
            
            # Формируем расширенный отчет
            report = f"✅ **Редактирование завершено!**\n\n"
            report += f"**Исправленный текст:**\n{edited_content}\n\n"
            
            # Добавляем метрики
            report += "**📊 Анализ текста:**\n"
            report += f"• Читаемость: {readability.get('readability_level', 'Недоступно')}\n"
            report += f"• Тональность: {sentiment.get('tonality', 'Нейтральный')}\n"
            report += f"• Длина: {length_check['length']} символов ({length_check['word_count']} слов)\n"
            report += f"• {length_check['recommendation']}\n"
            
            # Добавляем информацию о повторениях
            if repetitions.get("repeated_words") or repetitions.get("repeated_phrases"):
                report += "\n**⚠️ Обнаружены повторения:**\n"
                if repetitions.get("repeated_words"):
                    top_word = max(repetitions["repeated_words"].items(), key=lambda x: x[1])
                    report += f"• Слово '{top_word[0]}' встречается {top_word[1]} раз\n"
                if repetitions.get("repeated_phrases"):
                    top_phrase = max(repetitions["repeated_phrases"].items(), key=lambda x: x[1])
                    report += f"• Фраза '{top_phrase[0]}' повторяется {top_phrase[1]} раз\n"
            
            # Добавляем проверку стиля НКО
            if style_check:
                if style_check.get("matches_style"):
                    report += "\n✅ Текст соответствует стилю НКО\n"
                else:
                    report += "\n⚠️ Текст не полностью соответствует стилю НКО\n"
                    if style_check.get("recommendations"):
                        for rec in style_check["recommendations"][:3]:
                            report += f"• {rec}\n"
            
            # Добавляем анализ аудитории
            if audience_analysis:
                if audience_analysis.get("fits_audience"):
                    report += f"\n✅ Текст подходит для целевой аудитории ({audience_analysis.get('score', 7)}/10)\n"
                else:
                    report += f"\n⚠️ Текст может быть улучшен для аудитории\n"
            
            # Сохраняем в историю
            with get_db() as db:
                history_entry = ContentHistory(
                    user_id=user_id,
                    content_type="text",
                    content_data={
                        "original_text": text,
                        "edited_text": edited_content,
                        "type": "edited",
                        "readability": readability,
                        "sentiment": sentiment,
                        "repetitions": repetitions,
                        "style_check": style_check,
                        "audience_analysis": audience_analysis
                    }
                )
                db.add(history_entry)
                db.commit()
            
            context.user_data['edited_text'] = edited_content
            context.user_data['original_text'] = text
            context.user_data['analysis_data'] = {
                "readability": readability,
                "sentiment": sentiment,
                "repetitions": repetitions,
                "style_check": style_check,
                "audience_analysis": audience_analysis
            }
            
            await processing_msg.edit_text(
                report,
                reply_markup=get_text_editor_actions_keyboard(),
                parse_mode="Markdown"
            )
            
            return "text_analyzed"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при редактировании текста. Попробуй еще раз."
            )
    
    except Exception as e:
        logger.exception(f"Ошибка при редактировании текста: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при редактировании. Попробуй еще раз."
        )
    
    from telegram.ext import ConversationHandler
    return ConversationHandler.END


async def text_editor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback-ов редактора текста"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    analysis_data = context.user_data.get('analysis_data', {})
    edited_text = context.user_data.get('edited_text', '')
    original_text = context.user_data.get('original_text', '')
    
    if callback_data == "editor_seo":
        # Анализ SEO
        seo_analysis = await suggest_seo_improvements(edited_text)
        
        text = "🔍 **SEO анализ:**\n\n"
        if seo_analysis.get("needs_seo"):
            text += "Рекомендуются улучшения для SEO:\n"
            if seo_analysis.get("keywords_suggestions"):
                text += f"Ключевые слова: {', '.join(seo_analysis['keywords_suggestions'][:5])}\n"
            if seo_analysis.get("improvements"):
                text += "\nРекомендации:\n"
                for imp in seo_analysis["improvements"][:5]:
                    text += f"• {imp}\n"
        else:
            text += "Текст не требует SEO-оптимизации."
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "editor_structure":
        # Предложение структуры
        structure = await suggest_structure(edited_text)
        
        text = "📐 **Предложение структуры:**\n\n"
        if structure.get("improvements"):
            text += "Рекомендации:\n"
            for imp in structure["improvements"][:5]:
                text += f"• {imp}\n"
            text += f"\n**Улучшенный текст:**\n{structure.get('formatted_text', edited_text)[:500]}..."
        else:
            text += "Структура текста оптимальна."
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "editor_tonality":
        # Проверка тональности
        sentiment = analysis_data.get("sentiment", {})
        text = f"🎭 **Анализ тональности:**\n\n"
        text += f"Определенная тональность: {sentiment.get('tonality', 'Нейтральный')}\n"
        if sentiment.get("scores"):
            scores = sentiment["scores"]
            text += f"Позитивность: {scores.get('positive', 0):.2f}\n"
            text += f"Нейтральность: {scores.get('neutral', 0):.2f}\n"
            text += f"Негативность: {scores.get('negative', 0):.2f}\n"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "editor_readability":
        # Читаемость
        readability = analysis_data.get("readability", {})
        text = f"📖 **Читаемость текста:**\n\n"
        text += f"Уровень: {readability.get('readability_level', 'Недоступно')}\n"
        if readability.get("readability_score") is not None:
            text += f"Балл: {readability['readability_score']}/100\n"
        text += f"Слов: {readability.get('word_count', 0)}\n"
        text += f"Предложений: {readability.get('sentence_count', 0)}\n"
        text += f"Средняя длина предложения: {readability.get('avg_sentence_length', 0):.1f} слов"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "editor_repetitions":
        # Повторения
        repetitions = analysis_data.get("repetitions", {})
        text = "🔄 **Проверка повторений:**\n\n"
        
        if repetitions.get("repeated_words") or repetitions.get("repeated_phrases"):
            if repetitions.get("repeated_words"):
                text += "Часто повторяющиеся слова:\n"
                for word, count in list(repetitions["repeated_words"].items())[:5]:
                    text += f"• '{word}': {count} раз\n"
            
            if repetitions.get("repeated_phrases"):
                text += "\nПовторяющиеся фразы:\n"
                for phrase, count in list(repetitions["repeated_phrases"].items())[:3]:
                    text += f"• '{phrase}': {count} раз\n"
            
            if repetitions.get("suggestions"):
                text += "\nРекомендации:\n"
                for sug in repetitions["suggestions"][:3]:
                    text += f"• {sug}\n"
        else:
            text += "✅ Повторяющихся слов и фраз не обнаружено."
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    elif callback_data == "editor_stories":
        # Stories-версия
        stories_text = text_processor.generate_stories_version(edited_text)
        text = f"📱 **Версия для Stories:**\n\n{stories_text}"
        
        await query.edit_message_text(text, parse_mode="Markdown")
    
    return "text_analyzed"


def setup_text_editor_handlers(application):
    """Настройка обработчиков редактора текста"""
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^✏️ Редактор текста$"), show_text_editor_menu),
        ],
        states={
            "waiting_text": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_for_editing)
            ],
            "text_analyzed": [
                CallbackQueryHandler(text_editor_callback, pattern="^editor_")
            ]
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: ConversationHandler.END),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: ConversationHandler.END),
        ],
        allow_reentry=True
    )
    
    application.add_handler(conv_handler)

