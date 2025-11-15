"""
Сервис для прогнозирования эффективности контента
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.models import ContentHistory
from bot.database.database import get_db
from bot.services.ai.openrouter import openrouter_api

logger = logging.getLogger(__name__)


class PredictionService:
    """Сервис для прогнозирования эффективности контента"""
    
    @staticmethod
    async def predict_reach(
        user_id: int,
        text: str,
        hashtags: List[str],
        style: str
    ) -> Dict[str, any]:
        """
        Прогнозирует охват поста на основе истории
        
        Args:
            user_id: ID пользователя
            text: Текст поста
            hashtags: Список хештегов
            style: Стиль поста
        
        Returns:
            Dict с прогнозом охвата
        """
        try:
            # Анализируем историю пользователя
            with get_db() as db:
                history = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.content_type == "text"
                ).order_by(ContentHistory.generated_at.desc()).limit(50).all()
            
            if not history:
                return {
                    "success": True,
                    "predicted_reach": "средний",
                    "confidence": "низкая",
                    "message": "Недостаточно данных для точного прогноза"
                }
            
            # Анализируем паттерны
            avg_length = sum(len(str(item.content_data.get("text", ""))) for item in history) / len(history)
            current_length = len(text)
            
            # Анализируем хештеги
            avg_hashtags = sum(len(item.content_data.get("hashtags", [])) if isinstance(item.content_data, dict) else 0 for item in history) / len(history)
            current_hashtags = len(hashtags)
            
            # Простой прогноз на основе паттернов
            score = 0
            
            # Длина текста (оптимально 200-400 символов)
            if 200 <= current_length <= 400:
                score += 2
            elif 100 <= current_length <= 600:
                score += 1
            
            # Хештеги (оптимально 3-7)
            if 3 <= current_hashtags <= 7:
                score += 2
            elif 1 <= current_hashtags <= 10:
                score += 1
            
            # Определяем прогноз
            if score >= 3:
                predicted_reach = "высокий"
            elif score >= 2:
                predicted_reach = "средний"
            else:
                predicted_reach = "низкий"
            
            # Используем AI для более точного прогноза
            prompt = f"""Проанализируй следующий пост и спрогнозируй его потенциальный охват в социальных сетях.

Текст поста:
{text[:500]}

Хештеги: {', '.join(hashtags[:10])}
Стиль: {style}

На основе анализа текста, хештегов и стиля, дай прогноз:
1. Потенциальный охват (низкий/средний/высокий)
2. Уверенность в прогнозе (низкая/средняя/высокая)
3. Рекомендации по улучшению (если нужны)

