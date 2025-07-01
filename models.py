#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модели данных для Auto Montage Builder Pro
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Tuple, Optional, Any, Union
from pathlib import Path
import json
import time
import logging

logger = logging.getLogger(__name__)

# ==================== ENUMS ====================

class TransitionType(Enum):
    FADE = "fade"
    DISSOLVE = "dissolve"
    DIP_BLACK = "dip_black"
    DIP_WHITE = "dip_white"
    WIPE = "wipe"
    SLIDE = "slide"
    PUSH = "push"
    ZOOM = "zoom"
    BLUR = "blur"
    PIXELATE = "pixelate"
    GLITCH = "glitch"
    ROTATE = "rotate"
    SQUEEZE = "squeeze"
    MORPH = "morph"

class KenBurnsEffect(Enum):
    ZOOM_IN = "zoomIn"
    ZOOM_OUT = "zoomOut"
    PAN_LEFT = "panLeft"
    PAN_RIGHT = "panRight"
    PAN_UP = "panUp"
    PAN_DOWN = "panDown"
    ROTATE = "rotate"
    DIAGONAL = "diagonal"
    ZOOM_ROTATE = "zoomRotate"
    PARALLAX = "parallax"
    SPIRAL = "spiral"
    SHAKE = "shake"

class CapCutEffect(Enum):
    ZOOM_BURST = "zoomBurst"
    PULSE = "pulse"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    WAVE = "wave"
    GLITCH = "glitch"
    SHAKE = "shake"
    WOBBLE = "wobble"
    PENDULUM = "pendulum"
    SWING = "swing"
    SPIN = "spin"
    FLIP = "flip"
    ZOOM_BLUR = "zoomBlur"
    CHROMATIC = "chromatic"
    RGB_SPLIT = "rgbSplit"
    DISTORTION = "distortion"

# ==================== МОДЕЛИ ДАННЫХ ====================

@dataclass
class VideoQuality:
    """Настройки качества видео"""
    preset: str = "medium"  # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    crf: int = 23  # 0-51, меньше = лучше качество
    profile: str = "high"  # baseline, main, high
    level: str = "4.2"
    pixel_format: str = "yuv420p"
    color_space: str = "bt709"
    color_range: str = "tv"  # tv, pc
    
    def validate(self):
        """Валидация параметров качества"""
        valid_presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        if self.preset not in valid_presets:
            self.preset = "medium"
        
        self.crf = max(0, min(51, self.crf))
        
        valid_profiles = ["baseline", "main", "high"]
        if self.profile not in valid_profiles:
            self.profile = "high"
    
@dataclass
class ExportSettings:
    """Настройки экспорта видео"""
    resolution: str = "1920x1080"
    custom_width: int = 1920
    custom_height: int = 1080
    fps: int = 30
    bitrate: int = 8
    codec: str = "h264"
    quality: VideoQuality = field(default_factory=VideoQuality)
    use_gpu: bool = True
    gpu_type: str = "auto"  # auto, nvidia, amd, intel
    two_pass: bool = False
    audio_bitrate: int = 192
    audio_codec: str = "aac"
    container: str = "mp4"
    
    def get_resolution(self) -> Tuple[int, int]:
        """Получает разрешение в виде кортежа"""
        if self.resolution == "custom":
            return (self.custom_width, self.custom_height)
        
        resolution_map = {
            "1920x1080": (1920, 1080),
            "3840x2160": (3840, 2160),
            "2560x1440": (2560, 1440),
            "1280x720": (1280, 720),
            "1080x1920": (1080, 1920),  # Вертикальное
            "1080x1080": (1080, 1080),  # Квадрат
            "720x1280": (720, 1280),    # Shorts
        }
        return resolution_map.get(self.resolution, (1920, 1080))
    
    def validate(self):
        """Валидация настроек экспорта"""
        self.custom_width = max(320, min(7680, self.custom_width))
        self.custom_height = max(240, min(4320, self.custom_height))
        self.fps = max(1, min(120, self.fps))
        self.bitrate = max(1, min(100, self.bitrate))
        self.audio_bitrate = max(64, min(320, self.audio_bitrate))
        self.quality.validate()

