"""
Обработка и форматирование текста
"""
import logging
import re
import json
from typing import List, Optional, Dict, Any
from collections import Counter
try:
    import textstat
except ImportError:
    textstat = None
    logging.warning("textstat не установлен, проверка читаемости будет недоступна")
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_available = True
except ImportError:
    vader_available = False
    logging.warning("vaderSentiment не установлен, анализ тональности будет через AI")

logger = logging.getLogger(__name__)


class TextProcessor:
    """Класс для обработки текста"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Очищает текст от лишних пробелов и символов
        
        Args:
            text: Исходный текст
        
        Returns:
            Очищенный текст
        """
        # Убираем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        # Убираем пробелы в начале и конце
        text = text.strip()
        return text
    
    @staticmethod
    def split_into_paragraphs(text: str, max_length: int = 2000) -> List[str]:
        """
        Разбивает текст на абзацы по длине
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина абзаца
        
        Returns:
            Список абзацев
        """
        paragraphs = []
        current_paragraph = ""
        
        sentences = re.split(r'[.!?]\s+', text)
        
        for sentence in sentences:
            if len(current_paragraph) + len(sentence) + 2 <= max_length:
                if current_paragraph:
                    current_paragraph += ". " + sentence
                else:
                    current_paragraph = sentence
            else:
                if current_paragraph:
                    paragraphs.append(current_paragraph + ".")
                current_paragraph = sentence
        
        if current_paragraph:
            paragraphs.append(current_paragraph + ".")
        
        return paragraphs
    
    @staticmethod
    def format_for_telegram(text: str) -> str:
        """
        Форматирует текст для Telegram с сохранением абзацев
        
        Args:
            text: Исходный текст
        
        Returns:
            Отформатированный текст с абзацами
        """
        # Если текст пустой, возвращаем как есть
        if not text or not text.strip():
            return text
        
        # Нормализуем переносы строк
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Разбиваем на строки
        lines = text.split('\n')
        
        # Обрабатываем строки: убираем пробелы в начале/конце, но сохраняем пустые строки для абзацев
        processed_lines = []
        for line in lines:
            stripped = line.strip()
            # Если строка не пустая - добавляем её
            if stripped:
                processed_lines.append(stripped)
            # Если строка пустая и это не первый/последний элемент, добавляем для создания абзаца
            elif processed_lines and processed_lines[-1] != '':
                processed_lines.append('')
        
        # Объединяем строки: между непустыми строками одной группы - один пробел, между группами - двойной перенос (абзац)
        result_lines = []
        for i, line in enumerate(processed_lines):
            if line:  # Непустая строка
                result_lines.append(line)
            else:  # Пустая строка - начинаем новый абзац
                # Добавляем пустую строку только если предыдущая строка была непустой
                if result_lines and result_lines[-1] != '':
                    result_lines.append('')
        
        # Объединяем результат с двойными переносами между абзацами
        # Группируем строки: непустые строки одной группы объединяем пробелом, группы разделяем двойным переносом
        final_text = ''
        current_paragraph = []
        
        for line in result_lines:
            if line:  # Непустая строка - добавляем в текущий абзац
                current_paragraph.append(line)
            else:  # Пустая строка - заканчиваем текущий абзац и начинаем новый
                if current_paragraph:
                    if final_text:
                        final_text += '\n\n' + ' '.join(current_paragraph)
                    else:
                        final_text = ' '.join(current_paragraph)
                    current_paragraph = []
        
        # Добавляем последний абзац, если он есть
        if current_paragraph:
            if final_text:
                final_text += '\n\n' + ' '.join(current_paragraph)
            else:
                final_text = ' '.join(current_paragraph)
        
        return final_text
    
    @staticmethod
    def add_hashtags(text: str, hashtags: List[str]) -> str:
        """
        Добавляет хештеги к тексту
        
        Args:
            text: Исходный текст
            hashtags: Список хештегов
        
        Returns:
            Текст с хештегами
        """
        if not hashtags:
            return text
        
        hashtags_str = ' '.join(hashtags)
        return f"{text}\n\n{hashtags_str}"
    
    @staticmethod
    def adapt_text_for_platform(text: str, platform: str) -> str:
        """
        Адаптирует текст под платформу (длина, формат)
        
        Args:
            text: Исходный текст
            platform: Платформа (telegram, vk, instagram, facebook)
        
        Returns:
            Адаптированный текст
        """
        platform_limits = {
            "telegram": 4096,  # Максимальная длина сообщения Telegram
            "vk": 5000,  # Максимальная длина поста ВКонтакте
            "instagram": 2200,  # Рекомендуемая длина поста Instagram
            "facebook": 63206,  # Максимальная длина поста Facebook
        }
        
        max_length = platform_limits.get(platform.lower(), 4096)
        
        if len(text) <= max_length:
            return text
        
        # Обрезаем текст с сохранением абзацев
        truncated = text[:max_length]
        # Находим последний перенос строки или пробел
        last_newline = truncated.rfind('\n\n')
        if last_newline > max_length * 0.8:  # Если нашли в последних 20%
            return truncated[:last_newline] + "\n\n..."
        
        last_space = truncated.rfind(' ')
        if last_space > max_length * 0.8:
            return truncated[:last_space] + "..."
        
        return truncated + "..."
    
    @staticmethod
    def calculate_readability(text: str) -> Dict[str, Any]:
        """
        Рассчитывает индекс читаемости текста (Flesch Reading Ease)
        
        Args:
            text: Текст для анализа
        
        Returns:
            Dict с показателями читаемости
        """
        if textstat is None:
            return {
                "readability_score": None,
                "readability_level": "Недоступно (textstat не установлен)",
                "word_count": len(text.split()),
                "sentence_count": len(re.split(r'[.!?]+', text)),
                "avg_sentence_length": 0
            }
        
        try:
            # Flesch Reading Ease (для русского языка используется упрощенная версия)
            # Чем выше балл, тем легче читать (0-100, где 100 - очень легко)
            score = textstat.flesch_reading_ease(text)
            
            # Определяем уровень читаемости
            if score >= 90:
                level = "Очень легко"
            elif score >= 80:
                level = "Легко"
            elif score >= 70:
                level = "Довольно легко"
            elif score >= 60:
                level = "Стандартный"
            elif score >= 50:
                level = "Довольно сложно"
            elif score >= 30:
                level = "Сложно"
            else:
                level = "Очень сложно"
            
            word_count = textstat.lexicon_count(text, removepunct=True)
            sentence_count = textstat.sentence_count(text)
            avg_sentence_length = word_count / sentence_count if sentence_count > 0 else 0
            
            return {
                "readability_score": round(score, 2),
                "readability_level": level,
                "word_count": word_count,
                "sentence_count": sentence_count,
                "avg_sentence_length": round(avg_sentence_length, 2)
            }
        
        except Exception as e:
            logger.error(f"Ошибка при расчете читаемости: {e}")
            return {
                "readability_score": None,
                "readability_level": "Ошибка расчета",
                "error": str(e)
            }
    
    @staticmethod
    def generate_stories_version(text: str, max_length: int = 100) -> str:
        """
        Создает короткую версию текста для Stories
        
        Args:
            text: Исходный текст
            max_length: Максимальная длина Stories-версии
        
        Returns:
            Короткая версия текста
        """
        # Убираем хештеги
        text_no_hashtags = re.sub(r'#\w+', '', text)
        # Убираем лишние пробелы
        text_clean = re.sub(r'\s+', ' ', text_no_hashtags).strip()
        
        if len(text_clean) <= max_length:
            return text_clean
        
        # Обрезаем по предложениям
        sentences = re.split(r'[.!?]\s+', text_clean)
        result = ""
        
        for sentence in sentences:
            if len(result) + len(sentence) + 2 <= max_length:
                if result:
                    result += ". " + sentence
                else:
                    result = sentence
            else:
                break
        
        if result:
            result += "..."
        else:
            # Если даже первое предложение слишком длинное, обрезаем его
            result = text_clean[:max_length-3] + "..."
        
        return result
    
    @staticmethod
    def check_length_for_format(text: str, format_type: str) -> Dict[str, Any]:
        """
        Проверяет длину текста под формат
        
        Args:
            text: Текст для проверки
            format_type: Тип формата (post, story, announcement)
        
        Returns:
            Dict с результатами проверки
        """
        format_limits = {
            "post": {"min": 80, "max": 500, "optimal": 150},
            "story": {"min": 20, "max": 100, "optimal": 50},
            "announcement": {"min": 50, "max": 300, "optimal": 100}
        }
        
        limits = format_limits.get(format_type.lower(), format_limits["post"])
        text_length = len(text)
        
        word_count = len(text.split())
        
        return {
            "length": text_length,
            "word_count": word_count,
            "format": format_type,
            "limits": limits,
            "is_valid": limits["min"] <= text_length <= limits["max"],
            "is_optimal": limits["min"] <= text_length <= limits["optimal"],
            "recommendation": _get_length_recommendation(text_length, limits)
        }


