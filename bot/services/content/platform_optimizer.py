"""
Сервис для оптимизации контента под разные платформы
"""
from typing import Dict, Optional
from enum import Enum


class Platform(str, Enum):
    """Поддерживаемые платформы"""
    TELEGRAM = "telegram"
    VK = "vk"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    OK = "ok"  # Одноклассники


class PlatformConfig:
    """Конфигурация для каждой платформы"""
    
    MAX_LENGTH = {
        Platform.TELEGRAM: 4096,
        Platform.VK: 10000,
        Platform.INSTAGRAM: 2200,
        Platform.FACEBOOK: 63206,
        Platform.TWITTER: 280,
        Platform.OK: 10000
    }
    
    HASHTAG_FORMAT = {
        Platform.TELEGRAM: "#hashtag",
        Platform.VK: "#hashtag",
        Platform.INSTAGRAM: "#hashtag",
        Platform.FACEBOOK: "#hashtag",
        Platform.TWITTER: "#hashtag",
        Platform.OK: "#hashtag"
    }
    
    MAX_HASHTAGS = {
        Platform.TELEGRAM: 10,
        Platform.VK: 10,
        Platform.INSTAGRAM: 30,
        Platform.FACEBOOK: 10,
        Platform.TWITTER: 2,
        Platform.OK: 10
    }
    
    OPTIMAL_LENGTH = {
        Platform.TELEGRAM: 200,
        Platform.VK: 500,
        Platform.INSTAGRAM: 150,
        Platform.FACEBOOK: 250,
        Platform.TWITTER: 100,
        Platform.OK: 500
    }
    
    EMOJI_SUPPORT = {
        Platform.TELEGRAM: True,
        Platform.VK: True,
        Platform.INSTAGRAM: True,
        Platform.FACEBOOK: True,
        Platform.TWITTER: True,
        Platform.OK: True
    }


class PlatformOptimizer:
    """Класс для оптимизации контента под платформы"""
    
    @staticmethod
    def optimize_text(text: str, platform: Platform, nko_profile: Optional[Dict] = None) -> Dict[str, str]:
        """
        Оптимизирует текст под конкретную платформу
        
        Args:
            text: Исходный текст
            platform: Платформа
            nko_profile: Профиль НКО (опционально)
        
        Returns:
            Dict с оптимизированным текстом и метаданными
        """
        config = PlatformConfig()
        
        # Базовые ограничения
        max_length = config.MAX_LENGTH.get(platform, 4096)
        optimal_length = config.OPTIMAL_LENGTH.get(platform, 200)
        max_hashtags = config.MAX_HASHTAGS.get(platform, 10)
        
        # Извлекаем хештеги из текста
        hashtags = []
        words = text.split()
        text_without_hashtags = []
        
        for word in words:
            if word.startswith('#'):
                hashtags.append(word)
            else:
                text_without_hashtags.append(word)
        
        clean_text = ' '.join(text_without_hashtags)
        
        # Оптимизируем длину текста
        if len(clean_text) > optimal_length:
            # Сокращаем текст, сохраняя смысл
            sentences = clean_text.split('. ')
            optimized_text = ""
            for sentence in sentences:
                if len(optimized_text + sentence) <= optimal_length:
                    optimized_text += sentence + ". "
                else:
                    break
            optimized_text = optimized_text.strip()
        else:
            optimized_text = clean_text
        
        # Ограничиваем количество хештегов
        hashtags = hashtags[:max_hashtags]
        
        # Формируем финальный текст
        if hashtags:
            hashtags_str = ' '.join(hashtags)
            final_text = f"{optimized_text}\n\n{hashtags_str}"
        else:
            final_text = optimized_text
        
        # Проверяем общую длину
        if len(final_text) > max_length:
            # Сокращаем еще больше
            final_text = final_text[:max_length - 3] + "..."
        
        return {
            "text": final_text,
            "original_length": len(text),
            "optimized_length": len(final_text),
            "hashtags_count": len(hashtags),
            "platform": platform.value
        }
    
    @staticmethod
    def get_platform_prompt(platform: Platform) -> str:
        """
        Возвращает промпт для генерации контента с учетом платформы
        
        Args:
            platform: Платформа
        
        Returns:
            Промпт для AI
        """
        prompts = {
            Platform.TELEGRAM: (
                "Пост для Telegram. "
                "Оптимальная длина: 150-250 слов. "
                "Можно использовать эмодзи. "
                "Хештеги: до 10 штук в конце."
            ),
            Platform.VK: (
                "Пост для ВКонтакте. "
                "Оптимальная длина: 300-600 слов. "
                "Можно использовать эмодзи. "
                "Хештеги: до 10 штук в конце."
            ),
            Platform.INSTAGRAM: (
                "Пост для Instagram. "
                "Оптимальная длина: 100-200 слов. "
                "Можно использовать эмодзи. "
                "Хештеги: до 30 штук в конце (важно для охвата)."
            ),
            Platform.FACEBOOK: (
                "Пост для Facebook. "
                "Оптимальная длина: 200-300 слов. "
                "Можно использовать эмодзи. "
                "Хештеги: до 10 штук в конце."
            ),
            Platform.TWITTER: (
                "Пост для Twitter/X. "
                "Оптимальная длина: 80-120 слов (максимум 280 символов). "
                "Можно использовать эмодзи. "
                "Хештеги: до 2 штук в конце."
            ),
            Platform.OK: (
                "Пост для Одноклассников. "
                "Оптимальная длина: 300-600 слов. "
                "Можно использовать эмодзи. "
                "Хештеги: до 10 штук в конце."
            )
        }
        
        return prompts.get(platform, prompts[Platform.TELEGRAM])
    
    @staticmethod
    def format_for_platform(text: str, platform: Platform) -> str:
        """
        Форматирует текст для конкретной платформы
        
        Args:
            text: Исходный текст
            platform: Платформа
        
        Returns:
            Отформатированный текст
        """
        result = PlatformOptimizer.optimize_text(text, platform)
        return result["text"]


# Глобальный экземпляр
platform_optimizer = PlatformOptimizer()

