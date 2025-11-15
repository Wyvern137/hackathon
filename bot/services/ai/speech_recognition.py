"""
Сервис распознавания речи через OpenRouter Whisper API
"""
import logging
import aiohttp
import ssl
from pathlib import Path
from typing import Optional, Dict, Any
from bot.config import config
from bot.services.ai.openrouter import openrouter_api

logger = logging.getLogger(__name__)

# Создаем SSL контекст
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class SpeechRecognitionService:
    """Сервис для распознавания речи через OpenRouter Whisper"""
    
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.whisper_model = getattr(config, 'OPENROUTER_WHISPER_MODEL', 'openai/whisper-1')
        self.api_base = "https://openrouter.ai/api/v1"
        
    async def transcribe_voice_file(
        self,
        file_path: str,
        language: str = "ru"
    ) -> Optional[str]:
        """
        Распознает речь из аудиофайла через OpenRouter Whisper API
        
        Args:
            file_path: Путь к аудиофайлу
            language: Язык распознавания (ru, en, etc.)
        
        Returns:
            Распознанный текст или None при ошибке
        """
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"Файл не найден: {file_path}")
                return None
            
            # Проверяем размер файла (Whisper поддерживает до 25MB)
            file_size = file_path_obj.stat().st_size
            if file_size > 25 * 1024 * 1024:
                logger.error(f"Файл слишком большой: {file_size} bytes")
                return None
            
            # Открываем файл и отправляем на распознавание
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": "https://github.com/hackathon-nko-bot",
                    "X-Title": "Hackathon NKO Bot"
                }
                
                # Открываем файл для чтения
                with open(file_path, 'rb') as audio_file:
                    # Формируем multipart/form-data запрос
                    data = aiohttp.FormData()
                    data.add_field('file', audio_file, filename=file_path_obj.name)
                    data.add_field('model', self.whisper_model)
                    if language:
                        data.add_field('language', language)
                    
                    # Отправляем запрос к OpenRouter Whisper API
                    async with session.post(
                        f"{self.api_base}/audio/transcriptions",
                        headers=headers,
                        data=data,
                        timeout=aiohttp.ClientTimeout(total=120)  # 2 минуты для больших файлов
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            text = result.get('text', '')
                            logger.info(f"Распознано {len(text)} символов")
                            return text
                        else:
                            error_text = await response.text()
                            logger.error(f"Ошибка распознавания речи ({response.status}): {error_text[:200]}")
                            return None
                            
        except Exception as e:
            logger.exception(f"Ошибка при распознавании речи: {e}")
            return None
    
    async def transcribe_voice_message(
        self,
        voice_file_id: str,
        bot
    ) -> Optional[str]:
        """
        Распознает речь из Telegram voice message
        
        Args:
            voice_file_id: ID голосового файла в Telegram
            bot: Экземпляр Telegram бота
        
        Returns:
            Распознанный текст или None при ошибке
        """
        try:
            # Получаем информацию о файле
            voice_file = await bot.get_file(voice_file_id)
            
            # Создаем временную директорию для сохранения файла
            temp_dir = config.DATA_DIR / "temp_voice"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Путь для сохранения файла
            temp_file_path = temp_dir / f"{voice_file_id}.ogg"
            
            # Скачиваем файл
            await voice_file.download_to_drive(temp_file_path)
            logger.info(f"Голосовое сообщение скачано: {temp_file_path}")
            
            # Распознаем речь
            text = await self.transcribe_voice_file(str(temp_file_path), language="ru")
            
            # Удаляем временный файл
            try:
                temp_file_path.unlink()
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
            
            return text
            
        except Exception as e:
            logger.exception(f"Ошибка при обработке голосового сообщения: {e}")
            return None
    
    async def detect_intent(
        self,
        text: str
    ) -> Dict[str, Any]:
        """
        Определяет намерение пользователя из текста
        
        Args:
            text: Распознанный текст
        
        Returns:
            Словарь с информацией о намерении
        """
        try:
            prompt = f"""Определи намерение пользователя из следующего текста: "{text}"

Варианты намерений:
- text_generation: пользователь хочет создать текст/пост
- image_generation: пользователь хочет создать изображение
- other: другое намерение

Ответь ТОЛЬКО одним словом: text_generation, image_generation или other."""
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt="Ты помощник для определения намерений пользователей. Отвечай только одним словом.",
                temperature=0.3,
                max_tokens=10
            )
            
            if result and result.get("success"):
                intent_text = result.get("content", "").strip().lower()
                
                # Определяем намерение
                if "text_generation" in intent_text or "text" in intent_text:
                    return {
                        "intent": "text_generation",
                        "confidence": "high" if "text_generation" in intent_text else "medium"
                    }
                elif "image_generation" in intent_text or "image" in intent_text or "картинк" in text.lower() or "изображен" in text.lower():
                    return {
                        "intent": "image_generation",
                        "confidence": "high" if "image_generation" in intent_text else "medium"
                    }
                else:
                    return {
                        "intent": "other",
                        "confidence": "low"
                    }
            
            # Fallback: простой анализ по ключевым словам
            text_lower = text.lower()
            if any(word in text_lower for word in ["текст", "пост", "напиши", "создай текст", "сгенерируй текст"]):
                return {"intent": "text_generation", "confidence": "medium"}
            elif any(word in text_lower for word in ["изображение", "картинка", "создай изображение", "сгенерируй изображение", "нарисуй"]):
                return {"intent": "image_generation", "confidence": "medium"}
            else:
                return {"intent": "other", "confidence": "low"}
                
        except Exception as e:
            logger.exception(f"Ошибка при определении намерения: {e}")
            return {"intent": "other", "confidence": "low"}
    
    def extract_style_from_text(self, text: str) -> Optional[str]:
        """
        Извлекает указание стиля из текста
        
        Args:
            text: Текст для анализа
        
        Returns:
            Название стиля или None если не найдено
        """
        text_lower = text.lower()
        
        # Словарь соответствий
        style_keywords = {
            "разговорный": "разговорный",
            "conversational": "разговорный",
            "официальный": "официально-деловой",
            "formal": "официально-деловой",
            "деловой": "официально-деловой",
            "художественный": "художественный",
            "artistic": "художественный",
            "нейтральный": "нейтральный",
            "neutral": "нейтральный",
            "дружелюбный": "дружелюбный",
            "friendly": "дружелюбный"
        }
        
        for keyword, style in style_keywords.items():
            if keyword in text_lower:
                return style
        
        return None


# Глобальный экземпляр сервиса
speech_recognition_service = SpeechRecognitionService()