def _get_length_recommendation(length: int, limits: Dict[str, int]) -> str:
    """Возвращает рекомендацию по длине текста"""
    if length < limits["min"]:
        return f"Текст слишком короткий. Рекомендуется минимум {limits['min']} символов."
    elif length > limits["max"]:
        return f"Текст слишком длинный. Рекомендуется максимум {limits['max']} символов."
    elif length < limits["optimal"]:
        return f"Текст можно расширить до {limits['optimal']} символов для лучшей читаемости."
    else:
        return "Длина текста оптимальна для данного формата."


async def generate_headlines(text: str, count: int = 3) -> List[str]:
    """
    Генерирует варианты заголовков для поста через AI
    
    Args:
        text: Текст поста
        count: Количество вариантов заголовков
    
    Returns:
        Список вариантов заголовков
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Создай {count} вариантов привлекательных заголовков для следующего поста некоммерческой организации.

Текст поста:
{text[:500]}

Требования к заголовкам:
- Короткие и цепляющие (до 60 символов)
- Отражают суть поста
- Вызывают интерес
- Подходят для социальных сетей

Ответь только вариантами заголовков, каждый с новой строки, без нумерации."""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию заголовков для социальных сетей.",
            temperature=0.8,
            max_tokens=200
        )
        
        if result and result.get("success"):
            content = result.get("content", "")
            headlines = [h.strip() for h in content.split('\n') if h.strip() and not h.strip().isdigit()]
            return headlines[:count]
        
        return []
    
    except Exception as e:
        logger.error(f"Ошибка при генерации заголовков: {e}")
        return []


