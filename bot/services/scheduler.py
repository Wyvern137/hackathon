"""
Сервис для планирования и напоминаний
"""
import logging
from datetime import datetime, time, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bot.database.models import ContentPlan, NotificationSettings
from bot.database.database import get_db

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_reminder(user_id: int, plan_id: int, message: str):
    """Отправляет напоминание пользователю"""
    # Эта функция будет вызвана планировщиком
    # Здесь должна быть логика отправки сообщения через Telegram Bot API
    # Пока просто логируем
    logger.info(f"Напоминание для пользователя {user_id}, план {plan_id}: {message}")
    # TODO: Реализовать отправку через application.bot.send_message


async def schedule_content_plan_reminders(plan: ContentPlan):
    """
    Планирует напоминания для контент-плана
    
    Args:
        plan: Контент-план
    """
    try:
        with get_db() as db:
            settings = db.query(NotificationSettings).filter(
                NotificationSettings.user_id == plan.user_id
            ).first()
        
        if not settings or not settings.reminder_enabled:
            return
        
        schedule = plan.schedule if isinstance(plan.schedule, dict) else {}
        days = schedule.get("days", [])
        time_str = schedule.get("time", "09:00")
        
        # Парсим время
        reminder_time = settings.reminder_time or time(9, 0)
        if isinstance(time_str, str) and ":" in time_str:
            try:
                hour, minute = map(int, time_str.split(":")[:2])
                reminder_time = time(hour, minute)
            except:
                pass
        
        # Планируем напоминания для каждого дня
        for day in days:
            # day: 1=понедельник, 7=воскресенье
            # APScheduler использует: 0=понедельник, 6=воскресенье
            weekday = day - 1 if day <= 7 else day
            
            trigger = CronTrigger(
                day_of_week=weekday,
                hour=reminder_time.hour,
                minute=reminder_time.minute
            )
            
            message = f"📅 Напоминание: сегодня запланирован пост по контент-плану '{plan.plan_name}'"
            
            scheduler.add_job(
                send_reminder,
                trigger=trigger,
                args=[plan.user_id, plan.id, message],
                id=f"plan_{plan.id}_day_{day}",
                replace_existing=True
            )
        
        logger.info(f"Напоминания для плана {plan.id} запланированы")
    
    except Exception as e:
        logger.exception(f"Ошибка при планировании напоминаний: {e}")


async def cancel_content_plan_reminders(plan_id: int):
    """Отменяет напоминания для контент-плана"""
    try:
        # Удаляем все задачи для этого плана
        jobs = [job for job in scheduler.get_jobs() if job.id.startswith(f"plan_{plan_id}_")]
        for job in jobs:
            scheduler.remove_job(job.id)
        
        logger.info(f"Напоминания для плана {plan_id} отменены")
    
    except Exception as e:
        logger.exception(f"Ошибка при отмене напоминаний: {e}")


def start_scheduler():
    """Запускает планировщик"""
    if not scheduler.running:
        scheduler.start()
        logger.info("Планировщик запущен")


def stop_scheduler():
    """Останавливает планировщик"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Планировщик остановлен")

