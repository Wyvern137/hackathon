"""
Сервис для обработки и редактирования изображений
"""
import logging
from typing import Optional, List, Tuple
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

logger = logging.getLogger(__name__)


class ImageProcessingService:
    """Сервис для обработки изображений"""
    
    def __init__(self):
        self.supported_formats = ['PNG', 'JPEG', 'JPG', 'WEBP']
    
    async def add_text_to_image(
        self,
        image_path: Path,
        text: str,
        position: Tuple[int, int] = (10, 10),
        font_size: int = 24,
        text_color: Tuple[int, int, int] = (255, 255, 255),
        background_color: Optional[Tuple[int, int, int]] = None
    ) -> Optional[Path]:
        """
        Добавляет текст на изображение
        
        Args:
            image_path: Путь к исходному изображению
            text: Текст для добавления
            position: Позиция текста (x, y)
            font_size: Размер шрифта
            text_color: Цвет текста (R, G, B)
            background_color: Цвет фона текста (опционально)
        
        Returns:
            Путь к обработанному изображению или None
        """
        try:
            # Открываем изображение
            img = Image.open(image_path)
            
            # Создаем объект для рисования
            draw = ImageDraw.Draw(img)
            
            # Пытаемся загрузить шрифт
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except:
                try:
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                except:
                    font = ImageFont.load_default()
            
            # Если нужен фон для текста
            if background_color:
                # Получаем размеры текста
                bbox = draw.textbbox(position, text, font=font)
                padding = 5
                draw.rectangle(
                    [
                        bbox[0] - padding,
                        bbox[1] - padding,
                        bbox[2] + padding,
                        bbox[3] + padding
                    ],
                    fill=background_color
                )
            
            # Рисуем текст
            draw.text(position, text, fill=text_color, font=font)
            
            # Сохраняем
            output_path = image_path.parent / f"{image_path.stem}_with_text{image_path.suffix}"
            img.save(output_path)
            
            logger.info(f"Текст добавлен на изображение: {output_path}")
            return output_path
        
        except Exception as e:
            logger.exception(f"Ошибка при добавлении текста на изображение: {e}")
            return None
    
    async def add_logo(
        self,
        image_path: Path,
        logo_path: Path,
        position: str = "bottom_right",
        size: Tuple[int, int] = (100, 100),
        opacity: float = 1.0
    ) -> Optional[Path]:
        """
        Добавляет логотип на изображение
        
        Args:
            image_path: Путь к исходному изображению
            logo_path: Путь к логотипу
            position: Позиция логотипа (top_left, top_right, bottom_left, bottom_right, center)
            size: Размер логотипа (width, height)
            opacity: Прозрачность (0.0 - 1.0)
        
        Returns:
            Путь к обработанному изображению или None
        """
        try:
            # Открываем изображения
            img = Image.open(image_path)
            logo = Image.open(logo_path)
            
            # Изменяем размер логотипа
            logo = logo.resize(size, Image.Resampling.LANCZOS)
            
            # Применяем прозрачность
            if opacity < 1.0:
                logo = logo.convert("RGBA")
                alpha = logo.split()[3]
                alpha = alpha.point(lambda p: int(p * opacity))
                logo.putalpha(alpha)
            
            # Определяем позицию
            img_width, img_height = img.size
            logo_width, logo_height = logo.size
            
            positions = {
                "top_left": (10, 10),
                "top_right": (img_width - logo_width - 10, 10),
                "bottom_left": (10, img_height - logo_height - 10),
                "bottom_right": (img_width - logo_width - 10, img_height - logo_height - 10),
                "center": ((img_width - logo_width) // 2, (img_height - logo_height) // 2)
            }
            
            pos = positions.get(position, positions["bottom_right"])
            
            # Вставляем логотип
            if logo.mode == "RGBA":
                img.paste(logo, pos, logo)
            else:
                img.paste(logo, pos)
            
            # Сохраняем
            output_path = image_path.parent / f"{image_path.stem}_with_logo{image_path.suffix}"
            img.save(output_path)
            
            logger.info(f"Логотип добавлен на изображение: {output_path}")
            return output_path
        
        except Exception as e:
            logger.exception(f"Ошибка при добавлении логотипа: {e}")
            return None
    
    async def resize_for_platform(
        self,
        image_path: Path,
        platform: str
    ) -> Optional[Path]:
        """
        Изменяет размер изображения под платформу
        
        Args:
            image_path: Путь к исходному изображению
            platform: Платформа (telegram, vk, instagram, facebook, twitter)
        
        Returns:
            Путь к обработанному изображению или None
        """
        # Размеры для разных платформ
        platform_sizes = {
            "telegram": (1024, 1024),
            "vk": (1200, 1200),
            "instagram": (1080, 1080),
            "instagram_story": (1080, 1920),
            "facebook": (1200, 630),
            "twitter": (1200, 675)
        }
        
        target_size = platform_sizes.get(platform.lower(), (1024, 1024))
        
        try:
            img = Image.open(image_path)
            
            # Изменяем размер с сохранением пропорций
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
            
            # Создаем новое изображение нужного размера
            new_img = Image.new("RGB", target_size, (255, 255, 255))
            
            # Вставляем изображение по центру
            img_width, img_height = img.size
            x = (target_size[0] - img_width) // 2
            y = (target_size[1] - img_height) // 2
            new_img.paste(img, (x, y))
            
            # Сохраняем
            output_path = image_path.parent / f"{image_path.stem}_{platform}{image_path.suffix}"
            new_img.save(output_path)
            
            logger.info(f"Изображение изменено под {platform}: {output_path}")
            return output_path
        
        except Exception as e:
            logger.exception(f"Ошибка при изменении размера изображения: {e}")
            return None
    
    async def create_collage(
        self,
        image_paths: List[Path],
        layout: str = "grid",
        output_size: Tuple[int, int] = (1080, 1080)
    ) -> Optional[Path]:
        """
        Создает коллаж из нескольких изображений
        
        Args:
            image_paths: Список путей к изображениям
            layout: Расположение (grid, horizontal, vertical)
            output_size: Размер выходного изображения
        
        Returns:
            Путь к коллажу или None
        """
        try:
            if not image_paths:
                return None
            
            images = []
            for path in image_paths:
                if path.exists():
                    img = Image.open(path)
                    images.append(img)
            
            if not images:
                return None
            
            if layout == "grid":
                # Сетка 2x2 или 3x3
                cols = 2 if len(images) <= 4 else 3
                rows = (len(images) + cols - 1) // cols
                
                cell_width = output_size[0] // cols
                cell_height = output_size[1] // rows
                
                collage = Image.new("RGB", output_size, (255, 255, 255))
                
                for i, img in enumerate(images[:cols * rows]):
                    row = i // cols
                    col = i % cols
                    
                    # Изменяем размер изображения
                    img.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
                    
                    # Позиция
                    x = col * cell_width + (cell_width - img.width) // 2
                    y = row * cell_height + (cell_height - img.height) // 2
                    
                    collage.paste(img, (x, y))
            
            elif layout == "horizontal":
                # Горизонтальное расположение
                total_width = sum(img.width for img in images)
                max_height = max(img.height for img in images)
                
                collage = Image.new("RGB", (total_width, max_height), (255, 255, 255))
                x = 0
                for img in images:
                    y = (max_height - img.height) // 2
                    collage.paste(img, (x, y))
                    x += img.width
            
            elif layout == "vertical":
                # Вертикальное расположение
                max_width = max(img.width for img in images)
                total_height = sum(img.height for img in images)
                
                collage = Image.new("RGB", (max_width, total_height), (255, 255, 255))
                y = 0
                for img in images:
                    x = (max_width - img.width) // 2
                    collage.paste(img, (x, y))
                    y += img.height
            
            # Сохраняем
            output_path = image_paths[0].parent / f"collage_{len(images)}_images{image_paths[0].suffix}"
            collage.save(output_path)
            
            logger.info(f"Коллаж создан: {output_path}")
            return output_path
        
        except Exception as e:
            logger.exception(f"Ошибка при создании коллажа: {e}")
            return None


# Глобальный экземпляр
image_processing_service = ImageProcessingService()