@dataclass
class EffectSettings:
    """Настройки эффектов"""
    # Ken Burns эффекты
    ken_burns: List[str] = field(default_factory=list)
    ken_burns_intensity: int = 30
    rotation_angle: int = 5
    smart_crop: bool = True
    kb_randomize: bool = False
    kb_smooth_factor: float = 0.7  # Фактор сглаживания для плавности
    kb_ease_type: str = "ease-in-out"
    
    # Переходы
    transitions: List[str] = field(default_factory=lambda: ["fade"])
    transition_duration: float = 1.0
    trans_randomize: bool = False
    trans_overlap: float = 0.5  # Перекрытие переходов
    
    # Fade эффекты
    fade_in_from_black: bool = False
    fade_in_duration: float = 1.0
    fade_in_type: str = "ease"
    fade_out_to_black: bool = False
    fade_out_duration: float = 1.0
    fade_out_type: str = "ease"
    add_black_frame: bool = True
    
    # Цветокоррекция
    color_correction: bool = False
    color_filter: str = "none"
    vignette: bool = False
    vignette_intensity: int = 40
    grain: bool = False
    grain_intensity: int = 20
    blur_edges: bool = False
    blur_intensity: int = 30
    
    # Аудио
    audio_pitch: str = "0"
    audio_effect: str = "none"
    audio_stereo_enhance: bool = False
    audio_normalize: bool = True
    audio_compressor: bool = False
    audio_limiter: bool = False
    
    # Анимация
    easing_type: str = "ease"
    bezier_p1: int = 25
    bezier_p2: int = 75
    motion_blur: bool = False
    motion_blur_amount: int = 20
    
    # 3D Parallax
    enable_3d_parallax: bool = False
    parallax_depth_layers: int = 3
    parallax_speed: float = 1.0
    parallax_direction: str = "horizontal"
    parallax_depth_estimation: bool = False
    
    # CapCut эффекты
    capcut_effects: List[str] = field(default_factory=list)
    scale_amplitude: int = 15
    zoom_burst_start: int = 150
    zoom_burst_decay: int = 80
    motion_effects: List[str] = field(default_factory=list)
    motion_intensity: int = 30
    effect_frequency: str = "all"
    effect_percent: int = 50
    effect_every: int = 3
    avoid_repetition: bool = True
    capcut_timing: str = "start"  # start, middle, end, random
    
    def validate(self):
        """Валидация настроек эффектов"""
        # Валидация интенсивностей
        self.ken_burns_intensity = max(0, min(100, self.ken_burns_intensity))
        self.rotation_angle = max(0, min(90, self.rotation_angle))
        self.kb_smooth_factor = max(0.0, min(1.0, self.kb_smooth_factor))
        
        # Валидация длительностей
        self.transition_duration = max(0.1, min(5.0, self.transition_duration))
        self.trans_overlap = max(0.0, min(1.0, self.trans_overlap))
        self.fade_in_duration = max(0.1, min(5.0, self.fade_in_duration))
        self.fade_out_duration = max(0.1, min(5.0, self.fade_out_duration))
        
        # Валидация цветокоррекции
        self.vignette_intensity = max(0, min(100, self.vignette_intensity))
        self.grain_intensity = max(0, min(100, self.grain_intensity))
        self.blur_intensity = max(0, min(100, self.blur_intensity))
        
        # Валидация CapCut
        self.scale_amplitude = max(0, min(100, self.scale_amplitude))
        self.zoom_burst_start = max(100, min(300, self.zoom_burst_start))
        self.zoom_burst_decay = max(0, min(100, self.zoom_burst_decay))
        self.motion_intensity = max(0, min(100, self.motion_intensity))
        self.effect_percent = max(0, min(100, self.effect_percent))
        self.effect_every = max(1, min(10, self.effect_every))
        
        # Валидация эффектов
        self._validate_effect_lists()
    
    def _validate_effect_lists(self):
        """Валидация списков эффектов"""
        valid_ken_burns = [e.value for e in KenBurnsEffect]
        valid_transitions = [t.value for t in TransitionType]
        valid_capcut = [c.value for c in CapCutEffect]
        
        self.ken_burns = [e for e in self.ken_burns if e in valid_ken_burns]
        self.transitions = [t for t in self.transitions if t in valid_transitions]
        if not self.transitions:
            self.transitions = ["fade"]
        
        self.capcut_effects = [c for c in self.capcut_effects if c in valid_capcut]
        self.motion_effects = [m for m in self.motion_effects if m in valid_capcut]

