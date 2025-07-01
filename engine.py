#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Движок монтажа для Auto Montage Builder Pro
"""

import os
import time
import random
import shutil
import tempfile
import subprocess
import logging
from typing import Dict, List, Tuple, Optional, Callable
from pathlib import Path
from dataclasses import dataclass

from models import (
    Channel, MediaPair, EffectSettings, ExportSettings,
    OverlaySettings, KenBurnsEffect, CapCutEffect, TransitionType
)
from utils import (
    FFmpegUtils, FileUtils, ProgressTracker, 
    SystemUtils, Converters
)
from filters import FilterGenerator

logger = logging.getLogger(__name__)

@dataclass
class VideoClip:
    """Информация о видеоклипе"""
    video_path: str
    audio_path: str
    duration: float
    is_first: bool = False
    is_last: bool = False
    effects_applied: Dict[str, str] = None
    
    def __post_init__(self):
        if self.effects_applied is None:
            self.effects_applied = {}

class MontageEngine:
    """Основной движок для создания монтажа"""
    
    def __init__(self, project_folder: str):
        self.project_folder = Path(project_folder)
        self.audio_variants_folder = self.project_folder / "audio_variants"
        self.renders_folder = self.project_folder / "renders"
        self.temp_folder = Path(tempfile.gettempdir()) / "automontage" / f"session_{int(time.time())}"
        
        # Создаем необходимые папки
        FileUtils.ensure_directory(self.audio_variants_folder)
        FileUtils.ensure_directory(self.renders_folder)
        FileUtils.ensure_directory(self.temp_folder)
        
        self.media_pairs: List[MediaPair] = []
        self.progress_tracker = ProgressTracker()
        self.gpu_support = FFmpegUtils.check_gpu_support()
        self.filter_generator = FilterGenerator()
        
        # Проверяем FFmpeg
        if not FFmpegUtils.check_ffmpeg_installed():
            logger.error("FFmpeg не найден!")
            raise RuntimeError("FFmpeg не установлен или не найден в системе")
    
    def set_progress_callback(self, callback: Callable[[float, str], None]):
        """Устанавливает callback для отслеживания прогресса"""
        self.progress_tracker.add_callback(callback)
    
    def scan_project_folder(self, include_videos: bool = True) -> Dict[str, int]:
        """Сканирует папку проекта и находит пары файлов"""
        logger.info(f"Сканирование папки: {self.project_folder}")
        
        images, videos, audio = 0, 0, 0
        media_files = {}
        audio_files = {}
        
        for file_path in self.project_folder.iterdir():
            if not file_path.is_file():
                continue
            
            # Определяем тип файла
            if FileUtils.is_image(file_path):
                images += 1
                number = FileUtils.get_file_number(file_path)
                if number:
                    media_files[number] = {'type': 'image', 'path': file_path}
            elif include_videos and FileUtils.is_video(file_path):
                videos += 1
                number = FileUtils.get_file_number(file_path)
                if number:
                    media_files[number] = {'type': 'video', 'path': file_path}
            elif FileUtils.is_audio(file_path):
                audio += 1
                number = FileUtils.get_file_number(file_path)
                if number:
                    audio_files[number] = file_path
        
        # Создаем пары
        self.media_pairs = []
        for number in sorted(media_files.keys()):
            if number in audio_files:
                pair = MediaPair(
                    number=number,
                    media_type=media_files[number]['type'],
                    media_file=media_files[number]['path'],
                    audio_file=audio_files[number]
                )
                if pair.validate():
                    self.media_pairs.append(pair)
                else:
                    logger.warning(f"Пара {number} не прошла валидацию")
        
        result = {
            'images': images,
            'videos': videos,
            'audio': audio,
            'pairs': len(self.media_pairs)
        }
        
        logger.info(f"Результаты сканирования: {result}")
        return result
    
    def prepare_audio_variants(self, channels: List[Channel]) -> bool:
        """Подготавливает варианты аудио для всех каналов"""
        logger.info("Подготовка аудио вариантов...")
        
        # Собираем уникальные настройки аудио
        audio_configs = set()
        for channel in channels:
            pitch = channel.effects.audio_pitch
            effect = channel.effects.audio_effect
            audio_configs.add((pitch, effect))
        
        total_files = len(self.media_pairs) * len(audio_configs)
        if total_files == 0:
            return True
        
        self.progress_tracker.start()
        self.progress_tracker.total_steps = total_files
        processed = 0
        
        for pair in self.media_pairs:
            for pitch, effect in audio_configs:
                variant_name = self._get_audio_variant_name(pair.number, pitch, effect)
                variant_path = self.audio_variants_folder / variant_name
                
                if not variant_path.exists():
                    success = self._process_audio(
                        str(pair.audio_file),
                        str(variant_path),
                        pitch,
                        effect
                    )
                    
                    if not success:
                        logger.error(f"Ошибка создания аудио варианта: {variant_path}")
                        return False
                
                processed += 1
                self.progress_tracker.update(
                    processed, 
                    f"Обработка аудио: {processed}/{total_files}"
                )
        
        self.progress_tracker.finish("Аудио варианты подготовлены")
        return True
    
    def generate_channel_montage(self, channel: Channel, test_mode: bool = False) -> Optional[str]:
        """Генерирует монтаж для канала"""
        logger.info(f"Генерация монтажа для канала: {channel.name}")
        
        # Валидация канала
        channel.validate()
        
        pairs_to_use = self.media_pairs[:1] if test_mode else self.media_pairs
        if not pairs_to_use:
            logger.error("Нет пар файлов для обработки")
            return None
        
        # Подготавливаем клипы
        self.progress_tracker.start()
        self.progress_tracker.total_steps = len(pairs_to_use) + 2  # +2 для сборки и финализации
        
        video_clips = []
        resolution = channel.export.get_resolution()
        
        # Генерация эффектов для каждого клипа
        effects_manager = EffectsManager(channel.effects)
        
        for i, pair in enumerate(pairs_to_use):
            logger.info(f"Обработка пары {i+1}/{len(pairs_to_use)}: {pair.number}")
            
            # Получаем аудио файл
            audio_file = self._get_audio_variant(pair, channel.effects)
            if not audio_file:
                logger.error(f"Не найден аудио файл для пары {pair.number}")
                continue
            
            # Получаем длительность аудио
            audio_duration = FFmpegUtils.get_duration(str(audio_file))
            pair.duration = audio_duration
            
            # Выбираем эффекты для клипа
            clip_effects = effects_manager.get_effects_for_clip(i, len(pairs_to_use))
            
            # Создаем видео клип
            video_clip_path = self._create_video_clip(
                pair, audio_duration, resolution, channel, 
                clip_effects, i, len(pairs_to_use)
            )
            
            if video_clip_path and Path(video_clip_path).exists():
                video_clips.append(VideoClip(
                    video_path=video_clip_path,
                    audio_path=str(audio_file),
                    duration=audio_duration,
                    is_first=(i == 0),
                    is_last=(i == len(pairs_to_use) - 1),
                    effects_applied=clip_effects
                ))
            
            self.progress_tracker.increment(
                f"Обработан клип {i+1}/{len(pairs_to_use)}"
            )
        
        if not video_clips:
            logger.error("Не удалось создать ни одного клипа")
            return None
        
        # Собираем финальное видео
        timestamp = int(time.time())
        safe_name = FileUtils.safe_filename(channel.name)
        output_filename = f"{safe_name}_{timestamp}.{channel.export.container}"
        output_path = self.renders_folder / output_filename
        
        self.progress_tracker.update(
            len(pairs_to_use) + 1,
            "Сборка финального видео..."
        )
        
        success = self._combine_clips(video_clips, output_path, channel)
        
        # Очищаем временные файлы
        self._cleanup_temp_files(video_clips)
        
        if success:
            logger.info(f"Монтаж создан: {output_path}")
            self.progress_tracker.finish(f"Завершено: {output_path}")
            return str(output_path)
        else:
            logger.error("Ошибка создания финального видео")
            return None
    
    def _get_audio_variant_name(self, number: str, pitch: str, effect: str) -> str:
        """Генерирует имя для аудио варианта"""
        variant_name = f"{number}_pitch_{pitch.replace('+', 'plus').replace('.', '_')}"
        if effect != "none":
            variant_name += f"_{effect}"
        variant_name += ".mp3"
        return variant_name
    
    def _get_audio_variant(self, pair: MediaPair, effects: EffectSettings) -> Optional[Path]:
        """Получает нужный вариант аудио файла"""
        pitch = effects.audio_pitch
        effect = effects.audio_effect
        
        if pitch == "0" and effect == "none":
            return pair.audio_file
        
        variant_name = self._get_audio_variant_name(pair.number, pitch, effect)
        variant_path = self.audio_variants_folder / variant_name
        return variant_path if variant_path.exists() else pair.audio_file
    
    def _process_audio(self, input_path: str, output_path: str, 
                      pitch: str, effect: str) -> bool:
        """Обрабатывает аудио файл с эффектами"""
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        
        # Создаем временные настройки для генерации фильтров
        temp_settings = EffectSettings(
            audio_pitch=pitch,
            audio_effect=effect,
            audio_normalize=True
        )
        
        audio_filter = self.filter_generator.generate_audio_filter(temp_settings)
        
        cmd = [
            ffmpeg, '-i', input_path,
            '-af', audio_filter,
            '-b:a', '192k',
            '-y', output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Ошибка обработки аудио: {e}")
            return False
    
    def _create_video_clip(self, pair: MediaPair, duration: float, 
                          resolution: Tuple[int, int], channel: Channel, 
                          clip_effects: Dict, clip_index: int, 
                          total_clips: int) -> Optional[str]:
        """Создает видео клип с эффектами"""
        try:
            ffmpeg = FFmpegUtils.get_ffmpeg_path()
            input_path = str(pair.media_file)
            output_path = str(self.temp_folder / f"clip_{pair.number}_{clip_index}.mp4")
            
            # Проверяем существование входного файла
            if not Path(input_path).exists():
                logger.error(f"Входной файл не найден: {input_path}")
                return None
            
            effects = channel.effects
            export = channel.export
            
            # Определяем FPS для плавности
            output_fps = 60 if effects.ken_burns else export.fps
            
            filters = []
            
            # Базовая обработка размера
            if pair.media_type == "image":
                filters.append(
                    f"scale={resolution[0]*2}:{resolution[1]*2}:"
                    f"force_original_aspect_ratio=increase:flags=lanczos"
                )
                
                # CapCut эффект в начале
                if clip_effects.get('capcut_start'):
                    capcut_filter = self.filter_generator.generate_capcut_filter(
                        clip_effects['capcut_start'], duration * 0.3, 
                        effects, clip_index
                    )
                    if capcut_filter:
                        filters.append(capcut_filter)
                
                # Ken Burns эффект
                if clip_effects.get('ken_burns'):
                    kb_filter = self.filter_generator.generate_ken_burns_filter(
                        clip_effects['ken_burns'], duration, 
                        effects.ken_burns_intensity, resolution, 
                        effects.easing_type, effects.kb_smooth_factor
                    )
                    if kb_filter:
                        filters.append(kb_filter)
                else:
                    # Простое масштабирование если нет Ken Burns
                    filters.append(
                        f"scale={resolution[0]}:{resolution[1]}:"
                        f"force_original_aspect_ratio=increase"
                    )
                    filters.append(f"crop={resolution[0]}:{resolution[1]}")
                
                # CapCut эффект в конце
                if clip_effects.get('capcut_end'):
                    # Применяем эффект только к последним 30% клипа
                    end_start = duration * 0.7
                    capcut_filter = self.filter_generator.generate_capcut_filter(
                        clip_effects['capcut_end'], duration * 0.3, 
                        effects, clip_index
                    )
                    if capcut_filter:
                        filters.append(
                            f"split[main][effect];"
                            f"[effect]{capcut_filter},setpts=PTS+{end_start}/TB[effect_delayed];"
                            f"[main][effect_delayed]overlay=enable='gte(t,{end_start})'"
                        )
            else:
                # Для видео
                filters.append(
                    f"scale={resolution[0]}:{resolution[1]}:"
                    f"force_original_aspect_ratio=increase:flags=lanczos"
                )
                filters.append(f"crop={resolution[0]}:{resolution[1]}")
            
            # Цветокоррекция
            if effects.color_correction:
                color_filter = self.filter_generator.generate_color_correction_filter(effects)
                if color_filter:
                    filters.append(color_filter)
            
            # Motion blur для плавности
            if effects.motion_blur and self.filter_generator.available_filters.get('minterpolate', False):
                blur_amount = effects.motion_blur_amount / 100.0
                filters.append(
                    f"minterpolate=fps={output_fps}:mi_mode=mci:"
                    f"mc_mode=aobmc:me_mode=bidir:mb_size={int(8*blur_amount)}"
                )
            
            # Fade эффекты
            if clip_index == 0 and effects.fade_in_from_black:
                fade_filter = self.filter_generator.generate_fade_filter(
                    "in", effects.fade_in_duration
                )
                filters.append(fade_filter)
            
            if clip_index == total_clips - 1 and effects.fade_out_to_black:
                fade_start = max(0, duration - effects.fade_out_duration)
                fade_filter = self.filter_generator.generate_fade_filter(
                    "out", effects.fade_out_duration, fade_start
                )
                filters.append(fade_filter)
            
            # Финальная настройка FPS
            filters.append(f"fps={output_fps}")
            
            # Определяем кодек (без аудио параметров для промежуточных клипов)
            codec_params = self.filter_generator.get_codec_params(export, self.gpu_support, include_audio=False)
            
            # Строим команду FFmpeg
            cmd = [ffmpeg]
            
            if pair.media_type == "image":
                cmd.extend([
                    '-loop', '1',
                    '-framerate', str(output_fps),
                    '-i', input_path,
                    '-t', str(duration)
                ])
            else:
                cmd.extend([
                    '-stream_loop', '-1',
                    '-i', input_path,
                    '-t', str(duration)
                ])
            
            if filters:
                # Объединяем фильтры
                filter_complex = ','.join(filters)
                cmd.extend(['-vf', filter_complex])
            
            # Добавляем параметры кодека
            cmd.extend(codec_params)
            cmd.extend([
                '-movflags', '+faststart',
                '-an',  # без аудио на этом этапе
                '-y', output_path
            ])
            
            logger.debug(f"FFmpeg команда: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            if result.returncode == 0 and Path(output_path).exists():
                logger.info(f"Клип создан: {output_path}")
                return output_path
            else:
                logger.error(f"Ошибка создания клипа: {result.stderr}")
                return None
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Ошибка FFmpeg: {e.stderr}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при создании клипа: {str(e)}")
            return None
    
    def _create_audio_list_file(self, audio_files: List[str], output_dir: Path) -> str:
            """Создает файл списка для concat с правильным форматированием путей"""
            list_file = output_dir / "audio_list.txt"
            
            with open(list_file, 'w', encoding='utf-8') as f:
                for audio_file in audio_files:
                    # Проверяем существование файла
                    if not Path(audio_file).exists():
                        logger.warning(f"Аудиофайл не найден: {audio_file}")
                        continue
                    
                    # Нормализуем путь для Windows
                    normalized_path = Path(audio_file).resolve().as_posix()
                    
                    # Для Windows с абсолютными путями используем протокол file:
                    if Path(audio_file).is_absolute() and os.name == 'nt':
                        # Экранируем путь в одинарных кавычках для concat
                        f.write(f"file 'file:{normalized_path}'\n")
                    else:
                        # Для относительных путей просто используем кавычки
                        f.write(f"file '{normalized_path}'\n")
            
            return str(list_file)

    def _combine_clips(self, clips: List[VideoClip], output_path: Path, 
                      channel: Channel) -> bool:
        """Объединяет клипы в финальное видео с переходами"""
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        
        if len(clips) == 1:
            # Один клип - просто добавляем аудио
            cmd = [
                ffmpeg,
                '-i', clips[0].video_path,
                '-i', clips[0].audio_path,
                '-c:v', 'copy',
                '-c:a', channel.export.audio_codec,
                '-b:a', f'{channel.export.audio_bitrate}k',
                '-shortest',
                '-y', str(output_path)
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False
        
        # Для множественных клипов
        try:
            # Создаем временный список файлов для concat
            video_files = [clip.video_path for clip in clips]
            audio_files = [clip.audio_path for clip in clips]
            
            # Создаем списки с правильным форматированием
            concat_list = self._create_video_list_file(video_files, self.temp_folder)
            audio_list = self._create_audio_list_file(audio_files, self.temp_folder)
            
            # Проверяем, что списки не пустые
            if not Path(concat_list).exists() or Path(concat_list).stat().st_size == 0:
                logger.error("Список видеофайлов пуст или не создан")
                return False
                
            if not Path(audio_list).exists() or Path(audio_list).stat().st_size == 0:
                logger.error("Список аудиофайлов пуст или не создан")
                return False
            
            # Сначала объединяем видео
            temp_video = self.temp_folder / "combined_video.mp4"
            
            cmd_video = [
                ffmpeg,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list,
                '-c', 'copy',
                '-y', str(temp_video)
            ]
            
            logger.debug(f"Команда объединения видео: {' '.join(cmd_video)}")
            result = subprocess.run(cmd_video, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"Ошибка объединения видео: {result.stderr}")
                return False
            
            # Объединяем аудио
            temp_audio = self.temp_folder / "combined_audio.mp3"
            
            cmd_audio = [
                ffmpeg,
                '-f', 'concat',
                '-safe', '0',
                '-i', audio_list,
                '-c', 'copy',
                '-y', str(temp_audio)
            ]
            
            logger.debug(f"Команда объединения аудио: {' '.join(cmd_audio)}")
            result = subprocess.run(cmd_audio, capture_output=True, text=True, encoding='utf-8')
            if result.returncode != 0:
                logger.error(f"Ошибка объединения аудио: {result.stderr}")
                # Попробуем объединить аудио другим способом
                temp_audio = self._merge_audio_alternative(audio_files, self.temp_folder)
                if not temp_audio:
                    return False
            
            # Финальное объединение с переходами
            if channel.effects.transitions and channel.effects.transition_duration > 0:
                # Применяем переходы в отдельном проходе
                success = self._apply_transitions(
                    temp_video, temp_audio, output_path, 
                    clips, channel
                )
            else:
                # Простое объединение
                codec_params = self.filter_generator.get_codec_params(
                    channel.export, self.gpu_support
                )
                
                cmd_final = [
                    ffmpeg,
                    '-i', str(temp_video),
                    '-i', str(temp_audio)
                ]
                
                cmd_final.extend(codec_params)
                cmd_final.extend([
                    '-movflags', '+faststart',
                    '-shortest',
                    '-y', str(output_path)
                ])
                
                result = subprocess.run(cmd_final, capture_output=True, text=True)
                success = result.returncode == 0
            
            # Добавляем черный кадр если нужно
            if success and channel.effects.add_black_frame and channel.effects.fade_out_to_black:
                self._add_black_frame(output_path, channel.export)
            
            # Применяем оверлеи если есть
            if success and channel.overlays.enabled and channel.overlays.files:
                success = self._apply_overlays(output_path, channel.overlays)
            
            return success
            
        except Exception as e:
            logger.error(f"Ошибка объединения клипов: {str(e)}")
            return False

    def _create_video_list_file(self, video_files: List[str], output_dir: Path) -> str:
        """Создает файл списка видео для concat"""
        list_file = output_dir / "concat_list.txt"
        
        with open(list_file, 'w', encoding='utf-8') as f:
            for video_file in video_files:
                if not Path(video_file).exists():
                    logger.warning(f"Видеофайл не найден: {video_file}")
                    continue
                
                # Нормализуем путь
                normalized_path = Path(video_file).resolve().as_posix()
                
                # Для Windows с абсолютными путями
                if Path(video_file).is_absolute() and os.name == 'nt':
                    f.write(f"file 'file:{normalized_path}'\n")
                else:
                    f.write(f"file '{normalized_path}'\n")
        
        return str(list_file)

    def _merge_audio_alternative(self, audio_files: List[str], output_dir: Path) -> Optional[Path]:
        """Альтернативный метод объединения аудио без concat протокола"""
        if not audio_files:
            return None
        
        if len(audio_files) == 1:
            return Path(audio_files[0])
        
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        temp_audio = output_dir / "combined_audio_alt.mp3"
        
        try:
            # Используем filter_complex для объединения
            cmd = [ffmpeg]
            
            # Добавляем все входные файлы
            for audio_file in audio_files:
                cmd.extend(['-i', audio_file])
            
            # Создаем filter_complex для конкатенации
            filter_inputs = ''.join(f'[{i}:a]' for i in range(len(audio_files)))
            filter_complex = f'{filter_inputs}concat=n={len(audio_files)}:v=0:a=1[out]'
            
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[out]',
                '-y', str(temp_audio)
            ])
            
            logger.debug(f"Альтернативная команда объединения аудио: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
            
            if result.returncode == 0 and temp_audio.exists():
                return temp_audio
            else:
                logger.error(f"Ошибка альтернативного объединения аудио: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка в альтернативном методе объединения аудио: {str(e)}")
            return None
    
    def _apply_transitions(self, video_path: Path, audio_path: Path, 
                          output_path: Path, clips: List[VideoClip], 
                          channel: Channel) -> bool:
        """Применяет переходы между клипами"""
        # Упрощенная версия - используем fade переходы
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        
        try:
            filter_complex = []
            
            # Создаем fade переходы для каждого стыка клипов
            for i in range(len(clips) - 1):
                fade_duration = channel.effects.transition_duration
                clip_end = sum(c.duration for c in clips[:i+1])
                fade_start = clip_end - fade_duration / 2
                
                # Fade out для текущего клипа
                filter_complex.append(
                    f"fade=t=out:st={fade_start}:d={fade_duration/2}:alpha=1"
                )
            
            # Применяем фильтры
            codec_params = self.filter_generator.get_codec_params(
                channel.export, self.gpu_support
            )
            
            cmd = [
                ffmpeg,
                '-i', str(video_path),
                '-i', str(audio_path)
            ]
            
            if filter_complex:
                cmd.extend(['-vf', ','.join(filter_complex)])
            
            cmd.extend(codec_params)
            cmd.extend([
                '-movflags', '+faststart',
                '-shortest',
                '-y', str(output_path)
            ])
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Ошибка применения переходов: {str(e)}")
            return False
    
    def _apply_overlays(self, video_path: Path, overlay_settings: OverlaySettings) -> bool:
        """Применяет оверлеи к видео"""
        if not overlay_settings.files:
            return True
        
        # Выбираем оверлей
        if overlay_settings.randomize:
            overlay_file = random.choice(overlay_settings.files)
        else:
            overlay_file = overlay_settings.files[0]
        
        overlay_path = Path(overlay_settings.folder) / overlay_file
        if not overlay_path.exists():
            logger.warning(f"Файл оверлея не найден: {overlay_path}")
            return True
        
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        temp_output = video_path.with_suffix('.overlay.mp4')
        
        try:
            # Получаем длительность видео
            duration = FFmpegUtils.get_duration(str(video_path))
            
            # Генерируем фильтр оверлея
            overlay_filter = self.filter_generator.generate_overlay_filter(
                overlay_settings, duration
            )
            
            cmd = [
                ffmpeg,
                '-i', str(video_path),
                '-i', str(overlay_path),
                '-filter_complex', f"[1:v]{overlay_filter}",
                '-map', '0:a',
                '-c:a', 'copy',
                '-y', str(temp_output)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                # Заменяем оригинал
                video_path.unlink()
                temp_output.rename(video_path)
                return True
            else:
                logger.error(f"Ошибка применения оверлея: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при работе с оверлеем: {str(e)}")
            return False
    
    def _add_black_frame(self, video_path: Path, export_settings: ExportSettings):
        """Добавляет черный кадр в конец видео"""
        ffmpeg = FFmpegUtils.get_ffmpeg_path()
        temp_output = video_path.with_suffix('.black.mp4')
        
        resolution = export_settings.get_resolution()
        
        cmd = [
            ffmpeg,
            '-i', str(video_path),
            '-f', 'lavfi', '-i', f'color=black:s={resolution[0]}x{resolution[1]}:d=1',
            '-filter_complex', '[0:v][1:v]concat=n=2:v=1[v]',
            '-map', '[v]',
            '-map', '0:a',
            '-c:v', 'libx264',
            '-c:a', 'copy',
            '-y', str(temp_output)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                video_path.unlink()
                temp_output.rename(video_path)
        except Exception as e:
            logger.error(f"Ошибка добавления черного кадра: {str(e)}")
    
    def _cleanup_temp_files(self, clips: List[VideoClip]):
        """Очищает временные файлы"""
        for clip in clips:
            try:
                Path(clip.video_path).unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
        
        # Удаляем временную папку если она пуста
        try:
            if self.temp_folder.exists() and not any(self.temp_folder.iterdir()):
                self.temp_folder.rmdir()
        except:
            pass
    
    def cleanup_old_renders(self, days: int = 7) -> int:
        """Удаляет старые рендеры"""
        return FileUtils.cleanup_old_files(self.renders_folder, days, "*.mp4")


class EffectsManager:
    """Менеджер для управления эффектами"""
    
    def __init__(self, effects_settings: EffectSettings):
        self.settings = effects_settings
        self.used_effects = []
    
    def get_effects_for_clip(self, clip_index: int, total_clips: int) -> Dict[str, Optional[str]]:
        """Выбирает эффекты для конкретного клипа"""
        effects = {
            'ken_burns': None,
            'capcut_start': None,
            'capcut_end': None
        }
        
        # Ken Burns эффект
        if self.settings.ken_burns:
            if self.settings.kb_randomize:
                # Случайный выбор с избеганием повторений
                available = [e for e in self.settings.ken_burns 
                           if e not in self.used_effects[-2:]]
                if not available:
                    available = self.settings.ken_burns
                
                effects['ken_burns'] = random.choice(available)
                self.used_effects.append(effects['ken_burns'])
            else:
                # Последовательный выбор
                effects['ken_burns'] = self.settings.ken_burns[
                    clip_index % len(self.settings.ken_burns)
                ]
        
        # CapCut эффекты
        if self.settings.capcut_effects and self._should_apply_capcut(clip_index):
            all_effects = self.settings.capcut_effects + self.settings.motion_effects
            
            if self.settings.capcut_timing in ["start", "random"]:
                effects['capcut_start'] = random.choice(all_effects)
            
            if self.settings.capcut_timing in ["end", "random"]:
                effects['capcut_end'] = random.choice(all_effects)
            
            if self.settings.capcut_timing == "middle":
                # Для middle выбираем один эффект
                effects['capcut_start'] = random.choice(all_effects)
        
        return effects
    
    def _should_apply_capcut(self, clip_index: int) -> bool:
        """Определяет, нужно ли применять CapCut эффект"""
        if self.settings.effect_frequency == "all":
            return True
        elif self.settings.effect_frequency == "percent":
            return random.randint(1, 100) <= self.settings.effect_percent
        elif self.settings.effect_frequency == "every":
            return (clip_index + 1) % self.settings.effect_every == 0
        elif self.settings.effect_frequency == "random":
            return random.choice([True, False])
        return False