async def generate_cta(text: str, style: str = "friendly") -> str:
    """
    Генерирует призыв к действию (CTA) для поста через AI
    
    Args:
        text: Текст поста
        style: Стиль CTA (friendly, formal, neutral)
    
    Returns:
        Текст призыва к действию
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Создай естественный, ненавязчивый призыв к действию для следующего поста некоммерческой организации.

Текст поста:
{text[:500]}

Стиль: {style}

Требования:
- Естественный и ненавязчивый
- Короткий (1-2 предложения)
- Без пафоса и шаблонов
- Мягкий призыв, не навязчивый

Пример хорошего CTA: "Если хочешь помочь - заходи в гости. Будем рады!"
Пример плохого CTA: "Вместе мы сможем подарить шанс на новую жизнь!"

Ответь только текстом призыва к действию, без дополнительных объяснений."""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по созданию призывов к действию для социальных сетей.",
            temperature=0.7,
            max_tokens=100
        )
        
        if result and result.get("success"):
            cta = result.get("content", "").strip()
            # Убираем кавычки, если они есть
            cta = cta.strip('"').strip("'").strip()
            return cta
        
        return ""
    
    except Exception as e:
        logger.error(f"Ошибка при генерации CTA: {e}")
        return ""


async def suggest_emojis(text: str, count: int = 4) -> List[Dict[str, Any]]:
    """
    Предлагает эмодзи для улучшения восприятия текста через AI
    
    Args:
        text: Текст поста
        count: Количество эмодзи для предложения
    
    Returns:
        Список словарей с эмодзи и местами для вставки
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Проанализируй следующий текст поста и предложи {count} подходящих эмодзи для улучшения восприятия.

Текст:
{text[:500]}

Требования:
- Эмодзи должны быть уместными и релевантными
- Не переборщить - 2-4 эмодзи достаточно
- Эмодзи должны усиливать эмоции и смысл текста
- Подходят для некоммерческой организации

Ответь в формате JSON:
{{
    "emojis": ["эмодзи1", "эмодзи2", "эмодзи3"],
    "suggestions": [
        {{"emoji": "эмодзи", "position": "начало/конец/место", "reason": "причина"}}
    ]
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по использованию эмодзи в контенте для социальных сетей.",
            temperature=0.6,
            max_tokens=200
        )
        
        if result and result.get("success"):
            import json
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group())
                    return data.get("suggestions", [])
            except json.JSONDecodeError:
                pass
        
        return []
    
    except Exception as e:
        logger.error(f"Ошибка при предложении эмодзи: {e}")
        return []


    @staticmethod
    def analyze_sentiment(text: str) -> Dict[str, Any]:
        """
        Анализирует эмоциональную окраску текста
        
        Args:
            text: Текст для анализа
        
        Returns:
            Dict с анализом тональности
        """
        if vader_available:
            try:
                analyzer = SentimentIntensityAnalyzer()
                # VaderSentiment работает лучше с английским, но можно попробовать
                scores = analyzer.polarity_scores(text)
                
                # Определяем тональность
                if scores['compound'] >= 0.05:
                    tonality = "позитивный"
                elif scores['compound'] <= -0.05:
                    tonality = "негативный"
                else:
                    tonality = "нейтральный"
                
                return {
                    "tonality": tonality,
                    "scores": {
                        "positive": round(scores['pos'], 2),
                        "neutral": round(scores['neu'], 2),
                        "negative": round(scores['neg'], 2),
                        "compound": round(scores['compound'], 2)
                    }
                }
            except Exception as e:
                logger.error(f"Ошибка при анализе тональности через VaderSentiment: {e}")
        
        # Если VaderSentiment не доступен, возвращаем базовый результат
        return {
            "tonality": "нейтральный",
            "scores": {
                "positive": 0.0,
                "neutral": 1.0,
                "negative": 0.0,
                "compound": 0.0
            },
            "note": "Детальный анализ требует AI"
        }
    
    @staticmethod
    def check_repetitions(text: str) -> Dict[str, Any]:
        """
        Проверяет текст на повторяющиеся слова и фразы
        
        Args:
            text: Текст для проверки
        
        Returns:
            Dict с найденными повторениями и рекомендациями
        """
        # Разбиваем на слова (убираем знаки препинания)
        words = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]+\b', text.lower())
        word_count = Counter(words)
        
        # Находим часто повторяющиеся слова (более 3 раз)
        repetitions = {word: count for word, count in word_count.items() if count > 3}
        
        # Ищем повторяющиеся фразы (2-3 слова подряд)
        sentences = re.split(r'[.!?]+\s+', text)
        phrase_counts = Counter()
        
        for sentence in sentences:
            words_in_sentence = re.findall(r'\b[а-яА-ЯёЁa-zA-Z]+\b', sentence.lower())
            # Проверяем 2-словные фразы
            for i in range(len(words_in_sentence) - 1):
                phrase = ' '.join(words_in_sentence[i:i+2])
                phrase_counts[phrase] += 1
        
        repeated_phrases = {phrase: count for phrase, count in phrase_counts.items() if count > 2}
        
        return {
            "repeated_words": dict(sorted(repetitions.items(), key=lambda x: x[1], reverse=True)[:10]),
            "repeated_phrases": dict(sorted(repeated_phrases.items(), key=lambda x: x[1], reverse=True)[:5]),
            "suggestions": _generate_repetition_suggestions(repetitions, repeated_phrases)
        }


def _generate_repetition_suggestions(repetitions: Dict[str, int], phrases: Dict[str, int]) -> List[str]:
    """Генерирует рекомендации по устранению повторений"""
    suggestions = []
    
    if repetitions:
        top_word = max(repetitions.items(), key=lambda x: x[1])
        suggestions.append(f"Слово '{top_word[0]}' встречается {top_word[1]} раз. Рассмотрите использование синонимов.")
    
    if phrases:
        top_phrase = max(phrases.items(), key=lambda x: x[1])
        suggestions.append(f"Фраза '{top_phrase[0]}' повторяется {top_phrase[1]} раз. Попробуйте перефразировать.")
    
    if not suggestions:
        suggestions.append("Повторяющихся слов и фраз не обнаружено.")
    
    return suggestions


async def analyze_target_audience(text: str, target_audience: str) -> Dict[str, Any]:
    """
    Анализирует, подходит ли текст для указанной целевой аудитории
    
    Args:
        text: Текст для анализа
        target_audience: Описание целевой аудитории
    
    Returns:
        Dict с результатами анализа
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Проанализируй, подходит ли следующий текст для указанной целевой аудитории.

