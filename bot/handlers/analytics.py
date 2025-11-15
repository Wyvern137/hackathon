"""
Обработчики статистики и аналитики
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.helpers import get_or_create_user
from bot.database.models import ContentHistory, ContentPlan, PostTemplate
from bot.database.database import get_db

try:
    import matplotlib
    matplotlib.use('Agg')  # Используем backend без GUI
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    matplotlib_available = True
except ImportError:
    matplotlib_available = False
    logging.warning("matplotlib не установлен, визуализация будет недоступна")

logger = logging.getLogger(__name__)

CHARTS_DIR = Path("data/charts")
CHARTS_DIR.mkdir(parents=True, exist_ok=True)


async def show_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику использования бота"""
    user_id = update.effective_user.id
    get_or_create_user(user_id, update.effective_user.username, update.effective_user.first_name or "")
    
    with get_db() as db:
        # Общая статистика
        total_texts = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "text"
        ).count()
        
        total_images = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "image"
        ).count()
        
        total_plans = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "plan"
        ).count()
        
        # Статистика за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        texts_week = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "text",
            ContentHistory.generated_at >= week_ago
        ).count()
        
        images_week = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "image",
            ContentHistory.generated_at >= week_ago
        ).count()
        
        # Активные планы
        active_plans = db.query(ContentPlan).filter(
            ContentPlan.user_id == user_id,
            ContentPlan.is_active == True
        ).count()
        
        # Шаблоны
        templates_count = db.query(PostTemplate).filter(
            PostTemplate.user_id == user_id
        ).count()
        
        # Самая популярная функция
        all_items = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id
        ).all()
        
        function_usage = {
            "text": 0,
            "image": 0,
            "plan": 0
        }
        
        for item in all_items:
            if item.content_type in function_usage:
                function_usage[item.content_type] += 1
        
        most_popular = max(function_usage.items(), key=lambda x: x[1])[0] if function_usage else "text"
        most_popular_names = {
            "text": "📝 Генерация текста",
            "image": "🎨 Генерация изображений",
            "plan": "📅 Контент-план"
        }
        
        # Статистика по стилям (для расширенной аналитики)
        text_types = db.query(ContentHistory).filter(
            ContentHistory.user_id == user_id,
            ContentHistory.content_type == "text"
        ).all()
    
    # Формируем сообщение
    text = (
        "📊 **Статистика использования**\n\n"
        "**Общая статистика:**\n"
        f"📝 Текстов создано: {total_texts}\n"
        f"🎨 Изображений создано: {total_images}\n"
        f"📅 Контент-планов: {total_plans}\n"
        f"📋 Шаблонов: {templates_count}\n\n"
        
        "**За последние 7 дней:**\n"
        f"📝 Текстов: {texts_week}\n"
        f"🎨 Изображений: {images_week}\n\n"
        
        "**Активные планы:**\n"
        f"📅 Активных контент-планов: {active_plans}\n\n"
        
        "**Самая популярная функция:**\n"
        f"⭐ {most_popular_names.get(most_popular, 'Нет данных')}\n\n"
    )
    
    # Расширенная статистика
    if total_texts > 0:
        # Статистика по стилям
        style_stats = {}
        for item in text_types:
            if item.content_type == "text":
                content_data = item.content_data if isinstance(item.content_data, dict) else {}
                style = content_data.get("style", "не указан")
                style_stats[style] = style_stats.get(style, 0) + 1
        
        if style_stats:
            text += "**Статистика по стилям:**\n"
            for style, count in sorted(style_stats.items(), key=lambda x: x[1], reverse=True):
                text += f"• {style}: {count}\n"
            text += "\n"
        
        # Статистика активности за месяц
        month_ago = datetime.now() - timedelta(days=30)
        with get_db() as db_month:
            texts_month = db_month.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == "text",
                ContentHistory.generated_at >= month_ago
            ).count()
        
        text += "**За последний месяц:**\n"
        text += f"📝 Текстов: {texts_month}\n\n"
    
    # Рекомендации
    if total_texts == 0:
        text += "💡 Совет: Попробуй создать свой первый пост!"
    elif templates_count == 0 and total_texts > 3:
        text += "💡 Совет: Создай шаблон из часто используемых постов для ускорения работы!"
    elif active_plans == 0:
        text += "💡 Совет: Создай контент-план для регулярных публикаций!"
    elif texts_month == 0 and total_texts > 0:
        text += "💡 Совет: За последний месяц нет активности. Время вернуться к созданию контента!"
    
    await update.message.reply_text(text, parse_mode="Markdown")


