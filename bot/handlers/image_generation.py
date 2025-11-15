"""
Обработчики генерации изображений
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CallbackQueryHandler, MessageHandler, filters
from bot.keyboards.main_menu import get_main_menu_keyboard
from bot.keyboards.inline import (
    get_image_post_processing_keyboard,
    get_image_platform_keyboard
)
from bot.services.ai.image_ai import image_ai_service
from bot.services.ai.speech_recognition import speech_recognition_service
from bot.services.image_processing import image_processing_service
from bot.database.models import NKOProfile
from bot.database.database import get_db
from pathlib import Path

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
END = ConversationHandler.END


async def show_image_generation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает меню генерации изображений"""
    logger.info(f"show_image_generation_menu вызван для пользователя {update.effective_user.id}")
    
    text = (
        "🎨 **Генерация изображения**\n\n"
        "Опиши изображение, которое хочешь создать, или прикрепи референсные изображения.\n\n"
        "Отправь описание изображения:"
    )
    
    await update.message.reply_text(text, parse_mode="Markdown")
    context.user_data['image_gen'] = {}
    context.user_data['_conversation_active'] = True
    
    logger.info(f"Установлено состояние: waiting_image_description для пользователя {update.effective_user.id}")
    return "waiting_image_description"


async def handle_image_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка описания изображения (текст или голосовое)"""
    description = None
    processing_msg = None
    
    # Проверяем, это текстовое или голосовое сообщение
    if update.message.voice:
        # Голосовое сообщение
        logger.info(f"Получено голосовое сообщение для генерации изображения")
        
        # Показываем индикатор обработки
        processing_msg = await update.message.reply_text(
            "🎤 Распознаю голосовое сообщение...\n\n"
            "Это может занять несколько секунд."
        )
        
        try:
            # Распознаем речь
            transcribed_text = await speech_recognition_service.transcribe_voice_message(
                voice_file_id=update.message.voice.file_id,
                bot=context.bot
            )
            
            if not transcribed_text or len(transcribed_text.strip()) < 3:
                await processing_msg.edit_text(
                    "❌ Не удалось распознать голосовое сообщение или описание слишком короткое.\n\n"
                    "Попробуй еще раз или отправь описание текстом:"
                )
                return "waiting_image_description"
            
            description = transcribed_text.strip()
            
            # Показываем транскрипцию пользователю
            await processing_msg.edit_text(
                f"✅ Распознано:\n\n*{description}*\n\n"
                "Если нужно исправить, отправь описание текстом.\n\n"
                "⏳ Генерирую изображение...\n"
                "Это может занять некоторое время.",
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.exception(f"Ошибка при распознавании голосового сообщения: {e}")
            await processing_msg.edit_text(
                "❌ Ошибка при распознавании голосового сообщения.\n\n"
                "Попробуй отправить описание текстом:"
            )
            return "waiting_image_description"
    
    elif update.message.text:
        # Текстовое сообщение
        description = update.message.text.strip()
        logger.info(f"✅ ConversationHandler перехватил сообщение для генерации изображения! Получен текст: {description[:50]}... (длина: {len(description)})")
        
        # Отправляем сообщение о генерации
        processing_msg = await update.message.reply_text(
            f"✅ Описание принято: {description}\n\n"
            f"⏳ Генерирую изображение...\n"
            f"Это может занять некоторое время."
        )
    
    if not description or len(description) < 3:
        await update.message.reply_text(
            "❌ Описание слишком короткое. Напиши хотя бы 3 символа:"
        )
        return "waiting_image_description"
    
    context.user_data['image_gen']['description'] = description
    context.user_data['_conversation_active'] = True
    
    logger.info(f"Описание сохранено в user_data: {description[:30]}...")
    
    # Если processing_msg не был создан (для текстового сообщения), создаем его
    if processing_msg is None:
        processing_msg = await update.message.reply_text(
            f"⏳ Генерирую изображение...\n"
            f"Это может занять некоторое время."
        )
    
    try:
        user_id = update.effective_user.id
        
        # Генерируем изображение
        result = await image_ai_service.generate_image(
            prompt=description,
            style="realistic",
            aspect_ratio="1:1",
            user_id=user_id
        )
        
        if result and result.get("success"):
            file_path = result.get("file_path")
            image_path = Path(file_path)
            
            if image_path.exists():
                # Проверяем, есть ли логотип в профиле НКО
                has_logo = False
                logo_path = None
                with get_db() as db:
                    nko_profile = db.query(NKOProfile).filter(
                        NKOProfile.user_id == user_id,
                        NKOProfile.is_complete == True,
                        NKOProfile.is_active == True
                    ).first()
                    if nko_profile and nko_profile.logo_path:
                        logo_file = Path(nko_profile.logo_path)
                        if logo_file.exists():
                            has_logo = True
                            logo_path = logo_file
                
                # Сохраняем путь к изображению для дальнейшей обработки
                context.user_data['image_gen']['file_path'] = str(image_path)
                context.user_data['image_gen']['original_path'] = str(image_path)
                if logo_path:
                    context.user_data['image_gen']['logo_path'] = str(logo_path)
                
                # Отправляем изображение пользователю
                with open(image_path, 'rb') as photo:
                    await processing_msg.delete()
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"✅ **Готово!** Вот твоё изображение:\n\n*{description}*\n\n"
                                f"Можешь адаптировать его под разные платформы или добавить логотип.",
                        parse_mode="Markdown",
                        reply_markup=get_image_post_processing_keyboard(has_logo=has_logo)
                    )
                
                context.user_data['_conversation_active'] = True
                return "image_ready"
            else:
                await processing_msg.edit_text(
                    "❌ Файл изображения не найден. Попробуй еще раз."
                )
                context.user_data.pop('_conversation_active', None)
                return END
        else:
            error_msg = result.get('error', 'Неизвестная ошибка') if result else 'Ошибка генерации'
            await processing_msg.edit_text(
                f"❌ Ошибка при генерации изображения: {error_msg}\n\n"
                f"Попробуй изменить описание или проверь настройки API."
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    except Exception as e:
        logger.exception(f"Ошибка при генерации изображения: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при генерации. Попробуй еще раз."
        )
        context.user_data.pop('_conversation_active', None)
        return END


async def handle_image_post_processing(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка действий с готовым изображением"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    image_gen = context.user_data.get('image_gen', {})
    file_path = image_gen.get('file_path')
    
    if not file_path or not Path(file_path).exists():
        await query.edit_message_text(
            "❌ Изображение не найдено. Попробуй сгенерировать заново.",
            reply_markup=None
        )
        context.user_data.pop('_conversation_active', None)
        return END
    
    image_path = Path(file_path)
    
    if callback_data == "image_adapt_size":
        # Предлагаем выбрать платформу
        await query.edit_message_text(
            "📐 **Адаптация размера**\n\n"
            "Выбери платформу, для которой нужно адаптировать изображение:",
            reply_markup=get_image_platform_keyboard(),
            parse_mode="Markdown"
        )
        return "waiting_platform"
    
    elif callback_data == "image_add_logo":
        # Добавляем логотип
        logo_path = image_gen.get('logo_path')
        if not logo_path or not Path(logo_path).exists():
            await query.edit_message_text(
                "❌ Логотип не найден в профиле НКО.",
                reply_markup=None
            )
            return "image_ready"
        
        processing_msg = await query.edit_message_text(
            "🏷️ Добавляю логотип на изображение...",
            reply_markup=None
        )
        
        try:
            # Создаем копию изображения с логотипом
            output_path = image_path.parent / f"{image_path.stem}_with_logo{image_path.suffix}"
            result_path = image_processing_service.add_logo_to_image(
                image_path=image_path,
                logo_path=Path(logo_path),
                position="bottom_right",
                output_path=output_path
            )
            
            if result_path and result_path.exists():
                # Обновляем путь к изображению
                context.user_data['image_gen']['file_path'] = str(result_path)
                
                with open(result_path, 'rb') as photo:
                    await processing_msg.delete()
                    await update.message.reply_photo(
                        photo=photo,
                        caption=f"✅ **Логотип добавлен!**\n\n"
                                f"Изображение готово к использованию.",
                        parse_mode="Markdown",
                        reply_markup=get_image_post_processing_keyboard(has_logo=True)
                    )
                return "image_ready"
            else:
                await processing_msg.edit_text(
                    "❌ Ошибка при добавлении логотипа.",
                    reply_markup=None
                )
                return "image_ready"
        except Exception as e:
            logger.exception(f"Ошибка при добавлении логотипа: {e}")
            await processing_msg.edit_text(
                "❌ Произошла ошибка при добавлении логотипа.",
                reply_markup=None
            )
            return "image_ready"
    
    elif callback_data == "image_create_cover":
        # Создаем обложку с текстом
        await query.edit_message_text(
            "📝 **Создание обложки**\n\n"
            "Введи текст для обложки:",
            reply_markup=None,
            parse_mode="Markdown"
        )
        return "waiting_cover_text"
    
    elif callback_data == "image_create_collage":
        # Создаем коллаж
        await query.edit_message_text(
            "🖼️ **Создание коллажа**\n\n"
            "Отправь еще изображения для коллажа (до 4 изображений). "
            "Когда закончишь, напиши 'готово':",
            reply_markup=None,
            parse_mode="Markdown"
        )
        context.user_data['image_gen']['collage_images'] = [str(image_path)]
        return "waiting_collage_images"
    
    elif callback_data == "save_image":
        # Сохранение обрабатывается в другом месте
        await query.answer("Изображение сохранено в истории")
        return "image_ready"
    
    elif callback_data == "regenerate_image":
        # Возвращаемся к генерации
        description = image_gen.get('description', '')
        if description:
            # Сохраняем описание и переходим к генерации
            context.user_data['image_gen']['description'] = description
            await query.edit_message_text(
                f"🔄 Перегенерирую изображение...\n\n"
                f"Описание: *{description}*",
                parse_mode="Markdown"
            )
            # Создаем фиктивное сообщение для повторной генерации
            fake_message = type('obj', (object,), {
                'text': description,
                'voice': None,
                'reply_text': lambda text, **kwargs: query.edit_message_text(text, **kwargs)
            })()
            fake_update = type('obj', (object,), {
                'message': fake_message,
                'effective_user': update.effective_user
            })()
            return await handle_image_description(fake_update, context)
        else:
            await query.edit_message_text(
                "❌ Описание не найдено. Начни заново.",
                reply_markup=None
            )
            context.user_data.pop('_conversation_active', None)
            return END
    
    elif callback_data == "main_menu":
        context.user_data.pop('_conversation_active', None)
        await query.edit_message_text("Возврат в главное меню")
        return END
    
    return "image_ready"


async def handle_platform_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора платформы для адаптации размера"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == "skip_platform":
        await query.edit_message_text(
            "⏭️ Адаптация размера пропущена.",
            reply_markup=None
        )
        return "image_ready"
    
    # Маппинг платформ
    platform_map = {
        "platform_instagram": "instagram",
        "platform_instagram_story": "instagram_story",
        "platform_vk": "vk",
        "platform_telegram": "telegram",
        "platform_facebook": "facebook"
    }
    
    platform = platform_map.get(callback_data)
    if not platform:
        await query.answer("Неверный выбор платформы")
        return "waiting_platform"
    
    image_gen = context.user_data.get('image_gen', {})
    file_path = image_gen.get('file_path') or image_gen.get('original_path')
    
    if not file_path or not Path(file_path).exists():
        await query.edit_message_text(
            "❌ Изображение не найдено.",
            reply_markup=None
        )
        return END
    
    processing_msg = await query.edit_message_text(
        f"📐 Адаптирую изображение под {platform}...",
        reply_markup=None
    )
    
    try:
        image_path = Path(file_path)
        output_path = image_path.parent / f"{image_path.stem}_{platform}{image_path.suffix}"
        
        result_path = image_processing_service.resize_for_platform(
            image_path=image_path,
            platform=platform,
            output_path=output_path
        )
        
        if result_path and result_path.exists():
            # Обновляем путь к изображению
            context.user_data['image_gen']['file_path'] = str(result_path)
            
            with open(result_path, 'rb') as photo:
                await processing_msg.delete()
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"✅ **Изображение адаптировано под {platform}!**\n\n"
                            f"Размер оптимизирован для этой платформы.",
                    parse_mode="Markdown",
                    reply_markup=get_image_post_processing_keyboard(
                        has_logo=bool(image_gen.get('logo_path'))
                    )
                )
            return "image_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при адаптации размера.",
                reply_markup=None
            )
            return "image_ready"
    except Exception as e:
        logger.exception(f"Ошибка при адаптации размера: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при адаптации размера.",
            reply_markup=None
        )
        return "image_ready"


async def handle_cover_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текста для создания обложки"""
    cover_text = update.message.text.strip()
    
    if not cover_text or len(cover_text) < 3:
        await update.message.reply_text(
            "❌ Текст слишком короткий. Напиши хотя бы 3 символа:"
        )
        return "waiting_cover_text"
    
    processing_msg = await update.message.reply_text(
        "📝 Создаю обложку с текстом...",
        reply_markup=None
    )
    
    try:
        # Получаем цвета бренда из профиля НКО, если есть
        user_id = update.effective_user.id
        brand_colors = None
        with get_db() as db:
            nko_profile = db.query(NKOProfile).filter(
                NKOProfile.user_id == user_id,
                NKOProfile.is_complete == True,
                NKOProfile.is_active == True
            ).first()
            if nko_profile and nko_profile.brand_colors:
                brand_colors = nko_profile.brand_colors
        
        # Используем цвета бренда или дефолтные
        bg_color = tuple(brand_colors[0]) if brand_colors and len(brand_colors) > 0 else (41, 128, 185)
        text_color = (255, 255, 255)
        
        # Создаем обложку
        from datetime import datetime
        output_path = Path(context.user_data['image_gen'].get('file_path', '')).parent / \
                     f"cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        result_path = image_processing_service.generate_post_cover(
            text=cover_text,
            background_color=bg_color,
            text_color=text_color,
            output_path=output_path
        )
        
        if result_path and result_path.exists():
            context.user_data['image_gen']['file_path'] = str(result_path)
            
            with open(result_path, 'rb') as photo:
                await processing_msg.delete()
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"✅ **Обложка создана!**\n\n*{cover_text}*",
                    parse_mode="Markdown",
                    reply_markup=get_image_post_processing_keyboard(
                        has_logo=bool(context.user_data['image_gen'].get('logo_path'))
                    )
                )
            return "image_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при создании обложки.",
                reply_markup=None
            )
            return "image_ready"
    except Exception as e:
        logger.exception(f"Ошибка при создании обложки: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при создании обложки.",
            reply_markup=None
        )
        return "image_ready"


