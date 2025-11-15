"""
Сервис для генерации изображений через AI
"""
import logging
import aiohttp
import ssl
import re
import uuid
from typing import Optional, Dict, Any, List
from pathlib import Path
from bot.config import config

logger = logging.getLogger(__name__)


class ImageAIService:
    """Сервис для генерации изображений через AI API"""
    
    def __init__(self):
        self.provider = config.IMAGE_GENERATION_PROVIDER
        if self.provider == "gigachat":
            self.api_key = config.GIGACHAT_API_KEY
            # GigaChat API для генерации изображений через chat/completions
            self.api_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            self.files_url = "https://gigachat.devices.sberbank.ru/api/v1/files"
            self.auth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        else:
            self.api_key = config.YANDEX_ART_API_KEY
            self.api_url = None  # TODO: Добавить URL для YandexART
            self.files_url = None
            self.auth_url = None
        
        self.images_dir = config.IMAGES_DIR
        self.enabled = config.IMAGE_GENERATION_ENABLED and bool(self.api_key)
    
    async def generate_image(
        self,
        prompt: str,
        style: str = "realistic",
        aspect_ratio: str = "1:1",
        reference_images: Optional[List[bytes]] = None,
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует изображение по описанию
        
        Args:
            prompt: Текстовое описание изображения
            style: Стиль изображения (realistic, illustration, graphics, photo)
            aspect_ratio: Соотношение сторон (1:1, 16:9, 9:16)
            reference_images: Референсные изображения (опционально)
            user_id: ID пользователя для сохранения файла
        
        Returns:
            Dict с путем к файлу и метаданными или None при ошибке
        """
        if not self.enabled:
            logger.warning("Генерация изображений отключена или API ключ не указан")
            return None
        
        logger.info(f"Генерация изображения через {self.provider}: prompt={prompt[:50]}..., style={style}, aspect_ratio={aspect_ratio}")
        
        if self.provider == "gigachat":
            return await self._generate_gigachat_image(prompt, style, aspect_ratio, user_id)
        elif self.provider == "yandex":
            # TODO: Реализовать YandexART
            logger.warning("YandexART API пока не реализован")
            return None
        else:
            logger.error(f"Неизвестный провайдер генерации изображений: {self.provider}")
            return None
    
    async def _generate_gigachat_image(
        self,
        prompt: str,
        style: str = "realistic",
        aspect_ratio: str = "1:1",
        user_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует изображение через GigaChat API
        
        Args:
            prompt: Описание изображения
            style: Стиль изображения
            aspect_ratio: Соотношение сторон
            user_id: ID пользователя
        
        Returns:
            Dict с путем к файлу и метаданными или None
        """
        try:
            # Получаем токен доступа для GigaChat API
            # API ключ используется для получения токена, а не напрямую
            access_token = await self._get_gigachat_token()
            if not access_token:
                logger.error("Не удалось получить токен доступа GigaChat")
                return {
                    "success": False,
                    "error": "Не удалось получить токен доступа GigaChat. Проверьте правильность API ключа."
                }
            
            logger.info(f"Токен GigaChat получен и готов к использованию (длина: {len(access_token)})")
            
            # Формируем промпт с учетом стиля
            full_prompt = self._format_prompt_with_style(prompt, style)
            
            # GigaChat генерация изображений через chat/completions с "Василий Кандинский"
            # Согласно документации: https://developers.sber.ru/docs/ru/gigachat/guides/images-generation
            payload = {
                "model": "GigaChat",
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты — Василий Кандинский"
                    },
                    {
                        "role": "user",
                        "content": full_prompt
                    }
                ],
                "function_call": "auto"
            }
            
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # SSL контекст для HTTPS запросов
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Отправляем запрос на генерацию изображения
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)  # 2 минуты для генерации изображения
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # GigaChat возвращает в content строку с <img src="file_id" fuse="true"/>
                        # Нужно извлечь file_id и скачать изображение
                        if 'choices' in result and len(result['choices']) > 0:
                            content = result['choices'][0].get('message', {}).get('content', '')
                            
                            # Ищем file_id в формате <img src="file_id" .../>
                            img_match = re.search(r'<img[^>]*src=["\']([^"\']+)["\']', content)
                            
                            if img_match:
                                file_id = img_match.group(1)
                                logger.info(f"Найден file_id изображения: {file_id}")
                                
                                # Скачиваем изображение по file_id
                                download_url = f"{self.files_url}/{file_id}/content"
                                download_headers = {
                                    "Authorization": f"Bearer {access_token}",
                                    "Accept": "application/jpg"  # или image/png, image/jpeg
                                }
                                
                                async with session.get(
                                    download_url,
                                    headers=download_headers,
                                    timeout=aiohttp.ClientTimeout(total=60)
                                ) as img_response:
                                    if img_response.status == 200:
                                        image_bytes = await img_response.read()
                                        
                                        # Сохраняем изображение
                                        if user_id:
                                            file_path = await self.save_image(image_bytes, user_id)
                                            if file_path:
                                                return {
                                                    "success": True,
                                                    "file_path": str(file_path),
                                                    "prompt": prompt,
                                                    "style": style,
                                                    "aspect_ratio": aspect_ratio,
                                                    "provider": "gigachat",
                                                    "file_id": file_id
                                                }
                                    else:
                                        error_text = await img_response.text()
                                        logger.error(f"Ошибка скачивания изображения ({img_response.status}): {error_text[:200]}")
                            else:
                                logger.warning(f"Не удалось найти file_id в ответе: {content[:200]}")
                                return None
                        else:
                            logger.warning(f"Нет choices в ответе GigaChat: {result}")
                            return None
                    
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка GigaChat API ({response.status}): {error_text[:200]}")
                        return None
        
        except Exception as e:
            logger.exception(f"Ошибка при генерации изображения через GigaChat: {e}")
            return None
    
    async def _get_gigachat_token(self) -> Optional[str]:
        """
        Получает токен доступа для GigaChat API
        
        Returns:
            Токен доступа или None
        """
        try:
            # GigaChat использует OAuth 2.0 для аутентификации
            # API ключ (client_id) используется для получения токена
            # Генерируем уникальный идентификатор запроса (RqUID)
            rquid = str(uuid.uuid4())
            
            # Для получения токена GigaChat нужно использовать:
            # - Authorization: Bearer {API_KEY} (API ключ используется как Bearer токен)
            # - RqUID: уникальный идентификатор запроса
            # - Content-Type: application/x-www-form-urlencoded
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "RqUID": rquid,
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            # Параметры запроса в формате application/x-www-form-urlencoded
            # scope указывает область доступа для GigaChat API
            data = {
                "scope": "GIGACHAT_API_PERS"
            }
            
            # SSL контекст
            ssl_context_local = ssl.create_default_context()
            ssl_context_local.check_hostname = False
            ssl_context_local.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context_local)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.post(
                    self.auth_url,
                    headers=headers,
                    data=data,  # aiohttp автоматически конвертирует dict в form-urlencoded
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        access_token = result.get('access_token')
                        if access_token:
                            logger.info(f"Токен GigaChat успешно получен (длина: {len(access_token)})")
                        return access_token
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения токена GigaChat ({response.status}): {error_text}")
                        return None
        
        except Exception as e:
            logger.exception(f"Ошибка при получении токена GigaChat: {e}")
            return None
    
    def _format_prompt_with_style(self, prompt: str, style: str) -> str:
        """
        Форматирует промпт с учетом стиля
        
        Args:
            prompt: Исходный промпт
            style: Стиль изображения
        
        Returns:
            Отформатированный промпт
        """
        style_descriptions = {
            "realistic": "фотореалистичное изображение",
            "illustration": "иллюстрация в художественном стиле",
            "graphics": "графический дизайн",
            "photo": "фотография"
        }
        
        style_desc = style_descriptions.get(style, "изображение")
        return f"{style_desc}, {prompt}"
    
    def _get_size_from_aspect_ratio(self, aspect_ratio: str) -> str:
        """
        Преобразует соотношение сторон в размер для API
        
        Args:
            aspect_ratio: Соотношение сторон (1:1, 16:9, 9:16)
        
        Returns:
            Размер в формате "1024x1024" или аналогичный
        """
        size_map = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792"
        }
        return size_map.get(aspect_ratio, "1024x1024")
    
    async def save_image(self, image_data: bytes, user_id: int, filename: Optional[str] = None) -> Optional[Path]:
        """
        Сохраняет сгенерированное изображение на диск
        
        Args:
            image_data: Байты изображения
            user_id: ID пользователя
            filename: Имя файла (опционально)
        
        Returns:
            Path к сохраненному файлу или None
        """
        try:
            user_dir = self.images_dir / str(user_id)
            user_dir.mkdir(parents=True, exist_ok=True)
            
            if filename is None:
                from datetime import datetime
                filename = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            file_path = user_dir / filename
            
            with open(file_path, "wb") as f:
                f.write(image_data)
            
            logger.info(f"Изображение сохранено: {file_path}")
            return file_path
        
        except Exception as e:
            logger.error(f"Ошибка при сохранении изображения: {e}")
            return None


    async def generate_image_variations(
        self,
        prompt: str,
        count: int = 3,
        style: str = "realistic",
        aspect_ratio: str = "1:1",
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует серию вариантов одного изображения
        
        Args:
            prompt: Описание изображения
            count: Количество вариантов (3-5)
            style: Стиль изображения
            aspect_ratio: Соотношение сторон
            user_id: ID пользователя
        
        Returns:
            Список словарей с путями к изображениям
        """
        count = min(max(count, 3), 5)  # Ограничиваем от 3 до 5
        variations = []
        
        # Варианты промпта для разнообразия
        prompt_variations = [
            prompt,
            f"{prompt}, более яркий вариант",
            f"{prompt}, более спокойный вариант",
            f"{prompt}, другой ракурс",
            f"{prompt}, другой стиль"
        ]
        
        for i in range(count):
            variant_prompt = prompt_variations[i] if i < len(prompt_variations) else prompt
            
            result = await self.generate_image(
                prompt=variant_prompt,
                style=style,
                aspect_ratio=aspect_ratio,
                user_id=user_id
            )
            
            if result and result.get("success"):
                variations.append({
                    "variant_number": i + 1,
                    "file_path": result.get("file_path"),
                    "prompt": variant_prompt
                })
        
        return variations
    
    async def batch_generate_images(
        self,
        prompts: List[str],
        style: str = "realistic",
        aspect_ratio: str = "1:1",
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Генерирует серию изображений для контент-плана
        
        Args:
            prompts: Список описаний изображений
            style: Стиль изображений
            aspect_ratio: Соотношение сторон
            user_id: ID пользователя
        
        Returns:
            Список словарей с результатами генерации
        """
        results = []
        
        for i, prompt in enumerate(prompts, 1):
            logger.info(f"Генерация изображения {i}/{len(prompts)}: {prompt[:50]}...")
            
            result = await self.generate_image(
                prompt=prompt,
                style=style,
                aspect_ratio=aspect_ratio,
                user_id=user_id
            )
            
            if result:
                results.append({
                    "prompt_index": i,
                    "prompt": prompt,
                    **result
                })
        
        return results


# Глобальный экземпляр сервиса
image_ai_service = ImageAIService()

