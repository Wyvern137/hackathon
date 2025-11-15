"""
Конфигурация бота
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """Конфигурация приложения"""
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    # OpenRouter API (для текстовой генерации)
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")  # Модель по умолчанию
    
    # Резервные модели OpenRouter (если основная недоступна)
    OPENROUTER_FALLBACK_MODELS: list = [
        "openai/gpt-3.5-turbo",
        "meta-llama/llama-3.2-3b-instruct",
        "google/gemini-flash-1.5",
        "deepseek/deepseek-chat"
    ]
    
    # Генерация изображений (YandexART или GigaChat)
    YANDEX_ART_API_KEY: str = os.getenv("YANDEX_ART_API_KEY", "")
    GIGACHAT_API_KEY: str = os.getenv("GIGACHAT_API_KEY", "")
    IMAGE_GENERATION_ENABLED: bool = os.getenv("IMAGE_GENERATION_ENABLED", "true").lower() == "true"
    IMAGE_GENERATION_PROVIDER: str = os.getenv("IMAGE_GENERATION_PROVIDER", "gigachat")  # gigachat или yandex
    
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///bot.db")
    
    # Окружение
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    # Логирование
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Пути
    BASE_DIR: Path = Path(__file__).parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    IMAGES_DIR: Path = DATA_DIR / "images"
    TEMPLATES_DIR: Path = DATA_DIR / "templates"
    
    # Настройки генерации
    MAX_TEXT_LENGTH: int = 2000  # Максимальная длина текста для генерации
    MAX_IMAGE_SIZE: int = 10 * 1024 * 1024  # 10 MB максимум для изображений
    DEFAULT_TEMPERATURE: float = 0.7  # Температура для текстовой генерации
    DEFAULT_MAX_TOKENS: int = 500  # Максимальное количество токенов в ответе
    
    # Настройки контент-плана
    DEFAULT_POSTS_PER_WEEK: int = 3  # По умолчанию 3 поста в неделю
    MAX_CONTENT_PLAN_DAYS: int = 90  # Максимум 90 дней для контент-плана
    
    # Настройки истории
    MAX_HISTORY_ITEMS: int = 100  # Максимум элементов в истории на пользователя
    
    # Настройки распознавания речи (OpenRouter Whisper)
    OPENROUTER_WHISPER_MODEL: str = os.getenv("OPENROUTER_WHISPER_MODEL", "openai/whisper-1")  # Модель Whisper через OpenRouter
    SPEECH_RECOGNITION_LANGUAGE: str = os.getenv("SPEECH_RECOGNITION_LANGUAGE", "ru")  # Язык распознавания
    
    @classmethod
    def validate(cls) -> bool:
        """Проверяет наличие обязательных переменных окружения"""
        required_vars = [
            "TELEGRAM_BOT_TOKEN",
            "OPENROUTER_API_KEY"
        ]
        
        missing = []
        for var in required_vars:
            value = getattr(cls, var, None)
            if not value:
                missing.append(var)
        
        if missing:
            raise ValueError(
                f"Отсутствуют обязательные переменные окружения: {', '.join(missing)}\n"
                f"Создайте файл .env на основе env.example и заполните необходимые значения."
            )
        
        # Создаем необходимые директории
        cls.IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        cls.TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
        (cls.DATA_DIR / "temp_voice").mkdir(parents=True, exist_ok=True)
        
        return True


# Глобальный экземпляр конфигурации
config = Config()

