"""
Интеграция с OpenRouter AI API для текстовой генерации
"""
import logging
import aiohttp
import ssl
from typing import Optional, List, Dict, Any
from bot.config import config

logger = logging.getLogger(__name__)

# Создаем SSL контекст, который позволяет работать на macOS с проблемами сертификатов
# На macOS часто проблемы с SSL сертификатами Python
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE


class OpenRouterAPI:
    """Класс для работы с OpenRouter AI API"""
    
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.api_url = config.OPENROUTER_API_URL
        self.default_model = config.OPENROUTER_MODEL
        self.fallback_models = config.OPENROUTER_FALLBACK_MODELS
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/hackathon-nko-bot",
            "X-Title": "Hackathon NKO Bot"
        }
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = None,
        max_tokens: int = None,
        use_fallback: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует текст используя OpenRouter API
        
        Args:
            prompt: Текст запроса для генерации
            system_prompt: Системный промпт (опционально)
            model: ID модели (если не указан, используется модель по умолчанию)
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
            use_fallback: Использовать резервные модели при ошибке
        
        Returns:
            Dict с результатом генерации или None при ошибке
        """
        model = model or self.default_model
        temperature = temperature if temperature is not None else config.DEFAULT_TEMPERATURE
        max_tokens = max_tokens or config.DEFAULT_MAX_TOKENS
        
        # Формируем сообщения
        messages = []
        if system_prompt:
            messages.append({
                "role": "system",
                "content": system_prompt
            })
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Пробуем основную модель
        result = await self._make_request(payload, model)
        
        # Если не получилось и включен fallback, пробуем резервные модели
        if result is None and use_fallback:
            for fallback_model in self.fallback_models:
                if fallback_model == model:
                    continue  # Пропускаем, если это та же модель
                
                logger.info(f"Пробую резервную модель: {fallback_model}")
                payload["model"] = fallback_model
                result = await self._make_request(payload, fallback_model)
                if result is not None:
                    result["model_used"] = fallback_model
                    break
        
        return result
    
    async def _make_request(
        self,
        payload: Dict[str, Any],
        model: str
    ) -> Optional[Dict[str, Any]]:
        """
        Выполняет HTTP запрос к OpenRouter API
        
        Args:
            payload: Данные для запроса
            model: ID модели (для логирования)
        
        Returns:
            Dict с результатом или None при ошибке
        """
        try:
            # Создаем connector с SSL контекстом
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        if 'choices' in result and len(result['choices']) > 0:
                            content = result['choices'][0]['message']['content']
                            
                            return {
                                "success": True,
                                "content": content,
                                "model": result.get('model', model),
                                "usage": result.get('usage', {}),
                                "full_response": result
                            }
                        else:
                            logger.warning(f"Нет ответа в результате для модели {model}")
                            return None
                    
                    elif response.status == 401:
                        logger.error(f"Ошибка авторизации OpenRouter API (401)")
                        error_text = await response.text()
                        logger.error(f"Детали: {error_text[:200]}")
                        return None
                    
                    elif response.status == 402:
                        logger.error(f"Недостаточно средств на балансе OpenRouter (402)")
                        logger.error("Проверьте баланс на https://openrouter.ai/")
                        return None
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка OpenRouter API ({response.status}): {error_text[:200]}")
                        return None
        
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка подключения к OpenRouter API: {e}")
            return None
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при запросе к OpenRouter API: {e}")
            return None
    
    async def get_available_models(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Получает список доступных моделей
        
        Args:
            limit: Максимальное количество моделей для возврата
        
        Returns:
            Список доступных моделей
        """
        try:
            # Создаем connector с SSL контекстом
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                async with session.get(
                    "https://openrouter.ai/api/v1/models",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        if 'data' in models_data:
                            return models_data['data'][:limit]
                    return []
        except Exception as e:
            logger.error(f"Ошибка при получении списка моделей: {e}")
            return []


    async def generate_text_variants(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        count: int = 3,
        model: Optional[str] = None,
        temperature: float = 0.8,
        max_tokens: int = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует несколько вариантов одного текста
        
        Args:
            prompt: Текст запроса для генерации
            system_prompt: Системный промпт (опционально)
            count: Количество вариантов (3-5)
            model: ID модели (если не указан, используется модель по умолчанию)
            temperature: Температура генерации (0.0-1.0)
            max_tokens: Максимальное количество токенов в ответе
        
        Returns:
            Список словарей с вариантами текста
        """
        count = min(max(count, 3), 5)  # Ограничиваем от 3 до 5
        max_tokens = max_tokens or config.DEFAULT_MAX_TOKENS
        
        variants = []
        
        # Генерируем варианты с разными подходами
        approaches = [
            "Создай более эмоциональный вариант",
            "Создай более информативный вариант",
            "Создай более дружелюбный вариант",
            "Создай более профессиональный вариант",
            "Создай более креативный вариант"
        ]
        
        for i in range(count):
            approach = approaches[i] if i < len(approaches) else f"Создай вариант {i+1}"
            
            variant_prompt = f"""{approach} следующего текста поста.

Исходный запрос:
{prompt}

ТРЕБОВАНИЯ К ВАРИАНТУ:
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна тема
- Естественные переходы
- Уместные эмоции
- Простота языка

Создай уникальный вариант текста с тем же смыслом, но другим подходом."""
            
            result = await self.generate_text(
                prompt=variant_prompt,
                system_prompt=system_prompt or "Ты эксперт по созданию контента для некоммерческих организаций.",
                model=model,
                temperature=temperature + (i * 0.1),  # Немного меняем температуру для разнообразия
                max_tokens=max_tokens,
                use_fallback=True
            )
            
            if result and result.get("success"):
                variants.append({
                    "variant_number": i + 1,
                    "text": result.get("content", ""),
                    "approach": approach,
                    "model": result.get("model_used", model or self.default_model)
                })
        
        return variants


# Глобальный экземпляр API
openrouter_api = OpenRouterAPI()

