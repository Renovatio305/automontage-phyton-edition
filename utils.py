#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилиты для Auto Montage Builder Pro
"""

import os
import sys
import json
import shutil
import subprocess
import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# ==================== FFMPEG УТИЛИТЫ ====================

class FFmpegUtils:
    """Утилиты для работы с FFmpeg"""
    
    @staticmethod
    def get_ffmpeg_path() -> str:
        """Получает путь к FFmpeg"""
        # Пытаемся найти в системе
        for cmd in ['ffmpeg', 'ffmpeg.exe']:
            if shutil.which(cmd):
                return cmd
        
        # Проверяем локальную папку
        local_ffmpeg = Path(__file__).parent / 'ffmpeg' / 'ffmpeg.exe'
        if local_ffmpeg.exists():
            return str(local_ffmpeg)
        
        return 'ffmpeg'
    
    @staticmethod
    def get_ffprobe_path() -> str:
        """Получает путь к FFprobe"""
        for cmd in ['ffprobe', 'ffprobe.exe']:
            if shutil.which(cmd):
                return cmd
        
        local_ffprobe = Path(__file__).parent / 'ffmpeg' / 'ffprobe.exe'
        if local_ffprobe.exists():
            return str(local_ffprobe)
        
        return 'ffprobe'
    
    @staticmethod
    def check_ffmpeg_installed() -> bool:
        """Проверяет установлен ли FFmpeg"""
        try:
            ffmpeg = FFmpegUtils.get_ffmpeg_path()
            result = subprocess.run([ffmpeg, '-version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False
    
    @staticmethod
    def get_ffmpeg_version() -> Optional[str]:
        """Получает версию FFmpeg"""
        try:
            ffmpeg = FFmpegUtils.get_ffmpeg_path()
            result = subprocess.run([ffmpeg, '-version'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                return version_line
        except:
            pass
        return None
    
    @staticmethod
    def check_gpu_support() -> Dict[str, bool]:
        """Проверяет поддержку GPU кодеков"""
        support = {
            'nvidia': False,
            'amd': False,
            'intel': False,
            'videotoolbox': False
        }
        
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        
        try:
            result = subprocess.run([ffmpeg, '-encoders'], 
                                  capture_output=True, text=True)
            encoders = result.stdout
            
            if 'h264_nvenc' in encoders or 'hevc_nvenc' in encoders:
                support['nvidia'] = True
            if 'h264_amf' in encoders:
                support['amd'] = True
            if 'h264_qsv' in encoders:
                support['intel'] = True
            if 'h264_videotoolbox' in encoders:
                support['videotoolbox'] = True
                
        except Exception as e:
            logger.error(f"Ошибка проверки GPU: {str(e)}")
        
        return support
    
    @staticmethod
    def get_media_info(file_path: str) -> Dict[str, Any]:
        """Получает информацию о медиа файле"""
        ffprobe = FFmpegUtils.get_ffprobe_path()
        
        cmd = [
            ffprobe, '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', file_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Ошибка получения информации о файле: {str(e)}")
        
        return {}
    
    @staticmethod
    def get_duration(file_path: str) -> float:
        """Получает длительность медиа файла"""
        info = FFmpegUtils.get_media_info(file_path)
        
        # Пробуем разные способы получения длительности
        if info and 'format' in info and 'duration' in info['format']:
            try:
                return float(info['format']['duration'])
            except:
                pass
        
        if info and 'streams' in info:
            for stream in info['streams']:
                if 'duration' in stream:
                    try:
                        return float(stream['duration'])
                    except:
                        pass
        
        # Альтернативный метод
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        cmd = [ffmpeg, '-i', file_path, '-f', 'null', '-']
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})', result.stderr)
            if duration_match:
                hours = int(duration_match.group(1))
                minutes = int(duration_match.group(2))
                seconds = int(duration_match.group(3))
                centiseconds = int(duration_match.group(4))
                return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        except Exception as e:
            logger.error(f"Ошибка определения длительности: {str(e)}")
        
        return 10.0  # Значение по умолчанию
    
    @staticmethod
    def get_video_resolution(file_path: str) -> Tuple[int, int]:
        """Получает разрешение видео"""
        info = FFmpegUtils.get_media_info(file_path)
        
        if info and 'streams' in info:
            for stream in info['streams']:
                if stream.get('codec_type') == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        return (width, height)
        
        return (1920, 1080)  # По умолчанию
    
    @staticmethod
    def check_filter_available(filter_name: str) -> bool:
        """Проверяет доступность фильтра FFmpeg"""
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        
        try:
            result = subprocess.run([ffmpeg, '-filters'], 
                                  capture_output=True, text=True)
            return filter_name in result.stdout
        except:
            return False

# ==================== ФАЙЛОВЫЕ УТИЛИТЫ ====================

class FileUtils:
    """Утилиты для работы с файлами"""
    
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.bmp', '.tif', '.webp'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv'}
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.aiff', '.m4a', '.flac', '.ogg'}
    SUPPORTED_OVERLAY_FORMATS = {'.png', '.mp4', '.mov', '.gif', '.webm'}
    
    @staticmethod
    def is_image(file_path: Path) -> bool:
        """Проверяет, является ли файл изображением"""
        return file_path.suffix.lower() in FileUtils.SUPPORTED_IMAGE_FORMATS
    
    @staticmethod
    def is_video(file_path: Path) -> bool:
        """Проверяет, является ли файл видео"""
        return file_path.suffix.lower() in FileUtils.SUPPORTED_VIDEO_FORMATS
    
    @staticmethod
    def is_audio(file_path: Path) -> bool:
        """Проверяет, является ли файл аудио"""
        return file_path.suffix.lower() in FileUtils.SUPPORTED_AUDIO_FORMATS
    
    @staticmethod
    def is_overlay(file_path: Path) -> bool:
        """Проверяет, подходит ли файл для оверлея"""
        return file_path.suffix.lower() in FileUtils.SUPPORTED_OVERLAY_FORMATS
    
    @staticmethod
    def get_file_number(file_path: Path) -> Optional[str]:
        """Извлекает номер из имени файла (первые 4 цифры)"""
        name = file_path.name
        if len(name) >= 4 and name[:4].isdigit():
            return name[:4]
        return None
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """Создает безопасное имя файла"""
        # Транслитерация русских символов
        translit_dict = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '',
            'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '',
            'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }
        
        for cyrillic, latin in translit_dict.items():
            filename = filename.replace(cyrillic, latin)
        
        # Удаляем небезопасные символы
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
        filename = re.sub(r'_{2,}', '_', filename)  # Убираем множественные подчеркивания
        
        return filename
    
    @staticmethod
    def ensure_directory(path: Path) -> bool:
        """Создает директорию если она не существует"""
        try:
            path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error(f"Ошибка создания директории {path}: {str(e)}")
            return False
    
    @staticmethod
    def cleanup_old_files(directory: Path, days: int = 7, pattern: str = "*.mp4") -> int:
        """Удаляет старые файлы из директории"""
        import time
        
        count = 0
        current_time = time.time()
        age_seconds = days * 24 * 60 * 60
        
        try:
            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > age_seconds:
                        file_path.unlink()
                        count += 1
                        logger.info(f"Удален старый файл: {file_path}")
        except Exception as e:
            logger.error(f"Ошибка очистки старых файлов: {str(e)}")
        
        return count

# ==================== ВАЛИДАТОРЫ ====================

class Validators:
    """Валидаторы для проверки данных"""
    
    @staticmethod
    def validate_resolution(resolution: str) -> bool:
        """Проверяет корректность разрешения"""
        valid_resolutions = [
            "1920x1080", "3840x2160", "2560x1440", "1280x720",
            "1080x1920", "1080x1080", "720x1280", "custom"
        ]
        return resolution in valid_resolutions
    
    @staticmethod
    def validate_fps(fps: int) -> bool:
        """Проверяет корректность FPS"""
        return 1 <= fps <= 120
    
    @staticmethod
    def validate_bitrate(bitrate: int) -> bool:
        """Проверяет корректность битрейта"""
        return 1 <= bitrate <= 100
    
    @staticmethod
    def validate_audio_pitch(pitch: str) -> bool:
        """Проверяет корректность изменения тональности"""
        valid_pitches = [
            "-3", "-2.5", "-2", "-1.5", "-1", "-0.5", "0",
            "+0.5", "+1", "+1.5", "+2", "+2.5", "+3"
        ]
        return pitch in valid_pitches
    
    @staticmethod
    def validate_audio_effect(effect: str) -> bool:
        """Проверяет корректность аудио эффекта"""
        valid_effects = [
            "none", "bass", "reverb", "echo", "chorus", "telephone",
            "underwater", "radio", "vintage", "distortion", "robot"
        ]
        return effect in valid_effects
    
    @staticmethod
    def validate_easing_type(easing: str) -> bool:
        """Проверяет корректность типа интерполяции"""
        valid_easings = [
            "linear", "ease", "ease-in", "ease-out", "ease-in-out",
            "bounce", "elastic", "back"
        ]
        return easing in valid_easings

# ==================== КОНВЕРТЕРЫ ====================

class Converters:
    """Конвертеры для преобразования данных"""
    
    @staticmethod
    def time_to_seconds(time_str: str) -> float:
        """Преобразует время в формате HH:MM:SS.ms в секунды"""
        match = re.match(r'(\d{2}):(\d{2}):(\d{2})\.(\d{2})', time_str)
        if match:
            hours = int(match.group(1))
            minutes = int(match.group(2))
            seconds = int(match.group(3))
            centiseconds = int(match.group(4))
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        return 0.0
    
    @staticmethod
    def seconds_to_time(seconds: float) -> str:
        """Преобразует секунды в формат HH:MM:SS.ms"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds % 1) * 100)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
    
    @staticmethod
    def bytes_to_human(bytes_size: int) -> str:
        """Преобразует байты в человекочитаемый формат"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.1f} PB"
    
    @staticmethod
    def resolution_to_string(width: int, height: int) -> str:
        """Преобразует разрешение в строку"""
        return f"{width}x{height}"
    
    @staticmethod
    def string_to_resolution(resolution: str) -> Tuple[int, int]:
        """Преобразует строку в разрешение"""
        match = re.match(r'(\d+)x(\d+)', resolution)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return (1920, 1080)

# ==================== СИСТЕМНЫЕ УТИЛИТЫ ====================

class SystemUtils:
    """Системные утилиты"""
    
    @staticmethod
    def get_cpu_count() -> int:
        """Получает количество ядер процессора"""
        try:
            return os.cpu_count() or 1
        except:
            return 1
    
    @staticmethod
    def get_memory_info() -> Dict[str, int]:
        """Получает информацию о памяти"""
        try:
            import psutil
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'used': mem.used,
                'percent': mem.percent
            }
        except ImportError:
            # Если psutil не установлен
            return {
                'total': 0,
                'available': 0,
                'used': 0,
                'percent': 0
            }
    
    @staticmethod
    def get_disk_usage(path: str = '.') -> Dict[str, int]:
        """Получает информацию об использовании диска"""
        try:
            import psutil
            usage = psutil.disk_usage(path)
            return {
                'total': usage.total,
                'used': usage.used,
                'free': usage.free,
                'percent': usage.percent
            }
        except ImportError:
            # Если psutil не установлен
            return {
                'total': 0,
                'used': 0,
                'free': 0,
                'percent': 0
            }
    
    @staticmethod
    def is_windows() -> bool:
        """Проверяет, является ли ОС Windows"""
        return sys.platform.startswith('win')
    
    @staticmethod
    def is_macos() -> bool:
        """Проверяет, является ли ОС macOS"""
        return sys.platform == 'darwin'
    
    @staticmethod
    def is_linux() -> bool:
        """Проверяет, является ли ОС Linux"""
        return sys.platform.startswith('linux')

# ==================== ПРОГРЕСС ====================

class ProgressTracker:
    """Отслеживание прогресса операций"""
    
    def __init__(self, total_steps: int = 100):
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = None
        self.callbacks = []
    
    def add_callback(self, callback):
        """Добавляет callback для уведомления о прогрессе"""
        self.callbacks.append(callback)
    
    def start(self):
        """Начинает отслеживание"""
        import time
        self.start_time = time.time()
        self.current_step = 0
        self._notify(0, "Начало операции")
    
    def update(self, step: int, message: str = ""):
        """Обновляет прогресс"""
        self.current_step = min(step, self.total_steps)
        percent = (self.current_step / self.total_steps) * 100
        self._notify(percent, message)
    
    def increment(self, message: str = ""):
        """Увеличивает прогресс на один шаг"""
        self.update(self.current_step + 1, message)
    
    def finish(self, message: str = "Операция завершена"):
        """Завершает отслеживание"""
        self.update(self.total_steps, message)
        if self.start_time:
            import time
            elapsed = time.time() - self.start_time
            logger.info(f"Операция завершена за {elapsed:.1f} секунд")
    
    def _notify(self, percent: float, message: str):
        """Уведомляет подписчиков о прогрессе"""
        for callback in self.callbacks:
            try:
                callback(percent, message)
            except Exception as e:
                logger.error(f"Ошибка вызова callback прогресса: {str(e)}")
    
    def get_eta(self) -> Optional[float]:
        """Вычисляет оставшееся время"""
        if not self.start_time or self.current_step == 0:
            return None
        
        import time
        elapsed = time.time() - self.start_time
        steps_per_second = self.current_step / elapsed
        remaining_steps = self.total_steps - self.current_step
        
        if steps_per_second > 0:
            return remaining_steps / steps_per_second
        return None

# ==================== ЛОГИРОВАНИЕ ====================

def setup_logging(log_file: str = 'auto_montage.log', level: int = logging.INFO):
    """Настраивает логирование для приложения"""
    
    # Создаем форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Обработчик для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Отключаем лишние логи от библиотек
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    logger.info("Логирование настроено")