def get_detailed_statistics(user_id: int, period_days: int = 30) -> Dict[str, Any]:
    """
    Получает детальную статистику за период
    
    Args:
        user_id: ID пользователя
        period_days: Период в днях
    
    Returns:
        Dict со статистикой
    """
    try:
        start_date = datetime.now() - timedelta(days=period_days)
        
        with get_db() as db:
            # Статистика по типам контента
            texts = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == "text",
                ContentHistory.generated_at >= start_date
            ).all()
            
            images = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == "image",
                ContentHistory.generated_at >= start_date
            ).all()
            
            plans = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == "plan",
                ContentHistory.generated_at >= start_date
            ).all()
            
            # Активность по дням
            daily_activity = {}
            for item in texts + images + plans:
                day = item.generated_at.date()
                daily_activity[day] = daily_activity.get(day, 0) + 1
            
            # Статистика по стилям
            style_stats = {}
            for item in texts:
                content_data = item.content_data if isinstance(item.content_data, dict) else {}
                style = content_data.get("style", "не указан")
                style_stats[style] = style_stats.get(style, 0) + 1
            
            # Самая активная неделя
            weekly_activity = {}
            for day, count in daily_activity.items():
                week_start = day - timedelta(days=day.weekday())
                weekly_activity[week_start] = weekly_activity.get(week_start, 0) + count
            
            most_active_week = max(weekly_activity.items(), key=lambda x: x[1]) if weekly_activity else None
            
            return {
                "success": True,
                "period_days": period_days,
                "texts_count": len(texts),
                "images_count": len(images),
                "plans_count": len(plans),
                "total_count": len(texts) + len(images) + len(plans),
                "daily_activity": daily_activity,
                "style_stats": style_stats,
                "most_active_week": most_active_week[0].isoformat() if most_active_week else None,
                "most_active_week_count": most_active_week[1] if most_active_week else 0
            }
    
    except Exception as e:
        logger.exception(f"Ошибка при получении детальной статистики: {e}")
        return {"success": False, "error": str(e)}


