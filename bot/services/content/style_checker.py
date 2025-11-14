"""
Проверка соответствия текста стилю НКО
"""
import logging
import re
import json
from typing import Dict, List, Optional, Any
from bot.database.models import NKOProfile
from bot.services.ai.openrouter import openrouter_api

logger = logging.getLogger(__name__)


class StyleChecker:
    """Класс для проверки соответствия текста стилю НКО"""
    
    async def check_style(
        self,
        text: str,
        nko_profile: Optional[NKOProfile] = None
    ) -> Dict[str, Any]:
        """
        Проверяет соответствие текста стилю НКО
        
        Args:
            text: Текст для проверки
            nko_profile: Профиль НКО
        
        Returns:
            Dict с результатами проверки и рекомендациями
        """
        if not nko_profile or not nko_profile.is_complete:
            # Если профиль не заполнен, возвращаем базовую проверку
            return {
                "matches_style": True,
                "recommendations": [],
                "score": 7.0
            }
        
        try:
            # Формируем промпт для проверки стиля
            style_info = f"Стиль НКО: {nko_profile.tone_of_voice or 'нейтральный'}"
            if nko_profile.organization_name:
                style_info += f"\nОрганизация: {nko_profile.organization_name}"
            if nko_profile.description:
                style_info += f"\nОписание деятельности: {nko_profile.description}"
            if nko_profile.target_audience:
                style_info += f"\nЦелевая аудитория: {nko_profile.target_audience}"
            
            prompt = f"""Проанализируй текст поста на соответствие стилю некоммерческой организации.

{style_info}

Текст поста:
{text[:800]}

Проанализируй:
1. Соответствие указанному стилю изложения
2. Уместность для целевой аудитории
3. Эмоциональную окраску текста
4. Наличие призыва к действию (если нужно)
5. Общую тональность

Ответь в формате JSON:
{{
    "matches_style": true/false,
    "score": 0-10,
    "recommendations": ["рекомендация 1", "рекомендация 2"],
    "tone_analysis": "описание тональности",
    "audience_fit": "насколько подходит аудитории"
}}"""
            
            system_prompt = "Ты эксперт по контенту для некоммерческих организаций и маркетингу в соцсетях."
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=300
            )
            
            if result and result.get("success"):
                content = result.get("content", "")
                
                # Пытаемся извлечь JSON из ответа
                import json
                try:
                    # Ищем JSON в ответе
                    json_match = re.search(r'\{.*\}', content, re.DOTALL)
                    if json_match:
                        analysis = json.loads(json_match.group())
                        return analysis
                except json.JSONDecodeError:
                    pass
            
            # Если не удалось распарсить JSON, возвращаем базовый результат
            return {
                "matches_style": True,
                "score": 7.0,
                "recommendations": ["Рекомендуется проверить текст вручную"],
                "tone_analysis": "Не удалось определить автоматически",
                "audience_fit": "Требуется проверка"
            }
        
        except Exception as e:
            logger.error(f"Ошибка при проверке стиля: {e}")
            return {
                "matches_style": True,
                "score": 7.0,
                "recommendations": [],
                "error": str(e)
            }


# Глобальный экземпляр проверщика
style_checker = StyleChecker()

