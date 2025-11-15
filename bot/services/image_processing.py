"""
Сервис для обработки изображений (коллажи, добавление логотипа, адаптация размеров)
"""
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """Сервис для обработки изображений"""
    
    # Размеры изображений для разных платформ
    PLATFORM_SIZES = {
        "instagram": (1080, 1080),  # Квадратный пост
        "instagram_story": (1080, 1920),  # Stories
        "vk": (1200, 630),  # Обложка поста ВКонтакте
        "telegram": (1024, 1024),  # Telegram
        "facebook": (1200, 630),  # Facebook
    }
    
    def __init__(self):
        """Инициализация сервиса"""
        pass
    
    def resize_for_platform(
        self,
        image_path: Path,
        platform: str,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Адаптирует изображение под размеры для платформы
        
        Args:
            image_path: Путь к исходному изображению
            platform: Платформа (instagram, instagram_story, vk, telegram, facebook)
            output_path: Путь для сохранения (если None, перезаписывает исходный)
        
        Returns:
            Путь к адаптированному изображению или None
        """
        try:
            size = self.PLATFORM_SIZES.get(platform.lower())
            if not size:
                logger.warning(f"Неизвестная платформа: {platform}")
                return None
            
            image = Image.open(image_path)
            original_size = image.size
            
            # Изменяем размер с сохранением пропорций
            image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Создаем новое изображение нужного размера с белым фоном
            new_image = Image.new('RGB', size, (255, 255, 255))
            
            # Центрируем изображение
            paste_x = (size[0] - image.size[0]) // 2
            paste_y = (size[1] - image.size[1]) // 2
            new_image.paste(image, (paste_x, paste_y))
            
            output = output_path or image_path
            new_image.save(output, quality=95)
            
            logger.info(f"Изображение адаптировано под {platform}: {original_size} -> {size}")
            return output
        
        except Exception as e:
            logger.error(f"Ошибка при адаптации изображения: {e}")
            return None
    
    def create_collage(
        self,
        image_paths: List[Path],
        layout: str = "2x2",
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Создает коллаж из нескольких изображений
        
        Args:
            image_paths: Список путей к изображениям
            layout: Макет коллажа (1x2, 2x1, 2x2, 1x3, 3x1)
            output_path: Путь для сохранения
        
        Returns:
            Путь к созданному коллажу или None
        """
        try:
            if not image_paths:
                logger.warning("Нет изображений для создания коллажа")
                return None
            
            # Парсим layout
            rows, cols = map(int, layout.split('x'))
            max_images = rows * cols
            image_paths = image_paths[:max_images]
            
            # Загружаем изображения
            images = []
            for path in image_paths:
                try:
                    img = Image.open(path)
                    img = img.convert('RGB')
                    images.append(img)
                except Exception as e:
                    logger.error(f"Ошибка при загрузке изображения {path}: {e}")
                    continue
            
            if not images:
                logger.warning("Не удалось загрузить ни одного изображения")
                return None
            
            # Определяем размер каждого изображения в коллаже
            target_size = 512  # Размер каждой ячейки
            cell_width = target_size
            cell_height = target_size
            
            # Размер итогового изображения
            collage_width = cell_width * cols
            collage_height = cell_height * rows
            
            # Создаем новое изображение
            collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))
            
            # Размещаем изображения
            for i, img in enumerate(images):
                if i >= max_images:
                    break
                
                row = i // cols
                col = i % cols
                
                # Изменяем размер изображения под ячейку
                img_resized = img.copy()
                img_resized.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
                
                # Центрируем в ячейке
                x = col * cell_width + (cell_width - img_resized.width) // 2
                y = row * cell_height + (cell_height - img_resized.height) // 2
                
                # Вставляем изображение
                if img_resized.mode == 'RGBA':
                    collage.paste(img_resized, (x, y), img_resized)
                else:
                    collage.paste(img_resized, (x, y))
            
            # Сохраняем коллаж
            if output_path is None:
                from datetime import datetime
                output_path = Path(image_paths[0].parent) / f"collage_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            collage.save(output_path, quality=95)
            logger.info(f"Коллаж создан: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Ошибка при создании коллажа: {e}")
            return None
    
    def add_logo_to_image(
        self,
        image_path: Path,
        logo_path: Path,
        position: str = "bottom_right",
        size: Optional[Tuple[int, int]] = None,
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Добавляет логотип на изображение
        
        Args:
            image_path: Путь к исходному изображению
            logo_path: Путь к логотипу
            position: Позиция логотипа (top_left, top_right, bottom_left, bottom_right, center)
            size: Размер логотипа (ширина, высота) или None для автоматического
            output_path: Путь для сохранения
        
        Returns:
            Путь к изображению с логотипом или None
        """
        try:
            image = Image.open(image_path)
            logo = Image.open(logo_path)
            
            # Конвертируем в RGB если нужно
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Определяем размер логотипа
            if size:
                logo.thumbnail(size, Image.Resampling.LANCZOS)
            else:
                # Автоматический размер - 10% от ширины изображения
                logo_width = int(image.width * 0.1)
                logo.thumbnail((logo_width, logo_width), Image.Resampling.LANCZOS)
            
            # Определяем позицию
            margin = 20
            positions = {
                "top_left": (margin, margin),
                "top_right": (image.width - logo.width - margin, margin),
                "bottom_left": (margin, image.height - logo.height - margin),
                "bottom_right": (image.width - logo.width - margin, image.height - logo.height - margin),
                "center": ((image.width - logo.width) // 2, (image.height - logo.height) // 2)
            }
            
            pos = positions.get(position.lower(), positions["bottom_right"])
            
            # Вставляем логотип
            if logo.mode == 'RGBA':
                image.paste(logo, pos, logo)
            else:
                image.paste(logo, pos)
            
            output = output_path or image_path
            image.save(output, quality=95)
            
            logger.info(f"Логотип добавлен на изображение: {position}")
            return output
        
        except Exception as e:
            logger.error(f"Ошибка при добавлении логотипа: {e}")
            return None
    
    def generate_post_cover(
        self,
        text: str,
        background_color: Tuple[int, int, int] = (41, 128, 185),
        text_color: Tuple[int, int, int] = (255, 255, 255),
        size: Tuple[int, int] = (1200, 630),
        output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """
        Генерирует обложку для поста с текстом
        
        Args:
            text: Текст для обложки
            background_color: Цвет фона (RGB)
            text_color: Цвет текста (RGB)
            size: Размер изображения
            output_path: Путь для сохранения
        
        Returns:
            Путь к созданной обложке или None
        """
        try:
            # Создаем изображение
            image = Image.new('RGB', size, background_color)
            draw = ImageDraw.Draw(image)
            
            # Пытаемся загрузить шрифт
            try:
                # Пробуем разные шрифты в зависимости от системы
                font_paths = [
                    "/System/Library/Fonts/Helvetica.ttc",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
                    "C:/Windows/Fonts/arial.ttf",  # Windows
                ]
                
                font_size = 48
                font = None
                
                for font_path in font_paths:
                    if Path(font_path).exists():
                        try:
                            font = ImageFont.truetype(font_path, font_size)
                            break
                        except:
                            continue
                
                if font is None:
                    font = ImageFont.load_default()
            
            except Exception:
                font = ImageFont.load_default()
            
            # Разбиваем текст на строки
            words = text.split()
            lines = []
            current_line = []
            
            max_width = size[0] - 100  # Отступы 50px с каждой стороны
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                text_width = bbox[2] - bbox[0]
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Ограничиваем количество строк
            lines = lines[:5]
            
            # Рисуем текст по центру
            total_height = sum(draw.textbbox((0, 0), line, font=font)[3] - draw.textbbox((0, 0), line, font=font)[1] + 10 for line in lines)
            start_y = (size[1] - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                x = (size[0] - text_width) // 2
                y = start_y + i * (text_height + 10)
                
                draw.text((x, y), line, fill=text_color, font=font)
            
            # Сохраняем изображение
            if output_path is None:
                from datetime import datetime
                output_path = Path(f"/tmp/post_cover_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            image.save(output_path, quality=95)
            logger.info(f"Обложка для поста создана: {output_path}")
            return output_path
        
        except Exception as e:
            logger.error(f"Ошибка при создании обложки: {e}")
            return None


# Глобальный экземпляр сервиса
image_processing_service = ImageProcessingService()

