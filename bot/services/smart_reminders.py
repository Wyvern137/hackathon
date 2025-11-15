"""
Сервис умных напоминаний
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from bot.database.models import ContentPlan, ContentHistory, NotificationSettings
from bot.database.database import get_db
from bot.services.scheduler import scheduler
from bot.services.ai.openrouter import openrouter_api

logger = logging.getLogger(__name__)


class SmartReminderService:
    """Сервис для умных напоминаний"""
    
    @staticmethod
    async def schedule_adaptive_reminder(
        user_id: int,
        plan_id: int,
        scheduled_time: datetime,
        content_plan: ContentPlan
    ):
        """
        Планирует адаптивное напоминание с учетом истории пользователя
        
        Args:
            user_id: ID пользователя
            plan_id: ID контент-плана
            scheduled_time: Запланированное время публикации
            content_plan: Объект контент-плана
        """
        try:
            # Анализируем историю пользователя
            with get_db() as db:
                # Получаем последние публикации
                recent_posts = db.query(ContentHistory).filter(
                    ContentHistory.user_id == user_id,
                    ContentHistory.generated_at >= datetime.now() - timedelta(days=30)
                ).order_by(ContentHistory.generated_at.desc()).limit(10).all()
            
            # Определяем, часто ли пользователь опаздывает
            late_count = 0
            for post in recent_posts:
                # Проверяем, был ли пост создан позже запланированного времени
                # (упрощенная логика)
                if post.generated_at.hour > 18:  # После 18:00 считается поздним
                    late_count += 1
            
            # Если пользователь часто опаздывает, напоминаем раньше
            if late_count >= 3:
                reminder_offset = timedelta(hours=2)  # Напоминаем за 2 часа
            else:
                reminder_offset = timedelta(hours=1)  # Напоминаем за 1 час
            
            reminder_time = scheduled_time - reminder_offset
            
            # Планируем напоминание
            from bot.services.scheduler import send_reminder
            
            scheduler.add_job(
                send_reminder,
                'date',
                run_date=reminder_time,
                args=[user_id, plan_id, content_plan],
                id=f"reminder_{user_id}_{plan_id}_{scheduled_time.timestamp()}",
                replace_existing=True
            )
            
            logger.info(f"Адаптивное напоминание запланировано для пользователя {user_id} на {reminder_time}")
        
        except Exception as e:
            logger.exception(f"Ошибка при планировании адаптивного напоминания: {e}")
    
    @staticmethod
    async def suggest_content_for_event(
        user_id: int,
        event_date: datetime,
        event_name: str
    ) -> Optional[Dict]:
        """
        Предлагает контент на основе события
        
        Args:
            user_id: ID пользователя
            event_date: Дата события
            event_name: Название события
        
        Returns:
            Dict с предложенным контентом или None
        """
        try:
            # Получаем профиль НКО
            from bot.database.models import NKOProfile
            with get_db() as db:
                profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            
            nko_info = ""
            if profile:
                if profile.organization_name:
                    nko_info += f"Организация: {profile.organization_name}. "
                if profile.description:
                    nko_info += f"Деятельность: {profile.description[:200]}. "
            
            # Генерируем предложение контента
            prompt = f"""Создай идею поста для некоммерческой организации на основе события.

Событие: {event_name}
Дата: {event_date.strftime('%d.%m.%Y')}

{nko_info}

Создай:
1. Краткое описание идеи поста (1-2 предложения)
2. Предлагаемый стиль
3. Рекомендуемые хештеги (3-5 штук)

Формат ответа:
Идея: [описание]
Стиль: [стиль]
Хештеги: [хештеги через запятую]"""
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt="Ты эксперт по созданию контента для некоммерческих организаций.",
                temperature=0.7,
                max_tokens=200
            )
            
            if result and result.get("success"):
                content = result.get("content", "")
                
                # Парсим ответ
                suggestion = {
                    "event_name": event_name,
                    "event_date": event_date.isoformat(),
                    "suggestion": content,
                    "generated_at": datetime.now().isoformat()
                }
                
                return suggestion
            
            return None
        
        except Exception as e:
            logger.exception(f"Ошибка при предложении контента для события: {e}")
            return None
    
    @staticmethod
    async def auto_generate_holiday_content(
        user_id: int,
        holiday_date: datetime,
        holiday_name: str
    ) -> Optional[Dict]:
        """
        Автоматически генерирует контент для праздника
        
        Args:
            user_id: ID пользователя
            holiday_date: Дата праздника
            holiday_name: Название праздника
        
        Returns:
            Dict с сгенерированным контентом или None
        """
        try:
            # Получаем профиль НКО
            from bot.database.models import NKOProfile
            with get_db() as db:
                profile = db.query(NKOProfile).filter(NKOProfile.user_id == user_id).first()
            
            nko_info = ""
            if profile:
                if profile.organization_name:
                    nko_info += f"Организация: {profile.organization_name}. "
                if profile.description:
                    nko_info += f"Деятельность: {profile.description[:200]}. "
            
            # Генерируем пост
            prompt = f"""Создай пост для некоммерческой организации к празднику.

Праздник: {holiday_name}
Дата: {holiday_date.strftime('%d.%m.%Y')}

{nko_info}

Требования:
- Поздравление с праздником
- Связь с деятельностью НКО
- Живой, естественный язык
- Абзацы - ОБЯЗАТЕЛЬНО
- 80-120 слов
- Уместные хештеги"""
            
            result = await openrouter_api.generate_text(
                prompt=prompt,
                system_prompt="Ты эксперт по созданию праздничных постов для некоммерческих организаций.",
                temperature=0.8,
                max_tokens=300
            )
            
            if result and result.get("success"):
                text = result.get("content", "")
                
                # Сохраняем в историю
                from bot.database.models import ContentHistory
                from bot.utils.helpers import get_or_create_user
                from telegram import User
                
                with get_db() as db:
                    history_entry = ContentHistory(
                        user_id=user_id,
                        content_type="text",
                        content_data={
                            "text": text,
                            "type": "holiday",
                            "holiday_name": holiday_name,
                            "holiday_date": holiday_date.isoformat(),
                            "auto_generated": True
                        },
                        tags=[holiday_name]
                    )
                    db.add(history_entry)
                    db.commit()
                
                return {
                    "success": True,
                    "text": text,
                    "holiday_name": holiday_name,
                    "holiday_date": holiday_date.isoformat()
                }
            
            return None
        
        except Exception as e:
            logger.exception(f"Ошибка при автогенерации праздничного контента: {e}")
            return None


# Глобальный экземпляр
smart_reminder_service = SmartReminderService()