@dataclass
class OverlaySettings:
    """Настройки оверлеев"""
    enabled: bool = False
    folder: str = ""
    files: List[str] = field(default_factory=list)
    blend_mode: str = "screen"
    opacity: int = 100
    randomize: bool = False
    stretch: bool = True
    position: str = "center"  # center, top-left, top-right, bottom-left, bottom-right
    scale: int = 100
    rotation: int = 0
    animate: bool = False
    animation_type: str = "fade"  # fade, slide, zoom, rotate
    
    def validate(self):
        """Валидация настроек оверлеев"""
        valid_blend_modes = ["normal", "screen", "overlay", "multiply", "add", "lighten", "darken"]
        if self.blend_mode not in valid_blend_modes:
            self.blend_mode = "screen"
        
        valid_positions = ["center", "top-left", "top-right", "bottom-left", "bottom-right"]
        if self.position not in valid_positions:
            self.position = "center"
        
        self.opacity = max(0, min(100, self.opacity))
        self.scale = max(10, min(200, self.scale))
        self.rotation = max(-180, min(180, self.rotation))

@dataclass
class Channel:
    """Канал для генерации"""
    id: str
    name: str
    description: str = ""
    template: str = "youtube"
    export: ExportSettings = field(default_factory=ExportSettings)
    effects: EffectSettings = field(default_factory=EffectSettings)
    overlays: OverlaySettings = field(default_factory=OverlaySettings)
    
    def validate(self):
        """Полная валидация канала"""
        self.export.validate()
        self.effects.validate()
        self.overlays.validate()
    
    def to_dict(self) -> dict:
        """Преобразует канал в словарь"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Channel':
        """Создает канал из словаря"""
        factory = ChannelFactory()
        return factory.create_from_dict(data)

@dataclass
class MediaPair:
    """Пара медиа + аудио файлов"""
    number: str
    media_type: str  # image, video
    media_file: Path
    audio_file: Path
    duration: Optional[float] = None
    
    def __post_init__(self):
        """Преобразование путей в Path объекты"""
        if not isinstance(self.media_file, Path):
            self.media_file = Path(self.media_file)
        if not isinstance(self.audio_file, Path):
            self.audio_file = Path(self.audio_file)
    
    def validate(self) -> bool:
        """Проверяет существование файлов"""
        return self.media_file.exists() and self.audio_file.exists()

# ==================== ФАБРИКА ====================

class ChannelFactory:
    """Фабрика для безопасного создания объектов Channel"""
    
    def create_from_dict(self, data: dict) -> Channel:
        """Создает Channel из словаря с валидацией"""
        try:
            # Создаем вложенные объекты
            quality = self._create_video_quality(
                data.get("export", {}).get("quality", {})
            )
            
            export_settings = self._create_export_settings(
                data.get("export", {}), quality
            )
            
            effects = self._create_effect_settings(
                data.get("effects", {})
            )
            
            overlays = self._create_overlay_settings(
                data.get("overlays", {})
            )
            
            channel = Channel(
                id=data.get("id", f"channel_{int(time.time())}"),
                name=data.get("name", "Новый канал"),
                description=data.get("description", ""),
                template=data.get("template", "youtube"),
                export=export_settings,
                effects=effects,
                overlays=overlays
            )
            
            # Валидируем созданный канал
            channel.validate()
            return channel
            
        except Exception as e:
            logger.error(f"Ошибка создания канала: {str(e)}")
            # Возвращаем канал по умолчанию
            return self.create_default_channel()
    
    def create_default_channel(self) -> Channel:
        """Создает канал с настройками по умолчанию"""
        channel = Channel(
            id=f"channel_{int(time.time())}",
            name="Канал по умолчанию",
            description="Создан автоматически"
        )
        channel.validate()
        return channel
    
    def create_from_template(self, template_name: str) -> Channel:
        """Создает канал из предустановленного шаблона"""
        templates = {
            "youtube": {
                "name": "YouTube канал",
                "resolution": "1920x1080",
                "fps": 30,
                "bitrate": 8,
                "ken_burns": ["zoomIn", "panRight"],
                "transitions": ["fade", "dissolve"],
                "color_filter": "cinematic"
            },
            "shorts": {
                "name": "Shorts/Reels канал",
                "resolution": "1080x1920",
                "fps": 30,
                "bitrate": 10,
                "ken_burns": ["zoomIn", "zoomOut"],
                "transitions": ["zoom", "slide"],
                "capcut_effects": ["zoomBurst", "shake"]
            },
            "instagram": {
                "name": "Instagram канал",
                "resolution": "1080x1080",
                "fps": 30,
                "bitrate": 6,
                "ken_burns": ["diagonal"],
                "transitions": ["fade"],
                "color_filter": "instagram"
            },
            "cinematic": {
                "name": "Cinematic канал",
                "resolution": "3840x2160",
                "fps": 24,
                "bitrate": 20,
                "ken_burns": ["panLeft", "panRight"],
                "transitions": ["dissolve"],
                "color_filter": "cinematic",
                "vignette": True,
                "grain": True
            }
        }
        
        template = templates.get(template_name, templates["youtube"])
        
        channel = Channel(
            id=f"channel_{int(time.time())}",
            name=template["name"],
            description=f"Создан из шаблона {template_name}",
            template=template_name
        )
        
        # Применяем настройки из шаблона
        channel.export.resolution = template.get("resolution", "1920x1080")
        channel.export.fps = template.get("fps", 30)
        channel.export.bitrate = template.get("bitrate", 8)
        
        if "ken_burns" in template:
            channel.effects.ken_burns = template["ken_burns"]
        if "transitions" in template:
            channel.effects.transitions = template["transitions"]
        if "color_filter" in template:
            channel.effects.color_filter = template["color_filter"]
            channel.effects.color_correction = True
        if "vignette" in template:
            channel.effects.vignette = template["vignette"]
        if "grain" in template:
            channel.effects.grain = template["grain"]
        if "capcut_effects" in template:
            channel.effects.capcut_effects = template["capcut_effects"]
        
        channel.validate()
        return channel
    
    def _create_video_quality(self, data: dict) -> VideoQuality:
        """Создает VideoQuality с безопасными значениями"""
        quality = VideoQuality(
            preset=data.get("preset", "medium"),
            crf=data.get("crf", 23),
            profile=data.get("profile", "high"),
            level=data.get("level", "4.2"),
            pixel_format=data.get("pixel_format", "yuv420p"),
            color_space=data.get("color_space", "bt709"),
            color_range=data.get("color_range", "tv")
        )
        quality.validate()
        return quality
    
    def _create_export_settings(self, data: dict, quality: VideoQuality) -> ExportSettings:
        """Создает ExportSettings с валидацией"""
        export = ExportSettings(
            resolution=data.get("resolution", "1920x1080"),
            custom_width=data.get("custom_width", 1920),
            custom_height=data.get("custom_height", 1080),
            fps=data.get("fps", 30),
            bitrate=data.get("bitrate", 8),
            codec=data.get("codec", "h264"),
            quality=quality,
            use_gpu=data.get("use_gpu", True),
            gpu_type=data.get("gpu_type", "auto"),
            two_pass=data.get("two_pass", False),
            audio_bitrate=data.get("audio_bitrate", 192),
            audio_codec=data.get("audio_codec", "aac"),
            container=data.get("container", "mp4")
        )
        export.validate()
        return export
    
    def _create_effect_settings(self, data: dict) -> EffectSettings:
        """Создает EffectSettings с валидацией"""
        effects = EffectSettings(
            # Ken Burns
            ken_burns=data.get("ken_burns", []),
            ken_burns_intensity=data.get("ken_burns_intensity", 30),
            rotation_angle=data.get("rotation_angle", 5),
            smart_crop=data.get("smart_crop", True),
            kb_randomize=data.get("kb_randomize", False),
            kb_smooth_factor=data.get("kb_smooth_factor", 0.7),
            kb_ease_type=data.get("kb_ease_type", "ease-in-out"),
            
            # Переходы
            transitions=data.get("transitions", ["fade"]),
            transition_duration=data.get("transition_duration", 1.0),
            trans_randomize=data.get("trans_randomize", False),
            trans_overlap=data.get("trans_overlap", 0.5),
            
            # Fade эффекты
            fade_in_from_black=data.get("fade_in_from_black", False),
            fade_in_duration=data.get("fade_in_duration", 1.0),
            fade_in_type=data.get("fade_in_type", "ease"),
            fade_out_to_black=data.get("fade_out_to_black", False),
            fade_out_duration=data.get("fade_out_duration", 1.0),
            fade_out_type=data.get("fade_out_type", "ease"),
            add_black_frame=data.get("add_black_frame", True),
            
            # Цветокоррекция
            color_correction=data.get("color_correction", False),
            color_filter=data.get("color_filter", "none"),
            vignette=data.get("vignette", False),
            vignette_intensity=data.get("vignette_intensity", 40),
            grain=data.get("grain", False),
            grain_intensity=data.get("grain_intensity", 20),
            blur_edges=data.get("blur_edges", False),
            blur_intensity=data.get("blur_intensity", 30),
            
            # Аудио
            audio_pitch=data.get("audio_pitch", "0"),
            audio_effect=data.get("audio_effect", "none"),
            audio_stereo_enhance=data.get("audio_stereo_enhance", False),
            audio_normalize=data.get("audio_normalize", True),
            audio_compressor=data.get("audio_compressor", False),
            audio_limiter=data.get("audio_limiter", False),
            
            # Анимация
            easing_type=data.get("easing_type", "ease"),
            bezier_p1=data.get("bezier_p1", 25),
            bezier_p2=data.get("bezier_p2", 75),
            motion_blur=data.get("motion_blur", False),
            motion_blur_amount=data.get("motion_blur_amount", 20),
            
            # 3D Parallax
            enable_3d_parallax=data.get("enable_3d_parallax", False),
            parallax_depth_layers=data.get("parallax_depth_layers", 3),
            parallax_speed=data.get("parallax_speed", 1.0),
            parallax_direction=data.get("parallax_direction", "horizontal"),
            parallax_depth_estimation=data.get("parallax_depth_estimation", False),
            
            # CapCut эффекты
            capcut_effects=data.get("capcut_effects", []),
            scale_amplitude=data.get("scale_amplitude", 15),
            zoom_burst_start=data.get("zoom_burst_start", 150),
            zoom_burst_decay=data.get("zoom_burst_decay", 80),
            motion_effects=data.get("motion_effects", []),
            motion_intensity=data.get("motion_intensity", 30),
            effect_frequency=data.get("effect_frequency", "all"),
            effect_percent=data.get("effect_percent", 50),
            effect_every=data.get("effect_every", 3),
            avoid_repetition=data.get("avoid_repetition", True),
            capcut_timing=data.get("capcut_timing", "start")
        )
        effects.validate()
        return effects
    
    def _create_overlay_settings(self, data: dict) -> OverlaySettings:
        """Создает OverlaySettings с валидацией"""
        overlays = OverlaySettings(
            enabled=data.get("enabled", False),
            folder=data.get("folder", ""),
            files=data.get("files", []),
            blend_mode=data.get("blend_mode", "screen"),
            opacity=data.get("opacity", 100),
            randomize=data.get("randomize", False),
            stretch=data.get("stretch", True),
            position=data.get("position", "center"),
            scale=data.get("scale", 100),
            rotation=data.get("rotation", 0),
            animate=data.get("animate", False),
            animation_type=data.get("animation_type", "fade")
        )
        overlays.validate()
        return overlays

# ==================== МЕНЕДЖЕР ДАННЫХ ====================

class DataManager:
    """Менеджер для работы с сохранением и загрузкой данных"""
    
    def __init__(self, app_dir: Path = None):
        if app_dir is None:
            app_dir = Path(__file__).parent
        self.app_dir = app_dir
        self.channels_file = app_dir / "channels.json"
        self.settings_file = app_dir / "settings.json"
        self.factory = ChannelFactory()
    
    def save_channels(self, channels: List[Channel]) -> bool:
        """Сохраняет каналы в файл"""
        try:
            channels_data = [channel.to_dict() for channel in channels]
            with open(self.channels_file, 'w', encoding='utf-8') as f:
                json.dump(channels_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Сохранено каналов: {len(channels)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения каналов: {str(e)}")
            return False
    
    def load_channels(self) -> List[Channel]:
        """Загружает каналы из файла"""
        channels = []
        
        if self.channels_file.exists():
            try:
                with open(self.channels_file, 'r', encoding='utf-8') as f:
                    channels_data = json.load(f)
                
                for channel_data in channels_data:
                    channel = self.factory.create_from_dict(channel_data)
                    channels.append(channel)
                
                logger.info(f"Загружено каналов: {len(channels)}")
            except Exception as e:
                logger.error(f"Ошибка загрузки каналов: {str(e)}")
        
        # Если нет каналов, создаем канал по умолчанию
        if not channels:
            default_channel = self.factory.create_default_channel()
            channels.append(default_channel)
            self.save_channels(channels)
        
        return channels
    
    def export_channels(self, channels: List[Channel], file_path: str) -> bool:
        """Экспортирует каналы в файл"""
        try:
            channels_data = [channel.to_dict() for channel in channels]
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(channels_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Ошибка экспорта каналов: {str(e)}")
            return False
    
    def import_channels(self, file_path: str) -> List[Channel]:
        """Импортирует каналы из файла"""
        channels = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Поддержка разных форматов
            if isinstance(imported_data, list):
                channels_data = imported_data
            elif isinstance(imported_data, dict) and "channels" in imported_data:
                channels_data = imported_data["channels"]
            else:
                raise ValueError("Неверный формат файла")
            
            for channel_data in channels_data:
                channel = self.factory.create_from_dict(channel_data)
                channels.append(channel)
            
        except Exception as e:
            logger.error(f"Ошибка импорта каналов: {str(e)}")
        
        return channels
    
    def save_settings(self, settings: dict) -> bool:
        """Сохраняет настройки приложения"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения настроек: {str(e)}")
            return False
    
    def load_settings(self) -> dict:
        """Загружает настройки приложения"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки настроек: {str(e)}")
        
        return self.get_default_settings()
    
    def get_default_settings(self) -> dict:
        """Возвращает настройки по умолчанию"""
        return {
            "ffmpeg_path": "ffmpeg",
            "use_gpu": True,
            "gpu_type": "auto",
            "two_pass": False,
            "preview_resolution": "480p",
            "safe_filenames": True,
            "keep_temp_files": False,
            "auto_cleanup": False,
            "show_tooltips": True,
            "dark_theme": True,
            "language": "ru"
        }