Формат ответа:
Охват: [низкий/средний/высокий]
Уверенность: [низкая/средняя/высокая]
Рекомендации: [краткие рекомендации]"""
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt="Ты эксперт по анализу эффективности контента в социальных сетях.",
                temperature=0.5,
                max_tokens=200
            )
            
            ai_prediction = {}
            if result and result.get("success"):
                ai_text = result.get("content", "")
                # Парсим ответ AI
                for line in ai_text.split('\n'):
                    if 'охват' in line.lower():
                        if 'высокий' in line.lower():
                            ai_prediction['reach'] = 'высокий'
                        elif 'средний' in line.lower():
                            ai_prediction['reach'] = 'средний'
                        else:
                            ai_prediction['reach'] = 'низкий'
                    if 'уверенность' in line.lower():
                        if 'высокая' in line.lower():
                            ai_prediction['confidence'] = 'высокая'
                        elif 'средняя' in line.lower():
                            ai_prediction['confidence'] = 'средняя'
                        else:
                            ai_prediction['confidence'] = 'низкая'
                    if 'рекомендации' in line.lower():
                        ai_prediction['recommendations'] = line.split(':', 1)[1].strip() if ':' in line else ""
            
            # Объединяем результаты
            final_reach = ai_prediction.get('reach', predicted_reach)
            final_confidence = ai_prediction.get('confidence', 'средняя')
            
            return {
                "success": True,
                "predicted_reach": final_reach,
                "confidence": final_confidence,
                "recommendations": ai_prediction.get('recommendations', ''),
                "metrics": {
                    "text_length": current_length,
                    "hashtags_count": current_hashtags,
                    "style": style
                }
            }
        
        except Exception as e:
            logger.exception(f"Ошибка при прогнозировании охвата: {e}")
            return {
                "success": False,
                "error": str(e),
                "predicted_reach": "средний",
                "confidence": "низкая"
            }
    
    @staticmethod
    async def predict_engagement(
        user_id: int,
        content_type: str = "text"
    ) -> Dict[str, any]:
        """
        Прогнозирует вовлеченность на основе истории
        
        Args:
            user_id: ID пользователя
            content_type: Тип контента
        
        Returns:
            Dict с прогнозом вовлеченности
        """
        try:
            with get_db() as db:
                history = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.content_type == content_type
                ).order_by(ContentHistory.generated_at.desc()).limit(30).all()
            
            if not history:
                return {
                    "success": True,
                    "predicted_engagement": "средняя",
                    "message": "Недостаточно данных"
                }
            
            # Анализируем частоту публикаций
            if len(history) >= 2:
                time_diffs = []
                for i in range(1, len(history)):
                    diff = (history[i-1].generated_at - history[i].generated_at).total_seconds() / 3600
                    time_diffs.append(diff)
                
                avg_interval = sum(time_diffs) / len(time_diffs) if time_diffs else 24
                
                # Оптимальный интервал: 12-48 часов
                if 12 <= avg_interval <= 48:
                    engagement = "высокая"
                elif 6 <= avg_interval <= 72:
                    engagement = "средняя"
                else:
                    engagement = "низкая"
            else:
                engagement = "средняя"
            
            return {
                "success": True,
                "predicted_engagement": engagement,
                "avg_interval_hours": avg_interval if len(history) >= 2 else None,
                "recommendations": [
                    "Публикуй контент регулярно (1-2 раза в день)",
                    "Используй разнообразные типы контента",
                    "Экспериментируй со временем публикаций"
                ]
            }
        
        except Exception as e:
            logger.exception(f"Ошибка при прогнозировании вовлеченности: {e}")
            return {
                "success": False,
                "error": str(e),
                "predicted_engagement": "средняя"
            }
    
    @staticmethod
    async def recommend_posting_time(
        user_id: int
    ) -> Dict[str, any]:
        """
        Рекомендует лучшее время для публикаций
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Dict с рекомендациями по времени
        """
        try:
            with get_db() as db:
                history = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id
                ).order_by(ContentHistory.generated_at.desc()).limit(100).all()
            
            if not history:
                return {
                    "success": True,
                    "recommended_times": ["09:00", "14:00", "18:00"],
                    "message": "Рекомендуем стандартные времена публикаций"
                }
            
            # Анализируем время создания контента
            hours = {}
            for item in history:
                hour = item.generated_at.hour
                hours[hour] = hours.get(hour, 0) + 1
            
            # Находим наиболее активные часы
            sorted_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)
            
            # Рекомендуем время на основе активности
            if sorted_hours:
                top_hours = [h for h, _ in sorted_hours[:3]]
                recommended_times = [f"{h:02d}:00" for h in top_hours]
            else:
                recommended_times = ["09:00", "14:00", "18:00"]
            
            return {
                "success": True,
                "recommended_times": recommended_times,
                "analysis": {
                    "most_active_hour": sorted_hours[0][0] if sorted_hours else None,
                    "activity_distribution": hours
                }
            }
        
        except Exception as e:
            logger.exception(f"Ошибка при рекомендации времени: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommended_times": ["09:00", "14:00", "18:00"]
            }


# Глобальный экземпляр
prediction_service = PredictionService()

