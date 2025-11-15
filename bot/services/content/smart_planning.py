"""
Сервис для умного планирования контента
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, date
from bot.database.models import ContentHistory, ContentPlan
from bot.database.database import get_db
from bot.services.ai.openrouter import openrouter_api

logger = logging.getLogger(__name__)


class SmartPlanningService:
    """Сервис для умного планирования контента"""
    
    @staticmethod
    async def analyze_best_posting_times(user_id: int) -> Dict[str, any]:
        """
        Анализирует лучшее время для публикаций на основе истории
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Dict с рекомендациями по времени публикаций
        """
        try:
            with get_db() as db:
                # Получаем историю публикаций за последние 30 дней
                month_ago = datetime.now() - timedelta(days=30)
                history = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.generated_at >= month_ago
                ).all()
            
            if not history:
                return {
                    "success": True,
                    "recommended_times": ["09:00", "14:00", "18:00"],
                    "message": "Недостаточно данных для анализа. Рекомендуем стандартные времена: 09:00, 14:00, 18:00"
                }
            
            # Анализируем время создания контента
            hours = {}
            for item in history:
                hour = item.generated_at.hour
                hours[hour] = hours.get(hour, 0) + 1
            
            # Находим наиболее активные часы
            sorted_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)
            recommended_times = [f"{h:02d}:00" for h, _ in sorted_hours[:3]]
            
            return {
                "success": True,
                "recommended_times": recommended_times,
                "analysis": {
                    "total_posts": len(history),
                    "most_active_hour": sorted_hours[0][0] if sorted_hours else None,
                    "activity_by_hour": hours
                }
            }
        
        except Exception as e:
            logger.exception(f"Ошибка при анализе времени публикаций: {e}")
            return {
                "success": False,
                "error": str(e),
                "recommended_times": ["09:00", "14:00", "18:00"]
            }
    
    @staticmethod
    async def balance_content_types(
        content_types: List[str],
        count: int,
        user_history: Optional[List[Dict]] = None
    ) -> List[str]:
        """
        Балансирует типы контента для равномерного распределения
        
        Args:
            content_types: Список типов контента
            count: Количество постов
            user_history: История пользователя для анализа предпочтений
        
        Returns:
            Сбалансированный список типов контента
        """
        if not content_types:
            # Стандартные типы, если не указаны
            content_types = ["новости", "отчет", "анонс", "благодарность", "образование"]
        
        balanced = []
        types_count = len(content_types)
        
        # Если есть история, учитываем предпочтения
        if user_history:
            # Анализируем популярные типы
            type_usage = {}
            for item in user_history:
                content_data = item.get('content_data', {})
                content_type = content_data.get('type', 'новости')
                type_usage[content_type] = type_usage.get(content_type, 0) + 1
            
            # Взвешиваем типы
            weighted_types = []
            for ctype in content_types:
                weight = type_usage.get(ctype, 1)
                weighted_types.extend([ctype] * weight)
            
            # Распределяем взвешенные типы
            for i in range(count):
                if weighted_types:
                    balanced.append(weighted_types[i % len(weighted_types)])
                else:
                    balanced.append(content_types[i % types_count])
        else:
            # Равномерное распределение
            for i in range(count):
                balanced.append(content_types[i % types_count])
        
        return balanced
    
    @staticmethod
    async def auto_generate_plan_content(
        plan_id: int,
        user_id: int,
        nko_profile: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Автоматически генерирует контент для всех дат в плане
        
        Args:
            plan_id: ID контент-плана
            user_id: ID пользователя
            nko_profile: Профиль НКО
        
        Returns:
            Dict с результатами генерации
        """
        try:
            with get_db() as db:
                plan = db.query(ContentPlan).filter(
                    ContentPlan.id == plan_id,
                    ContentPlan.user_id == user_id
                ).first()
                
                if not plan:
                    return {"success": False, "error": "План не найден"}
                
                schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
                dates = schedule.get("dates", [])
                topics = schedule.get("topics", "любые")
                
                if not dates:
                    return {"success": False, "error": "В плане нет дат"}
            
            generated_posts = []
            
            # Генерируем пост для каждой даты
            for i, date_str in enumerate(dates, 1):
                try:
                    post_date = datetime.fromisoformat(date_str).date() if isinstance(date_str, str) else date_str
                    
                    # Формируем тему поста
                    topic = topics if isinstance(topics, str) else topics[i % len(topics)] if topics else "Пост для НКО"
                    
                    # Генерируем пост
                    nko_info = ""
                    if nko_profile:
                        if nko_profile.get('organization_name'):
                            nko_info += f"Организация: {nko_profile['organization_name']}. "
                        if nko_profile.get('description'):
                            nko_info += f"Деятельность: {nko_profile['description'][:200]}. "
                    
                    prompt = f"""Создай пост для некоммерческой организации на тему: {topic}
                    
{nko_info}

Дата публикации: {post_date.strftime('%d.%m.%Y')}

Требования:
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО (разделяй пустой строкой)
- 80-120 слов
- Одна тема
- Естественные переходы
- Уместные эмоции
- Простота языка

Создай готовый пост с хештегами."""
                    
                    result = await openrouter_api.generate_text(
                        prompt=prompt,
                        system_prompt="Ты эксперт по созданию контента для некоммерческих организаций.",
                        temperature=0.8,
                        max_tokens=300
                    )
                    
                    if result and result.get("success"):
                        text = result.get("content", "")
                        generated_posts.append({
                            "date": post_date.isoformat(),
                            "topic": topic,
                            "text": text,
                            "success": True
                        })
                    
                    # Небольшая задержка между генерациями
                    import asyncio
                    await asyncio.sleep(1)
                
                except Exception as e:
                    logger.error(f"Ошибка при генерации текста для даты {date_str}: {e}")
                    generated_posts.append({
                        "date": date_str,
                        "topic": topic,
                        "text": None,
                        "success": False,
                        "error": str(e)
                    })
                    continue
            
            return {
                "success": True,
                "generated_count": len([p for p in generated_posts if p.get("success")]),
                "total_count": len(generated_posts),
                "posts": generated_posts
            }
        
        except Exception as e:
            logger.exception(f"Ошибка при автогенерации контента: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def analyze_plan_effectiveness(
        plan_id: int,
        user_id: int
    ) -> Dict[str, any]:
        """
        Анализирует эффективность контент-плана
        
        Args:
            plan_id: ID контент-плана
            user_id: ID пользователя
        
        Returns:
            Dict с анализом эффективности
        """
        try:
            with get_db() as db:
                plan = db.query(ContentPlan).filter(
                    ContentPlan.id == plan_id,
                    ContentPlan.user_id == user_id
                ).first()
                
                if not plan:
                    return {"success": False, "error": "План не найден"}
                
                schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
                dates = schedule.get("dates", [])
                
                # Подсчитываем выполненные посты
                plan_start = plan.start_date
                plan_end = plan.end_date
                
                completed = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.content_type == "text",
                    ContentHistory.generated_at >= datetime.combine(plan_start, datetime.min.time()),
                    ContentHistory.generated_at <= datetime.combine(plan_end, datetime.min.time()) + timedelta(days=1)
                ).count()
                
                total_posts = len(dates) if dates else 0
                completion_percentage = (completed / total_posts * 100) if total_posts > 0 else 0
                
                # Анализ разнообразия контента
                content_types = {}
                posts = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.content_type == "text",
                    ContentHistory.generated_at >= datetime.combine(plan_start, datetime.min.time()),
                    ContentHistory.generated_at <= datetime.combine(plan_end, datetime.min.time()) + timedelta(days=1)
                ).all()
                
                for post in posts:
                    content_data = post.content_data if isinstance(post.content_data, dict) else {}
                    post_type = content_data.get('type', 'новости')
                    content_types[post_type] = content_types.get(post_type, 0) + 1
                
                # Рекомендации
                recommendations = []
                if completion_percentage < 50:
                    recommendations.append("💡 Рекомендуем увеличить частоту публикаций для лучшего охвата")
                if len(content_types) < 3:
                    recommendations.append("💡 Попробуй разнообразить типы контента (новости, отчеты, анонсы)")
                if completion_percentage > 80:
                    recommendations.append("⭐ Отличная работа! План выполняется успешно")
                
                return {
                    "success": True,
                    "plan_id": plan_id,
                    "total_posts": total_posts,
                    "completed_posts": completed,
                    "remaining_posts": total_posts - completed,
                    "completion_percentage": round(completion_percentage, 1),
                    "content_diversity": {
                        "types_count": len(content_types),
                        "types_distribution": content_types
                    },
                    "recommendations": recommendations
                }
        
        except Exception as e:
            logger.exception(f"Ошибка при анализе эффективности плана: {e}")
            return {"success": False, "error": str(e)}


# Глобальный экземпляр
smart_planning_service = SmartPlanningService()