Текст:
{text[:800]}

Целевая аудитория: {target_audience}

Оцени:
1. Соответствие языка и стиля аудитории
2. Уместность темы для аудитории
3. Понятность текста для аудитории
4. Эмоциональная близость к аудитории

Ответь в формате JSON:
{{
    "fits_audience": true/false,
    "score": 0-10,
    "language_appropriateness": "описание",
    "topic_relevance": "описание",
    "comprehensibility": "описание",
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по маркетингу и работе с целевыми аудиториями.",
            temperature=0.4,
            max_tokens=300
        )
        
        if result and result.get("success"):
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {
            "fits_audience": True,
            "score": 7,
            "recommendations": ["Требуется ручной анализ"]
        }
    
    except Exception as e:
        logger.error(f"Ошибка при анализе целевой аудитории: {e}")
        return {
            "fits_audience": True,
            "score": 7,
            "error": str(e)
        }


async def suggest_seo_improvements(text: str) -> Dict[str, Any]:
    """
    Предлагает улучшения для SEO (если нужно)
    
    Args:
        text: Текст для анализа
    
    Returns:
        Dict с рекомендациями по SEO
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Проанализируй следующий текст поста на SEO-оптимизацию для социальных сетей.

Текст:
{text[:800]}

Оцени:
1. Использование ключевых слов
2. Структуру текста (заголовки, абзацы)
3. Наличие призыва к действию
4. Оптимизацию для поисковых систем

Предложи улучшения (если нужны).

Ответь в формате JSON:
{{
    "needs_seo": true/false,
    "keywords_suggestions": ["ключевое слово 1", "ключевое слово 2"],
    "improvements": ["улучшение 1", "улучшение 2"],
    "score": 0-10
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по SEO и оптимизации контента.",
            temperature=0.3,
            max_tokens=250
        )
        
        if result and result.get("success"):
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {
            "needs_seo": False,
            "keywords_suggestions": [],
            "improvements": [],
            "score": 7
        }
    
    except Exception as e:
        logger.error(f"Ошибка при анализе SEO: {e}")
        return {
            "needs_seo": False,
            "error": str(e)
        }


async def suggest_structure(text: str) -> Dict[str, Any]:
    """
    Предлагает структуру текста (разбивка на абзацы, списки, выделения)
    
    Args:
        text: Текст для анализа
    
    Returns:
        Dict с предложениями по структуре
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        
        prompt = f"""Проанализируй структуру следующего текста и предложи улучшения.

Текст:
{text[:800]}

Предложи:
1. Разбивку на абзацы (если нужно)
2. Использование списков (если уместно)
3. Выделения важных моментов
4. Улучшение читаемости

Ответь в формате JSON:
{{
    "current_structure": "описание текущей структуры",
    "suggested_structure": "описание предложенной структуры",
    "improvements": ["улучшение 1", "улучшение 2"],
    "formatted_text": "текст с улучшенной структурой (Markdown)"
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по структурированию текстов для социальных сетей.",
            temperature=0.4,
            max_tokens=400
        )
        
        if result and result.get("success"):
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        return {
            "current_structure": "Базовая структура",
            "suggested_structure": "С улучшенной разбивкой на абзацы",
            "improvements": ["Добавить абзацы для лучшей читаемости"],
            "formatted_text": text
        }
    
    except Exception as e:
        logger.error(f"Ошибка при предложении структуры: {e}")
        return {
            "error": str(e),
            "formatted_text": text
        }


async def compare_texts(text1: str, text2: str) -> Dict[str, Any]:
    """
    Сравнивает два варианта текста
    
    Args:
        text1: Первый вариант текста
        text2: Второй вариант текста
    
    Returns:
        Dict с сравнением и рекомендациями
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        from bot.services.content.text_processor import text_processor
        
        # Анализируем оба текста
        readability1 = text_processor.calculate_readability(text1)
        readability2 = text_processor.calculate_readability(text2)
        sentiment1 = text_processor.analyze_sentiment(text1)
        sentiment2 = text_processor.analyze_sentiment(text2)
        
        prompt = f"""Сравни два варианта текста поста для некоммерческой организации и определи лучший.

Вариант 1:
{text1[:500]}

Вариант 2:
{text2[:500]}

Сравни:
1. Читаемость и понятность
2. Эмоциональное воздействие
3. Соответствие стилю НКО
4. Уместность призыва к действию
5. Общее качество

Ответь в формате JSON:
{{
    "best_variant": 1 или 2,
    "comparison": {{
        "readability": "какой вариант легче читать",
        "emotional_impact": "какой вариант более эмоционален",
        "style_match": "какой вариант лучше соответствует стилю"
    }},
    "differences": ["различие 1", "различие 2"],
    "recommendations": ["рекомендация 1", "рекомендация 2"]
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по контенту для социальных сетей и анализу текстов.",
            temperature=0.4,
            max_tokens=300
        )
        
        comparison = {
            "readability1": readability1,
            "readability2": readability2,
            "sentiment1": sentiment1,
            "sentiment2": sentiment2
        }
        
        if result and result.get("success"):
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    ai_comparison = json.loads(json_match.group())
                    comparison.update(ai_comparison)
            except json.JSONDecodeError:
                pass
        
        return comparison
    
    except Exception as e:
        logger.error(f"Ошибка при сравнении текстов: {e}")
        return {
            "error": str(e),
            "readability1": {},
            "readability2": {},
            "sentiment1": {},
            "sentiment2": {}
        }


async def check_tonality(text: str, required_tonality: str) -> Dict[str, Any]:
    """
    Проверяет соответствие текста требуемой тональности
    
    Args:
        text: Текст для проверки
        required_tonality: Требуемая тональность (позитивный, нейтральный, серьезный)
    
    Returns:
        Dict с результатами проверки
    """
    try:
        from bot.services.ai.openrouter import openrouter_api
        from bot.services.content.text_processor import text_processor
        
        sentiment = text_processor.analyze_sentiment(text)
        detected_tonality = sentiment.get("tonality", "нейтральный")
        
        prompt = f"""Проверь, соответствует ли следующий текст требуемой тональности.

Текст:
{text[:500]}

Требуемая тональность: {required_tonality}
Определенная тональность: {detected_tonality}

Оцени соответствие и предложи изменения, если нужно.

Ответь в формате JSON:
{{
    "matches": true/false,
    "detected_tonality": "{detected_tonality}",
    "required_tonality": "{required_tonality}",
    "score": 0-10,
    "suggestions": ["предложение 1", "предложение 2"]
}}"""
        
        result = await openrouter_api.generate_text(
            prompt=prompt,
            system_prompt="Ты эксперт по анализу тональности текстов.",
            temperature=0.3,
            max_tokens=200
        )
        
        if result and result.get("success"):
            content = result.get("content", "")
            try:
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        matches = (
            (required_tonality.lower() == "позитивный" and detected_tonality == "позитивный") or
            (required_tonality.lower() == "нейтральный" and detected_tonality == "нейтральный") or
            (required_tonality.lower() == "серьезный" and detected_tonality in ["нейтральный", "негативный"])
        )
        
        return {
            "matches": matches,
            "detected_tonality": detected_tonality,
            "required_tonality": required_tonality,
            "score": 8 if matches else 5,
            "suggestions": [] if matches else [f"Измените тональность с {detected_tonality} на {required_tonality}"]
        }
    
    except Exception as e:
        logger.error(f"Ошибка при проверке тональности: {e}")
        return {
            "matches": True,
            "error": str(e)
        }


# Глобальный экземпляр процессора
text_processor = TextProcessor()