async def analyze_content_popularity(user_id: int, content_type: str = "text", limit: int = 10) -> Dict[str, Any]:
    """
    Анализирует популярность контента по различным метрикам
    
    Args:
        user_id: ID пользователя
        content_type: Тип контента (text, image, plan)
        limit: Количество элементов для анализа
    
    Returns:
        Dict с результатами анализа
    """
    try:
        with get_db() as db:
            items = db.query(ContentHistory).filter(
                ContentHistory.user_id == user_id,
                ContentHistory.content_type == content_type
            ).order_by(ContentHistory.generated_at.desc()).limit(limit).all()
        
        if not items:
            return {"success": False, "error": "Контент не найден"}
        
        # Анализируем тексты
        if content_type == "text":
            popularity_metrics = {
                "most_used_hashtags": {},
                "most_common_styles": {},
                "average_length": 0,
                "total_hashtags": 0
            }
            
            total_length = 0
            for item in items:
                content_data = item.content_data if isinstance(item.content_data, dict) else {}
                text = content_data.get("text", str(content_data))
                
                # Подсчитываем длину
                total_length += len(text)
                
                # Анализируем хештеги
                hashtags = content_data.get("hashtags", [])
                for tag in hashtags:
                    popularity_metrics["most_used_hashtags"][tag] = popularity_metrics["most_used_hashtags"].get(tag, 0) + 1
                    popularity_metrics["total_hashtags"] += 1
                
                # Анализируем стили
                style = content_data.get("style", "не указан")
                popularity_metrics["most_common_styles"][style] = popularity_metrics["most_common_styles"].get(style, 0) + 1
            
            popularity_metrics["average_length"] = round(total_length / len(items), 1) if items else 0
            popularity_metrics["most_used_hashtags"] = dict(sorted(
                popularity_metrics["most_used_hashtags"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10])
            popularity_metrics["most_common_styles"] = dict(sorted(
                popularity_metrics["most_common_styles"].items(),
                key=lambda x: x[1],
                reverse=True
            ))
            
            return {
                "success": True,
                "content_type": content_type,
                "items_analyzed": len(items),
                "metrics": popularity_metrics
            }
        
        return {"success": False, "error": "Тип контента не поддерживается для анализа популярности"}
    
    except Exception as e:
        logger.exception(f"Ошибка при анализе популярности: {e}")
        return {"success": False, "error": str(e)}


async def generate_activity_chart(user_id: int, period_days: int = 30) -> Optional[Path]:
    """
    Генерирует график активности пользователя
    
    Args:
        user_id: ID пользователя
        period_days: Период в днях
    
    Returns:
        Path к файлу с графиком или None
    """
    if not matplotlib_available:
        logger.warning("matplotlib не установлен, график не может быть создан")
        return None
    
    try:
        stats = get_detailed_statistics(user_id, period_days)
        
        if not stats.get("success") or not stats.get("daily_activity"):
            return None
        
        daily_activity = stats["daily_activity"]
        
        # Сортируем по датам
        sorted_dates = sorted(daily_activity.keys())
        dates = sorted_dates
        counts = [daily_activity[date] for date in dates]
        
        # Создаем график
        plt.figure(figsize=(12, 6))
        plt.plot(dates, counts, marker='o', linestyle='-', linewidth=2, markersize=5)
        plt.fill_between(dates, counts, alpha=0.3)
        plt.title(f'Активность за {period_days} дней', fontsize=14, fontweight='bold')
        plt.xlabel('Дата', fontsize=12)
        plt.ylabel('Количество постов', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Форматируем даты
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
        plt.gcf().autofmt_xdate()
        
        plt.tight_layout()
        
        # Сохраняем график
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"activity_{user_id}_{timestamp}.png"
        file_path = CHARTS_DIR / filename
        plt.savefig(file_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        logger.info(f"График активности создан: {file_path}")
        return file_path
    
    except Exception as e:
        logger.exception(f"Ошибка при создании графика активности: {e}")
        return None


def generate_recommendations(user_id: int) -> List[str]:
    """
    Генерирует рекомендации на основе статистики пользователя
    
    Args:
        user_id: ID пользователя
    
    Returns:
        Список рекомендаций
    """
    recommendations = []
    
    try:
        stats = get_detailed_statistics(user_id, period_days=30)
        
        if not stats.get("success"):
            return ["Недостаточно данных для рекомендаций"]
        
        total_count = stats.get("total_count", 0)
        texts_count = stats.get("texts_count", 0)
        images_count = stats.get("images_count", 0)
        plans_count = stats.get("plans_count", 0)
        
        # Рекомендации на основе статистики
        if total_count == 0:
            recommendations.append("💡 Начни с создания первого поста!")
        elif texts_count > images_count * 3:
            recommendations.append("💡 Попробуй создать больше изображений для визуального разнообразия!")
        elif images_count > texts_count * 3:
            recommendations.append("💡 Добавь больше текстовых постов для контента!")
        elif plans_count == 0:
            recommendations.append("💡 Создай контент-план для регулярных публикаций!")
        elif stats.get("most_active_week_count", 0) > 10:
            recommendations.append("⭐ Отличная активность! Продолжай в том же духе!")
        
        # Анализ активности
        daily_activity = stats.get("daily_activity", {})
        if len(daily_activity) < 5:
            recommendations.append("📅 Попробуй публиковать контент регулярнее для лучшего охвата!")
        elif len(daily_activity) > 20:
            recommendations.append("🔥 Высокая активность! Отличная работа!")
        
        # Рекомендации по стилям
        style_stats = stats.get("style_stats", {})
        if len(style_stats) == 1:
            recommendations.append("💡 Попробуй экспериментировать с разными стилями изложения!")
        
        if not recommendations:
            recommendations.append("✨ Продолжай создавать качественный контент!")
        
        return recommendations
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации рекомендаций: {e}")
        return ["Не удалось сгенерировать рекомендации"]


def setup_analytics_handlers(application):
    """Настройка обработчиков аналитики"""
    pass