async def handle_collage_images(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изображений для коллажа"""
    if update.message.photo:
        # Получаем самое большое фото
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Сохраняем временно
        collage_images = context.user_data['image_gen'].setdefault('collage_images', [])
        temp_dir = Path(context.user_data['image_gen'].get('file_path', '')).parent
        temp_path = temp_dir / f"collage_temp_{len(collage_images)}_{photo.file_id}.jpg"
        
        await file.download_to_drive(temp_path)
        collage_images.append(str(temp_path))
        
        if len(collage_images) >= 4:
            await update.message.reply_text(
                f"✅ Получено {len(collage_images)} изображений. Создаю коллаж...",
                reply_markup=None
            )
            return await create_collage(update, context)
        else:
            await update.message.reply_text(
                f"✅ Изображение {len(collage_images)}/4 получено. Отправь еще или напиши 'готово':"
            )
            return "waiting_collage_images"
    
    elif update.message.text and update.message.text.strip().lower() in ['готово', 'готов', 'done']:
        return await create_collage(update, context)
    
    else:
        await update.message.reply_text(
            "Отправь изображение или напиши 'готово' для создания коллажа:"
        )
        return "waiting_collage_images"


async def create_collage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание коллажа из изображений"""
    processing_msg = await update.message.reply_text(
        "🖼️ Создаю коллаж...",
        reply_markup=None
    )
    
    try:
        collage_images = context.user_data['image_gen'].get('collage_images', [])
        if len(collage_images) < 2:
            await processing_msg.edit_text(
                "❌ Нужно минимум 2 изображения для коллажа.",
                reply_markup=None
            )
            return "image_ready"
        
        # Определяем layout
        image_count = len(collage_images)
        if image_count == 2:
            layout = "1x2"
        elif image_count == 3:
            layout = "1x3"
        else:
            layout = "2x2"
        
        # Создаем коллаж
        from datetime import datetime
        output_path = Path(collage_images[0]).parent / \
                     f"collage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        result_path = image_processing_service.create_collage(
            image_paths=[Path(p) for p in collage_images],
            layout=layout,
            output_path=output_path
        )
        
        if result_path and result_path.exists():
            context.user_data['image_gen']['file_path'] = str(result_path)
            
            with open(result_path, 'rb') as photo:
                await processing_msg.delete()
                await update.message.reply_photo(
                    photo=photo,
                    caption=f"✅ **Коллаж создан!**\n\n"
                            f"Объединено {len(collage_images)} изображений.",
                    parse_mode="Markdown",
                    reply_markup=get_image_post_processing_keyboard(
                        has_logo=bool(context.user_data['image_gen'].get('logo_path'))
                    )
                )
            
            # Очищаем временные файлы коллажа
            for img_path in collage_images[1:]:  # Первое изображение - оригинальное
                try:
                    Path(img_path).unlink()
                except:
                    pass
            
            context.user_data['image_gen'].pop('collage_images', None)
            return "image_ready"
        else:
            await processing_msg.edit_text(
                "❌ Ошибка при создании коллажа.",
                reply_markup=None
            )
            return "image_ready"
    except Exception as e:
        logger.exception(f"Ошибка при создании коллажа: {e}")
        await processing_msg.edit_text(
            "❌ Произошла ошибка при создании коллажа.",
            reply_markup=None
        )
        return "image_ready"


def setup_image_generation_handlers(application):
    """Настройка обработчиков генерации изображений"""
    # ConversationHandler для генерации изображений
    image_gen_handler = ConversationHandler(
        entry_points=[
            MessageHandler(
                filters.Regex("^🎨 Генерация изображения$"),
                show_image_generation_menu
            ),
        ],
        states={
            "waiting_image_description": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_image_description),
                MessageHandler(filters.VOICE, handle_image_description)
            ],
            "image_ready": [
                CallbackQueryHandler(handle_image_post_processing, pattern="^(image_|save_image|regenerate_image|main_menu)"),
            ],
            "waiting_platform": [
                CallbackQueryHandler(handle_platform_selection, pattern="^(platform_|skip_platform)"),
            ],
            "waiting_cover_text": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_cover_text),
            ],
            "waiting_collage_images": [
                MessageHandler(filters.PHOTO, handle_collage_images),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_collage_images),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Отмена$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
            MessageHandler(filters.Regex("^◀️ Назад$"), lambda u, c: (u.user_data.pop('_conversation_active', None), END)[1]),
        ],
        allow_reentry=True,
        per_chat=True,
        per_user=True
    )
    
    application.add_handler(image_gen_handler)
    logger.info("Обработчики генерации изображений настроены")

