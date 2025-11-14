"""
Генератор умных хештегов для постов
"""
import logging
import re
from typing import List, Optional, Dict
from bot.services.ai.openrouter import openrouter_api
from bot.database.models import NKOProfile, ActivityType

logger = logging.getLogger(__name__)


class HashtagGenerator:
    """Класс для генерации релевантных хештегов"""
    
    # Популярные хештеги по категориям НКО
    CATEGORY_HASHTAGS: Dict[str, List[str]] = {
        "environmental": [
            "#экология", "#защитаприроды", "#экологическоеобразование",
            "#чистаяпланета", "#зеленоебудущее", "#эко", "#эколайф"
        ],
        "animal_welfare": [
            "#помощьживотным", "#защитаживотных", "#благотворительность",
            "#животные", "#помощькотикам", "#помощьсобакам", "#приют"
        ],
        "humanitarian": [
            "#благотворительность", "#помощьлюдям", "#социальнаяпомощь",
            "#волонтерство", "#добро", "#помощь", "#поддержка"
        ],
        "education": [
            "#образование", "#обучение", "#развитие", "#знания",
            "#обучениедетей", "#образованиебесплатно"
        ],
        "culture": [
            "#культура", "#искусство", "#творчество", "#культурноеразвитие",
            "#театр", "#музыка", "#литература"
        ],
        "health": [
            "#здоровье", "#здоровыйобразжизни", "#медицина",
            "#профилактика", "#здоровье"
        ],
        "social": [
            "#социальнаяпомощь", "#социальнаязащита", "#социальнаяработа",
            "#помощь", "#поддержка", "#волонтерство"
        ]
    }
    
    # Общие популярные хештеги для НКО
    GENERAL_HASHTAGS = [
        "#нко", "#благотворительность", "#волонтерство", "#добро",
        "#помощь", "#социальныепроекты", "#некоммерческиеорганизации"
    ]
    
    async def generate_hashtags(
        self,
        text: str,
        nko_profile: Optional[NKOProfile] = None,
        count: int = 5,
        use_ai: bool = True
    ) -> List[str]:
        """
        Генерирует релевантные хештеги для текста
        
        Args:
            text: Текст поста
            nko_profile: Профиль НКО (для учета специфики)
            count: Количество хештегов для генерации
            use_ai: Использовать AI для генерации (если True) или только правила
        
        Returns:
            Список хештегов
        """
        hashtags = []
        
        # Приоритет: сначала AI генерация (более релевантная), потом категории
        if use_ai:
            ai_hashtags = await self._generate_ai_hashtags(text, nko_profile, count=count)
            hashtags.extend(ai_hashtags)
        
        # Добавляем хештеги из профиля НКО (если их еще не хватает)
        if len(hashtags) < count and nko_profile and nko_profile.activity_types:
            for activity_type in nko_profile.activity_types:
                if activity_type in self.CATEGORY_HASHTAGS:
                    category_tags = [tag for tag in self.CATEGORY_HASHTAGS[activity_type][:2] 
                                   if tag.lower() not in [h.lower() for h in hashtags]]
                    hashtags.extend(category_tags)
                    if len(hashtags) >= count:
                        break
        
        # Убираем дубликаты и лимитируем количество
        unique_hashtags = []
        seen = set()
        for tag in hashtags:
            tag_lower = tag.lower()
            if tag_lower not in seen and len(tag) <= 100:  # Telegram ограничение
                seen.add(tag_lower)
                unique_hashtags.append(tag)
                if len(unique_hashtags) >= count:
                    break
        
        # Если хештегов мало, добавляем общие
        while len(unique_hashtags) < count and len(self.GENERAL_HASHTAGS) > 0:
            for general_tag in self.GENERAL_HASHTAGS:
                if general_tag.lower() not in seen:
                    unique_hashtags.append(general_tag)
                    seen.add(general_tag.lower())
                    break
            else:
                break
        
        return unique_hashtags[:count]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Извлекает ключевые слова из текста
        
        Args:
            text: Текст
        
        Returns:
            Список ключевых слов
        """
        # Удаляем пунктуацию и приводим к нижнему регистру
        text_clean = re.sub(r'[^\w\s]', ' ', text.lower())
        
        # Разбиваем на слова
        words = text_clean.split()
        
        # Удаляем стоп-слова (русские)
        stop_words = {
            'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'над',
            'под', 'за', 'про', 'как', 'что', 'когда', 'где', 'кто',
            'это', 'какой', 'какая', 'какие', 'этот', 'эта', 'эти',
            'быть', 'был', 'была', 'были', 'было', 'есть', 'если',
            'но', 'или', 'а', 'же', 'ли', 'то', 'так', 'тоже', 'уже',
            'чтобы', 'чтобы', 'может', 'можно', 'нужно', 'должен',
            'не', 'нет', 'да', 'во', 'со', 'ко', 'об', 'из', 'к'
        }
        
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Берем топ-10 наиболее частых слов
        from collections import Counter
        word_counts = Counter(keywords)
        top_keywords = [word for word, _ in word_counts.most_common(10)]
        
        return top_keywords
    
    async def _generate_ai_hashtags(
        self,
        text: str,
        nko_profile: Optional[NKOProfile] = None,
        count: int = 3
    ) -> List[str]:
        """
        Генерирует хештеги с помощью AI
        
        Args:
            text: Текст поста
            nko_profile: Профиль НКО
            count: Количество хештегов
        
        Returns:
            Список хештегов
        """
        try:
            # Формируем промпт для генерации хештегов
            context = ""
            if nko_profile:
                if nko_profile.organization_name:
                    context += f"Организация: {nko_profile.organization_name}. "
                if nko_profile.description:
                    context += f"Деятельность: {nko_profile.description}. "
            
            prompt = f"""Проанализируй текст поста и предложи {count} релевантных, популярных хештегов на русском языке.

{context}

Текст поста:
{text[:500]}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Хештеги должны точно соответствовать теме и содержанию поста
2. Используй ПОПУЛЯРНЫЕ хештеги в сфере НКО, благотворительности и социальных сетей
3. Избегай абстрактных слов типа "теперь", "радостное", "событие" - они не информативны
4. Фокус на конкретных темах: #ПриютДляЖивотных, #ПомощьЖивотным, #УсыновлениеСобак и т.п.
5. Хештеги должны быть на русском языке, написаны слитно или через заглавные буквы
6. Каждый хештег начинается с символа #
7. Ответь ТОЛЬКО списком хештегов, каждый с новой строки
8. НЕ добавляй никаких объяснений, только хештеги

Примеры хороших хештегов для поста о приюте собак:
#ПриютДляЖивотных
#ПомощьЖивотным
#УсыновлениеСобак
#ЗащитаЖивотных
#Благотворительность

Примеры ПЛОХИХ хештегов (НЕ используй):
#теперь
#радостное
#событие
#нашем
#эти"""
            
            system_prompt = "Ты эксперт по социальным сетям и маркетингу для некоммерческих организаций."
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=100
            )
            
            if result and result.get("success"):
                content = result.get("content", "")
                # Парсим хештеги из ответа
                hashtags = re.findall(r'#[\wа-яё]+', content, re.IGNORECASE)
                return hashtags[:count]
            
        except Exception as e:
            logger.error(f"Ошибка при AI генерации хештегов: {e}")
        
        return []


# Глобальный экземпляр генератора
hashtag_generator = HashtagGenerator()

