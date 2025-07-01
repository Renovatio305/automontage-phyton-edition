#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генератор FFmpeg фильтров для Auto Montage Builder Pro
"""

import math
import logging
from typing import Dict, List, Tuple, Optional
from models import (
    EffectSettings, TransitionType, KenBurnsEffect, 
    CapCutEffect, OverlaySettings
)
from utils import FFmpegUtils

logger = logging.getLogger(__name__)

class FilterGenerator:
    """Генератор FFmpeg фильтров для эффектов"""
    
    def __init__(self):
        self.available_filters = self._check_available_filters()
    
    def _check_available_filters(self) -> Dict[str, bool]:
        """Проверяет доступные фильтры FFmpeg"""
        filters_to_check = [
            'zoompan', 'scale', 'rotate', 'fade', 'xfade',
            'crop', 'overlay', 'colorchannelmixer', 'curves',
            'eq', 'vignette', 'noise', 'gblur', 'minterpolate',
            'split', 'blend', 'setpts', 'fps', 'format'
        ]
        
        available = {}
        for filter_name in filters_to_check:
            available[filter_name] = FFmpegUtils.check_filter_available(filter_name)
        
        return available
    
    def get_easing_expression(self, easing_type: str, t: str = "t", duration: str = "duration") -> str:
        """Возвращает математическое выражение для easing функции"""
        easing_map = {
            "linear": f"{t}/{duration}",
            "ease": f"(3*pow({t}/{duration},2) - 2*pow({t}/{duration},3))",
            "ease-in": f"pow({t}/{duration},2)",
            "ease-out": f"(1 - pow(1-{t}/{duration},2))",
            "ease-in-out": f"if(lt({t},{duration}/2), 2*pow({t}/{duration},2), 1-2*pow(1-{t}/{duration},2))",
            "bounce": f"if(lt({t},{duration}/2), 2*pow({t}/{duration},2), 1-2*pow(1-{t}/{duration},2))*abs(sin(10*{t}/{duration}))",
            "elastic": f"1-cos(20*{t}/{duration})*exp(-5*{t}/{duration})",
            "back": f"pow({t}/{duration},2)*(2.70158*({t}/{duration})-1.70158)"
        }
        return easing_map.get(easing_type, easing_map["ease"])
    
    def generate_ken_burns_filter(self, effect: str, duration: float, intensity: int, 
                                 resolution: Tuple[int, int], easing: str = "ease",
                                 smooth_factor: float = 0.7) -> str:
        """Генерирует фильтр Ken Burns с улучшенной плавностью"""
        
        if not self.available_filters.get('zoompan', True):
            logger.warning("Фильтр zoompan недоступен")
            return ""
        
        w, h = resolution
        fps = 60  # Увеличиваем FPS для плавности
        total_frames = int(duration * fps)
        
        # Базовый масштаб с учетом интенсивности
        intensity_factor = intensity / 100.0
        
        # Функция плавности
        easing_expr = self.get_easing_expression(easing, "on", str(total_frames))
        
        if effect == KenBurnsEffect.ZOOM_IN.value:
            start_scale = 1.0 + intensity_factor * 0.3
            end_scale = 1.0
            scale_expr = f"{start_scale}-({start_scale}-{end_scale})*{easing_expr}"
            
            filter_parts = [
                f"scale={w*2}:{h*2}:flags=lanczos",
                f"zoompan=z='{scale_expr}':d={total_frames}:x='(iw-ow)/2':y='(ih-oh)/2':s={w}x{h}:fps={fps}"
            ]
            
            # Добавляем интерполяцию только если доступна
            if self.available_filters.get('minterpolate', False):
                filter_parts.append(f"minterpolate=fps={fps}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir")
            
            return ",".join(filter_parts)
        
        elif effect == KenBurnsEffect.ZOOM_OUT.value:
            start_scale = 1.0
            end_scale = 1.0 + intensity_factor * 0.3
            scale_expr = f"{start_scale}+({end_scale}-{start_scale})*{easing_expr}"
            
            filter_parts = [
                f"scale={w*2}:{h*2}:flags=lanczos",
                f"zoompan=z='{scale_expr}':d={total_frames}:x='(iw-ow)/2':y='(ih-oh)/2':s={w}x{h}:fps={fps}"
            ]
            
            if self.available_filters.get('minterpolate', False):
                filter_parts.append(f"minterpolate=fps={fps}:mi_mode=mci")
            
            return ",".join(filter_parts)
        
        elif effect == KenBurnsEffect.PAN_LEFT.value:
            zoom = 1.2 + intensity_factor * 0.2
            pan_distance = intensity_factor * 0.3
            x_expr = f"(iw-ow)*{pan_distance}*(1-{easing_expr})"
            
            return (f"scale={w*2}:{h*2}:flags=lanczos,"
                   f"zoompan=z='{zoom}':d={total_frames}:x='{x_expr}':y='(ih-oh)/2':"
                   f"s={w}x{h}:fps={fps}")
        
        elif effect == KenBurnsEffect.PAN_RIGHT.value:
            zoom = 1.2 + intensity_factor * 0.2
            pan_distance = intensity_factor * 0.3
            x_expr = f"(iw-ow)*{pan_distance}*{easing_expr}"
            
            return (f"scale={w*2}:{h*2}:flags=lanczos,"
                   f"zoompan=z='{zoom}':d={total_frames}:x='{x_expr}':y='(ih-oh)/2':"
                   f"s={w}x{h}:fps={fps}")
        
        elif effect == KenBurnsEffect.ROTATE.value:
            angle = intensity_factor * 15  # До 15 градусов
            rotate_expr = f"{angle}*sin(2*PI*{easing_expr})"
            zoom = 1.3  # Увеличиваем для компенсации поворота
            
            if self.available_filters.get('rotate', True):
                return (f"scale={w*2}:{h*2}:flags=lanczos,"
                       f"rotate={rotate_expr}*PI/180:c=none:ow=rotw(iw):oh=roth(ih),"
                       f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
                       f"crop={w}:{h}")
            else:
                # Fallback без вращения
                return (f"scale={w*2}:{h*2}:flags=lanczos,"
                       f"zoompan=z='{zoom}':d={total_frames}:x='(iw-ow)/2':y='(ih-oh)/2':"
                       f"s={w}x{h}:fps={fps}")
        
        elif effect == KenBurnsEffect.DIAGONAL.value:
            zoom = 1.3 + intensity_factor * 0.2
            pan_amount = intensity_factor * 0.2
            x_expr = f"(iw-ow)*{pan_amount}*{easing_expr}"
            y_expr = f"(ih-oh)*{pan_amount}*{easing_expr}"
            
            return (f"scale={w*2}:{h*2}:flags=lanczos,"
                   f"zoompan=z='{zoom}':d={total_frames}:x='{x_expr}':y='{y_expr}':"
                   f"s={w}x{h}:fps={fps}")
        
        elif effect == KenBurnsEffect.ZOOM_ROTATE.value:
            # Комбинация зума и вращения
            start_scale = 1.0
            end_scale = 1.0 + intensity_factor * 0.3
            scale_expr = f"{start_scale}+({end_scale}-{start_scale})*{easing_expr}"
            angle = intensity_factor * 10
            rotate_expr = f"{angle}*{easing_expr}"
            
            filter_parts = [
                f"scale={w*2}:{h*2}:flags=lanczos",
                f"zoompan=z='{scale_expr}':d={total_frames}:x='(iw-ow)/2':y='(ih-oh)/2':s={w}x{h}:fps={fps}"
            ]
            
            if self.available_filters.get('rotate', True):
                filter_parts.append(f"rotate={rotate_expr}*PI/180:c=none")
            
            return ",".join(filter_parts)
        
        elif effect == KenBurnsEffect.PARALLAX.value:
            # Эффект параллакса через многослойное движение
            zoom = 1.4
            x_expr = f"(iw-ow)/2+sin(2*PI*{easing_expr})*{intensity_factor*50}"
            y_expr = f"(ih-oh)/2+cos(2*PI*{easing_expr})*{intensity_factor*30}"
            
            return (f"scale={w*2}:{h*2}:flags=lanczos,"
                   f"zoompan=z='{zoom}':d={total_frames}:x='{x_expr}':y='{y_expr}':"
                   f"s={w}x{h}:fps={fps}")
        
        return ""
    
    def generate_capcut_filter(self, effect: str, duration: float, settings: EffectSettings,
                              clip_index: int = 0) -> str:
        """Генерирует CapCut-style эффекты"""
        
        if effect == CapCutEffect.ZOOM_BURST.value:
            # Резкий зум с затуханием
            start_scale = settings.zoom_burst_start / 100.0
            decay_time = settings.zoom_burst_decay / 100.0 * duration
            
            # Экспоненциальное затухание для реалистичности
            scale_expr = f"if(lt(t,{decay_time}),{start_scale}*exp(-3*t/{decay_time})+1*(1-exp(-3*t/{decay_time})),1)"
            
            return f"scale=w='iw*({scale_expr})':h='ih*({scale_expr})':eval=frame:flags=lanczos"
        
        elif effect == CapCutEffect.PULSE.value:
            # Пульсация
            amplitude = settings.scale_amplitude / 100.0 * 0.1
            frequency = 2.5  # Пульсаций за клип
            
            scale_expr = f"1+{amplitude}*sin(2*PI*t*{frequency}/{duration})"
            
            return f"scale=w='iw*({scale_expr})':h='ih*({scale_expr})':eval=frame:flags=lanczos"
        
        elif effect == CapCutEffect.BOUNCE.value:
            # Эффект отскока
            amplitude = settings.scale_amplitude / 100.0 * 0.15
            
            # Затухающие колебания
            scale_expr = f"1+{amplitude}*sin(10*PI*t/{duration})*exp(-5*t/{duration})"
            
            return f"scale=w='iw*({scale_expr})':h='ih*({scale_expr})':eval=frame:flags=lanczos"
        
        elif effect == CapCutEffect.SHAKE.value:
            # Тряска камеры
            intensity = settings.motion_intensity / 100.0 * 10
            
            # Случайная тряска с использованием синусов разных частот
            x_shake = f"{intensity}*sin(t*50+{clip_index})"
            y_shake = f"{intensity}*cos(t*37+{clip_index*2})"
            
            return f"crop=w=iw-{intensity*2}:h=ih-{intensity*2}:x='{intensity}+{x_shake}':y='{intensity}+{y_shake}':eval=frame"
        
        elif effect == CapCutEffect.GLITCH.value:
            # Цифровой глитч - безопасная версия
            intensity = settings.motion_intensity / 100.0
            
            # Используем базовые фильтры для имитации глитча
            if self.available_filters.get('split', True) and self.available_filters.get('blend', True):
                return (f"split[main][glitch];"
                       f"[glitch]crop=w=iw:h=ih/3:x=0:y=ih/3,setpts=PTS+{intensity*0.1}[g1];"
                       f"[main][g1]overlay=x={intensity*5}*sin(t*10):y=H/3:enable='mod(t,0.5)'")
            else:
                # Простой fallback
                return f"eq=brightness={1+intensity*0.1}*sin(t*20):eval=frame"
        
        elif effect == CapCutEffect.CHROMATIC.value:
            # Хроматическая аберрация через разделение каналов
            intensity = settings.motion_intensity / 100.0 * 5
            
            if self.available_filters.get('split', True) and self.available_filters.get('colorchannelmixer', True):
                return (f"split=3[r][g][b];"
                       f"[r]colorchannelmixer=1:0:0:0:0:0:0:0:0:0:0:0[red];"
                       f"[g]colorchannelmixer=0:0:0:0:1:0:0:0:0:0:0:0[green];"
                       f"[b]colorchannelmixer=0:0:0:0:0:0:0:0:1:0:0:0[blue];"
                       f"[red]setpts=PTS-{intensity*0.01}/TB[r1];"
                       f"[blue]setpts=PTS+{intensity*0.01}/TB[b1];"
                       f"[r1][green]blend=all_mode=screen[rg];"
                       f"[rg][b1]blend=all_mode=screen")
            else:
                # Простая альтернатива
                return f"eq=saturation=1+{intensity*0.1}*sin(t*5):eval=frame"
        
        elif effect == CapCutEffect.ZOOM_BLUR.value:
            # Радиальное размытие при зуме
            intensity = settings.motion_intensity / 100.0
            
            zoom_expr = f"1+0.1*sin(2*PI*t/{duration})"
            
            # Комбинируем зум с размытием если доступно
            if self.available_filters.get('gblur', False):
                return (f"scale=w='iw*({zoom_expr})':h='ih*({zoom_expr})':eval=frame,"
                       f"gblur=sigma={intensity*5}*abs(sin(2*PI*t/{duration})):steps=1")
            else:
                return f"scale=w='iw*({zoom_expr})':h='ih*({zoom_expr})':eval=frame"
        
        elif effect == CapCutEffect.WOBBLE.value:
            # Покачивание
            amplitude = settings.motion_intensity / 100.0 * 0.05
            
            wobble_expr = f"1+{amplitude}*sin(4*PI*t/{duration})*cos(2*PI*t/{duration})"
            
            return f"scale=w='iw*({wobble_expr})':h='ih':eval=frame"
        
        elif effect == CapCutEffect.SPIN.value:
            # Вращение
            if self.available_filters.get('rotate', True):
                speed = settings.motion_intensity / 100.0 * 360  # градусов за секунду
                return f"rotate=a={speed}*t*PI/180:c=none:ow=rotw(iw):oh=roth(ih)"
            else:
                return ""
        
        return ""
    
    def generate_transition_filter(self, transition_type: str, duration: float = 1.0) -> Dict[str, str]:
        """Генерирует параметры для переходов между клипами"""
        
        if transition_type == TransitionType.FADE.value:
            return {
                "name": "fade",
                "duration": duration,
                "filter": f"fade=t=out:st=0:d={duration}:alpha=1"
            }
        
        elif transition_type == TransitionType.DISSOLVE.value:
            if self.available_filters.get('xfade', False):
                return {
                    "name": "xfade",
                    "duration": duration,
                    "filter": f"xfade=transition=dissolve:duration={duration}:offset=0"
                }
            else:
                # Fallback на fade
                return self.generate_transition_filter("fade", duration)
        
        elif transition_type == TransitionType.WIPE.value:
            if self.available_filters.get('xfade', False):
                return {
                    "name": "xfade",
                    "duration": duration,
                    "filter": f"xfade=transition=wipeleft:duration={duration}:offset=0"
                }
            else:
                return self.generate_transition_filter("fade", duration)
        
        elif transition_type == TransitionType.SLIDE.value:
            if self.available_filters.get('xfade', False):
                return {
                    "name": "xfade",
                    "duration": duration,
                    "filter": f"xfade=transition=slideright:duration={duration}:offset=0"
                }
            else:
                return self.generate_transition_filter("fade", duration)
        
        elif transition_type == TransitionType.ZOOM.value:
            if self.available_filters.get('xfade', False):
                return {
                    "name": "xfade", 
                    "duration": duration,
                    "filter": f"xfade=transition=zoomin:duration={duration}:offset=0"
                }
            else:
                return self.generate_transition_filter("fade", duration)
        
        elif transition_type == TransitionType.BLUR.value:
            if self.available_filters.get('xfade', False):
                return {
                    "name": "xfade",
                    "duration": duration,
                    "filter": f"xfade=transition=fadeblack:duration={duration}:offset=0"
                }
            else:
                return self.generate_transition_filter("fade", duration)
        
        # По умолчанию - fade
        return {
            "name": "fade",
            "duration": duration,
            "filter": f"fade=t=out:st=0:d={duration}"
        }
    
    def generate_color_correction_filter(self, settings: EffectSettings) -> str:
        """Генерирует фильтр цветокоррекции"""
        filters = []
        
        # Базовые цветовые фильтры
        color_filters = {
            "warm": "colorbalance=rs=0.3:gs=0.1:bs=-0.2",
            "cold": "colorbalance=rs=-0.2:gs=-0.1:bs=0.3",
            "vintage": "curves=preset=vintage,colorbalance=rs=0.3:gs=-0.1:bs=-0.2",
            "blackwhite": "hue=s=0",
            "sepia": "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131",
            "cinematic": "curves=preset=darker,colorbalance=rs=0.2:bs=-0.1",
            "vibrant": "eq=saturation=1.5:contrast=1.2",
            "faded": "eq=saturation=0.7:contrast=0.9",
            "instagram": "curves=preset=lighter,eq=saturation=1.2",
            "film": "curves=preset=vintage"
        }
        
        # Применяем только доступные фильтры
        if settings.color_filter in color_filters:
            filter_cmd = color_filters[settings.color_filter]
            
            # Проверяем доступность фильтров в команде
            if 'colorbalance' in filter_cmd and not self.available_filters.get('colorbalance', True):
                # Используем eq как альтернативу
                if settings.color_filter == "warm":
                    filter_cmd = "eq=saturation=1.2:gamma_r=1.1:gamma_b=0.9"
                elif settings.color_filter == "cold":
                    filter_cmd = "eq=saturation=0.9:gamma_r=0.9:gamma_b=1.1"
            
            if 'curves' in filter_cmd and not self.available_filters.get('curves', True):
                # Упрощаем до базовых настроек
                if settings.color_filter == "vintage":
                    filter_cmd = "eq=saturation=0.8:contrast=0.9:brightness=0.05"
                elif settings.color_filter == "cinematic":
                    filter_cmd = "eq=contrast=1.1:brightness=-0.05"
            
            filters.append(filter_cmd)
        
        # Виньетка
        if settings.vignette and self.available_filters.get('vignette', True):
            intensity = settings.vignette_intensity / 100.0
            filters.append(f"vignette=angle=PI/4*{intensity}:mode=backward")
        elif settings.vignette:
            # Альтернативная виньетка через затемнение краев
            filters.append("boxblur=20:20,format=gray,geq='lum(X,Y)*(1-hypot(2*(X/W-0.5),2*(Y/H-0.5)))'")
        
        # Зерно пленки
        if settings.grain and self.available_filters.get('noise', True):
            intensity = settings.grain_intensity
            filters.append(f"noise=alls={intensity}:allf=t")
        
        # Размытие краев
        if settings.blur_edges and self.available_filters.get('gblur', True):
            intensity = settings.blur_intensity / 100.0 * 20
            filters.append(f"gblur=sigma={intensity}:steps=1")
        
        return ",".join(filters) if filters else ""
    
    def generate_overlay_filter(self, overlay_settings: OverlaySettings, duration: float) -> str:
        """Генерирует фильтр для оверлея"""
        if not overlay_settings.enabled or not overlay_settings.files:
            return ""
        
        # Позиционирование
        position_map = {
            "center": "x=(W-w)/2:y=(H-h)/2",
            "top-left": "x=0:y=0",
            "top-right": "x=W-w:y=0",
            "bottom-left": "x=0:y=H-h",
            "bottom-right": "x=W-w:y=H-h"
        }
        
        position = position_map.get(overlay_settings.position, position_map["center"])
        
        # Режим наложения
        blend_modes = {
            "normal": "",
            "screen": ":blend=screen",
            "overlay": ":blend=overlay",
            "multiply": ":blend=multiply",
            "add": ":blend=addition",
            "lighten": ":blend=lighten",
            "darken": ":blend=darken"
        }
        
        blend = blend_modes.get(overlay_settings.blend_mode, "")
        
        # Строим фильтр
        filters = []
        
        # Масштабирование
        if overlay_settings.scale != 100:
            scale = overlay_settings.scale / 100.0
            filters.append(f"scale=iw*{scale}:ih*{scale}")
        
        # Поворот
        if overlay_settings.rotation != 0 and self.available_filters.get('rotate', True):
            filters.append(f"rotate={overlay_settings.rotation}*PI/180:c=none")
        
        # Прозрачность
        opacity = overlay_settings.opacity / 100.0
        if self.available_filters.get('format', True):
            filters.append(f"format=rgba,colorchannelmixer=aa={opacity}")
        
        # Анимация
        if overlay_settings.animate:
            if overlay_settings.animation_type == "fade":
                filters.append("fade=in:st=0:d=1:alpha=1")
            elif overlay_settings.animation_type == "slide":
                position = f"{position}:x='if(lt(t,2),W-w*t/2,x)':eval=frame"
            elif overlay_settings.animation_type == "zoom":
                filters.append("scale=w='iw*(1+0.1*sin(t))':h='ih*(1+0.1*sin(t))':eval=frame")
        
        overlay_filter = ','.join(filters) if filters else "null"
        
        # Возвращаем полный фильтр overlay
        return f"{overlay_filter}[ov];[ov]overlay={position}{blend}"
    
    def generate_fade_filter(self, fade_type: str, duration: float, start_time: float = 0) -> str:
        """Генерирует fade фильтр"""
        if fade_type == "in":
            return f"fade=t=in:st={start_time}:d={duration}"
        elif fade_type == "out":
            return f"fade=t=out:st={start_time}:d={duration}"
        else:
            return ""
    
    def generate_audio_filter(self, settings: EffectSettings) -> str:
        """Генерирует аудио фильтры"""
        filters = []
        
        # Изменение тональности
        if settings.audio_pitch != "0":
            try:
                semitones = float(settings.audio_pitch)
                # Проверяем доступность rubberband
                if FFmpegUtils.check_filter_available("rubberband"):
                    filters.append(f"rubberband=pitch={semitones}")
                else:
                    # Fallback на простой метод
                    rate_multiplier = 2 ** (semitones / 12)
                    filters.append(f"asetrate=44100*{rate_multiplier},aresample=44100")
            except ValueError:
                pass
        
        # Добавляем эффекты
        effect_filters = {
            "bass": "bass=g=10:f=100",
            "reverb": "aecho=0.8:0.9:40:0.4",
            "echo": "aecho=0.8:0.7:60:0.5",
            "chorus": "chorus=0.5:0.9:50|60|40:0.4|0.32|0.3:0.25|0.4|0.3:2|2.3|1.3",
            "telephone": "highpass=f=300,lowpass=f=3000",
            "underwater": "lowpass=f=500,aecho=0.8:0.9:1000:0.3",
            "radio": "highpass=f=300,lowpass=f=3000,aecho=0.8:0.7:40:0.25",
            "vintage": "lowpass=f=8000,aecho=0.6:0.8:60:0.35",
            "distortion": "acompressor=threshold=0.5:ratio=5:attack=10",
            "robot": "afftfilt=real='re * (1-clip((b/nb)*b,0,1))':imag='im * (1-clip((b/nb)*b,0,1))'"
        }
        
        if settings.audio_effect in effect_filters:
            effect_filter = effect_filters[settings.audio_effect]
            # Проверяем доступность сложных фильтров
            if 'afftfilt' in effect_filter and not FFmpegUtils.check_filter_available('afftfilt'):
                # Используем альтернативу для robot
                effect_filter = "aecho=0.8:0.8:5:0.7,aecho=0.8:0.8:11:0.5"
            
            filters.append(effect_filter)
        
        # Стерео расширение
        if settings.audio_stereo_enhance and FFmpegUtils.check_filter_available('stereotools'):
            filters.append("stereotools=slev=1.5:sbal=0")
        
        # Компрессор
        if settings.audio_compressor:
            filters.append("acompressor=threshold=0.1:ratio=4:attack=5:release=50")
        
        # Лимитер
        if settings.audio_limiter:
            filters.append("alimiter=limit=0.95:attack=5:release=50")
        
        # Нормализация (всегда последняя)
        if settings.audio_normalize:
            if FFmpegUtils.check_filter_available('loudnorm'):
                filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            else:
                # Простая нормализация
                filters.append("volume=0.9")
        
        return ",".join(filters) if filters else "anull"
    
    def get_codec_params(self, export_settings, gpu_support: Dict[str, bool], include_audio: bool = True) -> List[str]:
        """Получает параметры кодека для экспорта"""
        params = []
        
        # Выбор кодека
        if export_settings.use_gpu and export_settings.gpu_type == "auto":
            # Автоопределение GPU
            if gpu_support.get('nvidia', False):
                params.extend(['-c:v', 'h264_nvenc'])
                params.extend(['-preset', 'p4', '-tune', 'hq'])
                params.extend(['-rc', 'vbr', '-cq', str(export_settings.quality.crf)])
            elif gpu_support.get('amd', False):
                params.extend(['-c:v', 'h264_amf'])
                params.extend(['-quality', 'balanced'])
                params.extend(['-rc', 'cqp', '-qp_i', str(export_settings.quality.crf)])
            elif gpu_support.get('intel', False):
                params.extend(['-c:v', 'h264_qsv'])
                params.extend(['-preset', 'medium'])
                params.extend(['-global_quality', str(export_settings.quality.crf)])
            else:
                # CPU fallback
                params.extend(['-c:v', 'libx264'])
                params.extend(['-preset', export_settings.quality.preset])
                params.extend(['-crf', str(export_settings.quality.crf)])
        else:
            # CPU кодирование
            params.extend(['-c:v', 'libx264'])
            params.extend(['-preset', export_settings.quality.preset])
            params.extend(['-crf', str(export_settings.quality.crf)])
        
        # Битрейт
        params.extend([
            '-b:v', f'{export_settings.bitrate}M',
            '-maxrate', f'{export_settings.bitrate + 2}M',
            '-bufsize', f'{export_settings.bitrate * 2}M'
        ])
        
        # Профиль и уровень
        if export_settings.codec == 'h264' and 'nvenc' not in ' '.join(params):
            params.extend(['-profile:v', export_settings.quality.profile])
            params.extend(['-level', export_settings.quality.level])
        
        # Пиксельный формат и цветовое пространство
        params.extend(['-pix_fmt', export_settings.quality.pixel_format])
        
        if export_settings.quality.color_space:
            params.extend(['-colorspace', export_settings.quality.color_space])
        
        if export_settings.quality.color_range:
            params.extend(['-color_range', export_settings.quality.color_range])
        
        # Аудио кодек (только если нужно)
        if include_audio:
            params.extend([
                '-c:a', export_settings.audio_codec,
                '-b:a', f'{export_settings.audio_bitrate}k'
            ])
        
        return params