#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Вкладки интерфейса для Auto Montage Builder Pro
"""

import time
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from models import (
    Channel, EffectSettings, ExportSettings, OverlaySettings,
    KenBurnsEffect, CapCutEffect, TransitionType
)
from gui_base import (
    BaseWidget, EffectCheckBox, SliderWithLabel, 
    FilePathSelector, CollapsibleGroupBox, LogWidget
)
from gui_widgets import (
    ProjectInfoPanel, ChannelSelectionPanel, ChannelDialog
)

logger = logging.getLogger(__name__)

# ==================== ВКЛАДКА ГЕНЕРАЦИИ ====================

class GenerationTab(BaseWidget):
    """Вкладка генерации монтажа"""
    
    generate_requested = Signal(list, bool)  # channels, test_mode
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.selected_channel_ids = set()
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Панель проекта
        self.project_panel = ProjectInfoPanel()
        scroll_layout.addWidget(self.project_panel)
        
        # Панель выбора каналов
        self.channel_selection = ChannelSelectionPanel()
        self.channel_selection.selection_changed.connect(self._on_selection_changed)
        scroll_layout.addWidget(self.channel_selection)
        
        # Настройки генерации
        generation_group = CollapsibleGroupBox("⚙️ Настройки генерации")
        generation_layout = QVBoxLayout()
        
        self.process_audio_check = QCheckBox(
            "Автоматически обработать аудио перед генерацией"
        )
        self.process_audio_check.setChecked(True)
        generation_layout.addWidget(self.process_audio_check)
        
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Качество обработки:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Быстро", "Баланс", "Качество", "Максимум"])
        self.quality_combo.setCurrentIndex(1)
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        generation_layout.addLayout(quality_layout)
        
        self.parallel_check = QCheckBox("Параллельная обработка каналов")
        self.parallel_check.setToolTip(
            "Обрабатывать несколько каналов одновременно (требует больше ресурсов)"
        )
        generation_layout.addWidget(self.parallel_check)
        
        generation_group.setLayout(generation_layout)
        scroll_layout.addWidget(generation_group)
        
        # Кнопки действий

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(10)
        
        self.test_btn = QPushButton("🧪 Тест (1 пара)")
        self.test_btn.setToolTip("Создать тестовое видео из первой пары файлов")
        self.test_btn.clicked.connect(self._on_test_clicked)
        actions_layout.addWidget(self.test_btn)
        
        actions_layout.addStretch()
        
        self.generate_btn = QPushButton("🎬 СОЗДАТЬ МОНТАЖ")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.clicked.connect(self._on_generate_clicked)
        self.generate_btn.setEnabled(False)
        actions_layout.addWidget(self.generate_btn)
        
        scroll_layout.addLayout(actions_layout)
        
        # Прогресс
        progress_group = QGroupBox("📊 Прогресс")
        progress_layout = QVBoxLayout()
        
        self.progress_label = QLabel("Готов к работе")
        progress_layout.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        self.eta_label = QLabel("")
        self.eta_label.setObjectName("infoLabel")
        progress_layout.addWidget(self.eta_label)
        
        self.cancel_btn = QPushButton("❌ Отменить")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setVisible(False)
        progress_layout.addWidget(self.cancel_btn)
        
        progress_group.setLayout(progress_layout)
        scroll_layout.addWidget(progress_group)
        
        # Лог
        log_group = CollapsibleGroupBox("📜 Журнал")
        log_layout = QVBoxLayout()
        
        self.log_widget = LogWidget()
        log_layout.addWidget(self.log_widget)
        
        log_buttons = QHBoxLayout()
        clear_log_btn = QPushButton("Очистить")
        clear_log_btn.clicked.connect(self.log_widget.clear_log)
        log_buttons.addWidget(clear_log_btn)
        log_buttons.addStretch()
        log_layout.addLayout(log_buttons)
        
        log_group.setLayout(log_layout)
        scroll_layout.addWidget(log_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self.channel_selection.set_channels(channels)
    
    def get_project_info_panel(self) -> ProjectInfoPanel:
        """Возвращает панель информации о проекте"""
        return self.project_panel
    
    def update_progress(self, value: float, text: str = ""):
        """Обновляет прогресс"""
        self.progress_bar.setValue(int(value))
        if text:
            self.progress_label.setText(text)
        
        # Обновляем ETA если возможно
        if hasattr(self, '_start_time') and value > 0:
            elapsed = time.time() - self._start_time
            if value < 100:
                eta = elapsed * (100 - value) / value
                eta_text = f"Осталось примерно: {self._format_time(eta)}"
                self.eta_label.setText(eta_text)
            else:
                self.eta_label.setText("")
    
    def _format_time(self, seconds: float) -> str:
        """Форматирует время в читаемый вид"""
        if seconds < 60:
            return f"{int(seconds)} сек"
        elif seconds < 3600:
            return f"{int(seconds / 60)} мин {int(seconds % 60)} сек"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours} ч {minutes} мин"
    
    def start_generation(self):
        """Начинает генерацию"""
        self._start_time = time.time()
        self.generate_btn.setEnabled(False)
        self.test_btn.setEnabled(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Начало генерации...")
    
    def finish_generation(self):
        """Завершает генерацию"""
        self.generate_btn.setEnabled(True)
        self.test_btn.setEnabled(True)
        self.cancel_btn.setVisible(False)
        self.eta_label.setText("")
    
    def add_log_message(self, message: str, level: str = "info"):
        """Добавляет сообщение в лог"""
        self.log_widget.add_message(message, level)
    
    def _on_selection_changed(self, selected_ids: set):
        """Обработчик изменения выбора каналов"""
        self.selected_channel_ids = selected_ids
        self.generate_btn.setEnabled(len(selected_ids) > 0)
    
    def _on_test_clicked(self):
        """Обработчик кнопки тестирования"""
        selected_channels = self.channel_selection.get_selected_channels()
        if not selected_channels:
            self.show_warning("Выберите хотя бы один канал для тестирования")
            return
        
        # Берем только первый канал для теста
        self.generate_requested.emit([selected_channels[0]], True)
    
    def _on_generate_clicked(self):
        """Обработчик кнопки генерации"""
        selected_channels = self.channel_selection.get_selected_channels()
        if not selected_channels:
            self.show_warning("Выберите хотя бы один канал для генерации")
            return
        
        # Применяем настройки качества
        quality_map = {
            "Быстро": "veryfast",
            "Баланс": "medium",
            "Качество": "slow",
            "Максимум": "veryslow"
        }
        
        quality_preset = quality_map.get(self.quality_combo.currentText(), "medium")
        for channel in selected_channels:
            channel.export.quality.preset = quality_preset
        
        self.generate_requested.emit(selected_channels, False)
    
    def get_process_audio_setting(self) -> bool:
        """Возвращает настройку обработки аудио"""
        return self.process_audio_check.isChecked()
    
    def get_parallel_processing(self) -> bool:
        """Возвращает настройку параллельной обработки"""
        return self.parallel_check.isChecked()

# ==================== ВКЛАДКА КАНАЛОВ ====================

class ChannelsTab(BaseWidget):
    """Вкладка управления каналами"""
    
    channels_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        create_btn = QPushButton("➕ Создать канал")
        create_btn.clicked.connect(self._create_channel)
        buttons_layout.addWidget(create_btn)
        
        import_btn = QPushButton("📥 Импорт")
        import_btn.clicked.connect(self._import_channels)
        buttons_layout.addWidget(import_btn)
        
        export_btn = QPushButton("📤 Экспорт")
        export_btn.clicked.connect(self._export_channels)
        buttons_layout.addWidget(export_btn)
        
        template_btn = QPushButton("📋 Из шаблона")
        template_btn.clicked.connect(self._create_from_template)
        buttons_layout.addWidget(template_btn)
        
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
        
        # Список каналов
        channels_group = QGroupBox("📋 Список каналов")
        channels_layout = QVBoxLayout()
        
        # Поиск
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Поиск каналов...")
        self.search_edit.textChanged.connect(self._filter_channels)
        search_layout.addWidget(self.search_edit)
        channels_layout.addLayout(search_layout)
        
        # Таблица каналов
        self.channels_table = QTableWidget()
        self.channels_table.setColumnCount(5)
        self.channels_table.setHorizontalHeaderLabels([
            "Название", "Описание", "Разрешение", "FPS", "Действия"
        ])
        self.channels_table.horizontalHeader().setStretchLastSection(True)
        self.channels_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.channels_table.setAlternatingRowColors(True)
        channels_layout.addWidget(self.channels_table)
        
        channels_group.setLayout(channels_layout)
        layout.addWidget(channels_group)
        
        # Статистика
        self.stats_label = QLabel()
        self.stats_label.setObjectName("infoLabel")
        layout.addWidget(self.stats_label)
        
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self._update_table()
    
    def _update_table(self, filter_text: str = ""):
        """Обновляет таблицу каналов"""
        self.channels_table.setRowCount(0)
        
        for channel in self.channels:
            # Фильтрация
            if filter_text and filter_text.lower() not in channel.name.lower():
                continue
            
            row = self.channels_table.rowCount()
            self.channels_table.insertRow(row)
            
            # Название
            name_item = QTableWidgetItem(channel.name)
            name_item.setData(Qt.UserRole, channel.id)
            self.channels_table.setItem(row, 0, name_item)
            
            # Описание
            desc_item = QTableWidgetItem(channel.description)
            self.channels_table.setItem(row, 1, desc_item)
            
            # Разрешение
            res_item = QTableWidgetItem(channel.export.resolution)
            res_item.setTextAlignment(Qt.AlignCenter)
            self.channels_table.setItem(row, 2, res_item)
            
            # FPS
            fps_item = QTableWidgetItem(f"{channel.export.fps} fps")
            fps_item.setTextAlignment(Qt.AlignCenter)
            self.channels_table.setItem(row, 3, fps_item)
            
            # Действия
            actions_widget = self._create_actions_widget(channel)
            self.channels_table.setCellWidget(row, 4, actions_widget)
        
        # Обновляем статистику
        self._update_stats()
    
    def _create_actions_widget(self, channel: Channel) -> QWidget:
        """Создает виджет с кнопками действий"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Кнопка редактирования
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Редактировать")
        edit_btn.setFixedSize(24, 24)
        edit_btn.clicked.connect(lambda: self._edit_channel(channel))
        layout.addWidget(edit_btn)
        
        # Кнопка дублирования
        duplicate_btn = QPushButton("📋")
        duplicate_btn.setToolTip("Дублировать")
        duplicate_btn.setFixedSize(24, 24)
        duplicate_btn.clicked.connect(lambda: self._duplicate_channel(channel))
        layout.addWidget(duplicate_btn)
        
        # Кнопка экспорта
        export_btn = QPushButton("📤")
        export_btn.setToolTip("Экспортировать")
        export_btn.setFixedSize(24, 24)
        export_btn.clicked.connect(lambda: self._export_channel(channel))
        layout.addWidget(export_btn)
        
        # Кнопка удаления
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Удалить")
        delete_btn.setFixedSize(24, 24)
        delete_btn.clicked.connect(lambda: self._delete_channel(channel))
        layout.addWidget(delete_btn)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def _update_stats(self):
        """Обновляет статистику"""
        total = len(self.channels)
        youtube = sum(1 for ch in self.channels if ch.template == "youtube")
        shorts = sum(1 for ch in self.channels if ch.template == "shorts")
        other = total - youtube - shorts
        
        stats_text = f"Всего каналов: {total} | YouTube: {youtube} | Shorts: {shorts} | Другие: {other}"
        self.stats_label.setText(stats_text)
    
    def _filter_channels(self, text: str):
        """Фильтрует каналы по тексту"""
        self._update_table(text)
    
    def _create_channel(self):
        """Создает новый канал"""
        dialog = ChannelDialog(parent=self)
        if dialog.exec():
            channel = dialog.get_channel()
            self.channels.append(channel)
            self._update_table()
            self.channels_changed.emit()
            self.show_info(f"Канал '{channel.name}' создан")
    
    def _edit_channel(self, channel: Channel):
        """Редактирует канал"""
        dialog = ChannelDialog(channel=channel, parent=self)
        if dialog.exec():
            updated_channel = dialog.get_channel()
            # Обновляем канал в списке
            for i, ch in enumerate(self.channels):
                if ch.id == channel.id:
                    self.channels[i] = updated_channel
                    break
            self._update_table()
            self.channels_changed.emit()
            self.show_info(f"Канал '{updated_channel.name}' обновлен")
    
    def _duplicate_channel(self, channel: Channel):
        """Дублирует канал"""
        from models import Channel
        from dataclasses import asdict
        
        # Создаем копию
        channel_dict = asdict(channel)
        channel_dict['id'] = f"channel_{int(time.time())}"
        channel_dict['name'] = f"{channel.name} (копия)"
        
        new_channel = Channel.from_dict(channel_dict)
        self.channels.append(new_channel)
        self._update_table()
        self.channels_changed.emit()
        self.show_info(f"Создана копия канала '{channel.name}'")
    
    def _delete_channel(self, channel: Channel):
        """Удаляет канал"""
        if self.confirm_action(f"Удалить канал '{channel.name}'?"):
            self.channels = [ch for ch in self.channels if ch.id != channel.id]
            self._update_table()
            self.channels_changed.emit()
            self.show_info(f"Канал '{channel.name}' удален")
    
    def _export_channel(self, channel: Channel):
        """Экспортирует канал"""
        from models import DataManager
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт канала",
            f"{channel.name}.json",
            "JSON files (*.json)"
        )
        
        if file_path:
            data_manager = DataManager()
            if data_manager.export_channels([channel], file_path):
                self.show_info(f"Канал экспортирован: {file_path}")
            else:
                self.show_error("Ошибка экспорта канала")
    
    def _export_channels(self):
        """Экспортирует все каналы"""
        from models import DataManager
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт каналов",
            f"channels_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )
        
        if file_path:
            data_manager = DataManager()
            if data_manager.export_channels(self.channels, file_path):
                self.show_info(f"Каналы экспортированы: {file_path}")
            else:
                self.show_error("Ошибка экспорта каналов")
    
    def _import_channels(self):
        """Импортирует каналы"""
        from models import DataManager
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт каналов",
            "", "JSON files (*.json)"
        )
        
        if file_path:
            data_manager = DataManager()
            imported = data_manager.import_channels(file_path)
            
            if imported:
                self.channels.extend(imported)
                self._update_table()
                self.channels_changed.emit()
                self.show_info(f"Импортировано каналов: {len(imported)}")
            else:
                self.show_error("Ошибка импорта каналов")
    
    def _create_from_template(self):
        """Создает канал из шаблона"""
        from models import ChannelFactory
        
        templates = {
            "YouTube (16:9)": "youtube",
            "Shorts/Reels (9:16)": "shorts",
            "Instagram (1:1)": "instagram",
            "Cinematic (21:9)": "cinematic"
        }
        
        template_name, ok = QInputDialog.getItem(
            self, "Выбор шаблона",
            "Выберите шаблон канала:",
            list(templates.keys()), 0, False
        )
        
        if ok and template_name:
            factory = ChannelFactory()
            template_id = templates[template_name]
            channel = factory.create_from_template(template_id)
            
            # Открываем диалог для редактирования
            dialog = ChannelDialog(channel=channel, parent=self)
            if dialog.exec():
                channel = dialog.get_channel()
                self.channels.append(channel)
                self._update_table()
                self.channels_changed.emit()
                self.show_info(f"Канал создан из шаблона '{template_name}'")

# ==================== ВКЛАДКА ЭФФЕКТОВ ====================

class EffectsTab(BaseWidget):
    """Вкладка настройки эффектов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.current_channel: Optional[Channel] = None
        self.effect_widgets = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Выбор канала
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("📺 Канал:"))
        
        self.channel_combo = QComboBox()
        self.channel_combo.currentTextChanged.connect(self._load_channel_effects)
        channel_layout.addWidget(self.channel_combo)
        
        self.copy_btn = QPushButton("📋 Копировать в...")
        self.copy_btn.clicked.connect(self._copy_effects)
        channel_layout.addWidget(self.copy_btn)
        
        channel_layout.addStretch()
        layout.addLayout(channel_layout)
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Ken Burns эффекты
        self._create_ken_burns_section(scroll_layout)
        
        # Переходы
        self._create_transitions_section(scroll_layout)
        
        # Fade эффекты
        self._create_fade_section(scroll_layout)
        
        # Цветокоррекция
        self._create_color_section(scroll_layout)
        
        # Аудио эффекты
        self._create_audio_section(scroll_layout)
        
        # Анимация и плавность
        self._create_animation_section(scroll_layout)
        
        # Кнопки сохранения
        save_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_effects)
        save_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 Сбросить")
        reset_btn.clicked.connect(self._reset_effects)
        save_layout.addWidget(reset_btn)
        
        save_layout.addStretch()
        scroll_layout.addLayout(save_layout)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self._update_channel_combo()
    
    def _update_channel_combo(self):
        """Обновляет список каналов"""
        current = self.channel_combo.currentText()
        self.channel_combo.clear()
        self.channel_combo.addItems([ch.name for ch in self.channels])
        
        if current in [ch.name for ch in self.channels]:
            self.channel_combo.setCurrentText(current)
    
    def _create_ken_burns_section(self, layout: QVBoxLayout):
        """Создает секцию Ken Burns эффектов"""
        group = CollapsibleGroupBox("🎬 Ken Burns эффекты")
        group_layout = QVBoxLayout()
        
        # Список эффектов
        effects_grid = QGridLayout()
        
        kb_effects = [
            ("zoomIn", "Zoom In", "Плавное приближение"),
            ("zoomOut", "Zoom Out", "Плавное отдаление"),
            ("panLeft", "Pan Left", "Движение влево"),
            ("panRight", "Pan Right", "Движение вправо"),
            ("panUp", "Pan Up", "Движение вверх"),
            ("panDown", "Pan Down", "Движение вниз"),
            ("rotate", "Rotate", "Вращение"),
            ("diagonal", "Diagonal", "Диагональное движение"),
            ("zoomRotate", "Zoom + Rotate", "Зум с вращением"),
            ("parallax", "Parallax", "Эффект параллакса"),
            ("spiral", "Spiral", "Спиральное движение"),
            ("shake", "Shake", "Легкая тряска")
        ]
        
        self.kb_effects = {}
        for i, (effect_id, label, desc) in enumerate(kb_effects):
            widget = EffectCheckBox(effect_id, label, desc)
            self.kb_effects[effect_id] = widget
            effects_grid.addWidget(widget, i // 2, i % 2)
        
        group_layout.addLayout(effects_grid)
        
        # Настройки
        settings_layout = QFormLayout()
        
        self.kb_intensity = SliderWithLabel(0, 100, 30)
        settings_layout.addRow("Интенсивность:", self.kb_intensity)
        
        self.kb_rotation = SliderWithLabel(0, 45, 5, "°")
        settings_layout.addRow("Угол вращения:", self.kb_rotation)
        
        self.kb_smooth = SliderWithLabel(0, 100, 70)
        settings_layout.addRow("Плавность:", self.kb_smooth)
        
        self.kb_randomize = QCheckBox("Случайный выбор эффектов")
        settings_layout.addRow(self.kb_randomize)
        
        self.kb_smart_crop = QCheckBox("Умная обрезка (без черных полос)")
        self.kb_smart_crop.setChecked(True)
        settings_layout.addRow(self.kb_smart_crop)
        
        # Easing
        self.kb_easing = QComboBox()
        self.kb_easing.addItems([
            "linear", "ease", "ease-in", "ease-out", 
            "ease-in-out", "bounce", "elastic", "back"
        ])
        self.kb_easing.setCurrentText("ease")
        settings_layout.addRow("Тип анимации:", self.kb_easing)
        
        group_layout.addLayout(settings_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_transitions_section(self, layout: QVBoxLayout):
        """Создает секцию переходов"""
        group = CollapsibleGroupBox("🔄 Переходы между клипами")
        group_layout = QVBoxLayout()
        
        # Список переходов
        trans_grid = QGridLayout()
        
        transitions = [
            ("fade", "Fade", "Плавное затухание"),
            ("dissolve", "Cross Dissolve", "Перекрестное растворение"),
            ("dip_black", "Dip to Black", "Через черный"),
            ("dip_white", "Dip to White", "Через белый"),
            ("wipe", "Wipe", "Вытеснение"),
            ("slide", "Slide", "Сдвиг"),
            ("push", "Push", "Выталкивание"),
            ("zoom", "Zoom", "Масштабирование"),
            ("blur", "Blur", "Размытие"),
            ("pixelate", "Pixelate", "Пикселизация"),
            ("glitch", "Glitch", "Цифровой сбой"),
            ("rotate", "Rotate", "Поворот")
        ]
        
        self.transitions = {}
        for i, (trans_id, label, desc) in enumerate(transitions):
            widget = EffectCheckBox(trans_id, label, desc)
            self.transitions[trans_id] = widget
            trans_grid.addWidget(widget, i // 2, i % 2)
        
        group_layout.addLayout(trans_grid)
        
        # Настройки
        settings_layout = QFormLayout()
        
        self.trans_duration = QDoubleSpinBox()
        self.trans_duration.setRange(0.1, 3.0)
        self.trans_duration.setValue(1.0)
        self.trans_duration.setSingleStep(0.1)
        self.trans_duration.setSuffix(" сек")
        settings_layout.addRow("Длительность:", self.trans_duration)
        
        self.trans_overlap = QDoubleSpinBox()
        self.trans_overlap.setRange(0.0, 1.0)
        self.trans_overlap.setValue(0.5)
        self.trans_overlap.setSingleStep(0.1)
        settings_layout.addRow("Перекрытие:", self.trans_overlap)
        
        self.trans_randomize = QCheckBox("Случайный выбор переходов")
        settings_layout.addRow(self.trans_randomize)
        
        group_layout.addLayout(settings_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_fade_section(self, layout: QVBoxLayout):
        """Создает секцию Fade эффектов"""
        group = CollapsibleGroupBox("🌑 Fade In/Out эффекты")
        group_layout = QVBoxLayout()
        
        # Fade In
        fade_in_layout = QHBoxLayout()
        self.fade_in_check = QCheckBox("Fade In from Black (первый клип)")
        fade_in_layout.addWidget(self.fade_in_check)
        
        self.fade_in_duration = QDoubleSpinBox()
        self.fade_in_duration.setRange(0.1, 5.0)
        self.fade_in_duration.setValue(1.0)
        self.fade_in_duration.setSingleStep(0.1)
        self.fade_in_duration.setSuffix(" сек")
        fade_in_layout.addWidget(QLabel("Длительность:"))
        fade_in_layout.addWidget(self.fade_in_duration)
        
        self.fade_in_type = QComboBox()
        self.fade_in_type.addItems(["linear", "ease", "ease-in", "ease-out"])
        self.fade_in_type.setCurrentText("ease")
        fade_in_layout.addWidget(QLabel("Тип:"))
        fade_in_layout.addWidget(self.fade_in_type)
        
        fade_in_layout.addStretch()
        group_layout.addLayout(fade_in_layout)
        
        # Fade Out
        fade_out_layout = QHBoxLayout()
        self.fade_out_check = QCheckBox("Fade Out to Black (последний клип)")
        fade_out_layout.addWidget(self.fade_out_check)
        
        self.fade_out_duration = QDoubleSpinBox()
        self.fade_out_duration.setRange(0.1, 5.0)
        self.fade_out_duration.setValue(1.0)
        self.fade_out_duration.setSingleStep(0.1)
        self.fade_out_duration.setSuffix(" сек")
        fade_out_layout.addWidget(QLabel("Длительность:"))
        fade_out_layout.addWidget(self.fade_out_duration)
        
        self.fade_out_type = QComboBox()
        self.fade_out_type.addItems(["linear", "ease", "ease-in", "ease-out"])
        self.fade_out_type.setCurrentText("ease")
        fade_out_layout.addWidget(QLabel("Тип:"))
        fade_out_layout.addWidget(self.fade_out_type)
        
        fade_out_layout.addStretch()
        group_layout.addLayout(fade_out_layout)
        
        # Черный кадр
        self.add_black_frame = QCheckBox("Добавить черный кадр в конец")
        self.add_black_frame.setChecked(True)
        group_layout.addWidget(self.add_black_frame)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_color_section(self, layout: QVBoxLayout):
        """Создает секцию цветокоррекции"""
        group = CollapsibleGroupBox("🎨 Цветокоррекция")
        group_layout = QVBoxLayout()
        
        self.color_correction = QCheckBox("Включить цветокоррекцию")
        self.color_correction.toggled.connect(self._on_color_correction_toggled)
        group_layout.addWidget(self.color_correction)
        
        # Настройки цвета
        self.color_widget = QWidget()
        color_layout = QFormLayout()
        
        self.color_filter = QComboBox()
        self.color_filter.addItems([
            "none", "warm", "cold", "vintage", "blackwhite", "sepia",
            "cinematic", "vibrant", "faded", "instagram", "film"
        ])
        color_layout.addRow("Фильтр:", self.color_filter)
        
        # Виньетка
        vignette_layout = QHBoxLayout()
        self.vignette_check = QCheckBox("Виньетка")
        vignette_layout.addWidget(self.vignette_check)
        self.vignette_intensity = SliderWithLabel(0, 100, 40)
        vignette_layout.addWidget(self.vignette_intensity)
        color_layout.addRow(vignette_layout)
        
        # Зерно
        grain_layout = QHBoxLayout()
        self.grain_check = QCheckBox("Зерно пленки")
        grain_layout.addWidget(self.grain_check)
        self.grain_intensity = SliderWithLabel(0, 100, 20)
        grain_layout.addWidget(self.grain_intensity)
        color_layout.addRow(grain_layout)
        
        # Размытие краев
        blur_layout = QHBoxLayout()
        self.blur_edges_check = QCheckBox("Размытие краев")
        blur_layout.addWidget(self.blur_edges_check)
        self.blur_intensity = SliderWithLabel(0, 100, 30)
        blur_layout.addWidget(self.blur_intensity)
        color_layout.addRow(blur_layout)
        
        self.color_widget.setLayout(color_layout)
        self.color_widget.setVisible(False)
        group_layout.addWidget(self.color_widget)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_audio_section(self, layout: QVBoxLayout):
        """Создает секцию аудио эффектов"""
        group = CollapsibleGroupBox("🎵 Аудио эффекты")
        group_layout = QFormLayout()
        
        # Тональность
        self.audio_pitch = QComboBox()
        pitches = [
            "-3", "-2.5", "-2", "-1.5", "-1", "-0.5", "0",
            "+0.5", "+1", "+1.5", "+2", "+2.5", "+3"
        ]
        self.audio_pitch.addItems(pitches)
        self.audio_pitch.setCurrentText("0")
        group_layout.addRow("Тональность:", self.audio_pitch)
        
        # Эффект
        self.audio_effect = QComboBox()
        self.audio_effect.addItems([
            "none", "bass", "reverb", "echo", "chorus", "telephone",
            "underwater", "radio", "vintage", "distortion", "robot"
        ])
        group_layout.addRow("Эффект:", self.audio_effect)
        
        # Дополнительные настройки
        self.audio_stereo = QCheckBox("Расширение стерео")
        group_layout.addRow(self.audio_stereo)
        
        self.audio_normalize = QCheckBox("Нормализация громкости")
        self.audio_normalize.setChecked(True)
        group_layout.addRow(self.audio_normalize)
        
        self.audio_compressor = QCheckBox("Компрессор")
        group_layout.addRow(self.audio_compressor)
        
        self.audio_limiter = QCheckBox("Лимитер")
        group_layout.addRow(self.audio_limiter)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_animation_section(self, layout: QVBoxLayout):
        """Создает секцию настроек анимации"""
        group = CollapsibleGroupBox("⚡ Плавность анимации")
        group_layout = QFormLayout()
        
        # Motion blur
        motion_layout = QHBoxLayout()
        self.motion_blur = QCheckBox("Motion Blur")
        motion_layout.addWidget(self.motion_blur)
        self.motion_blur_amount = SliderWithLabel(0, 50, 20)
        motion_layout.addWidget(self.motion_blur_amount)
        group_layout.addRow(motion_layout)
        
        # 3D Parallax
        self.parallax_enabled = QCheckBox("3D Parallax эффект (экспериментально)")
        self.parallax_enabled.toggled.connect(self._on_parallax_toggled)
        group_layout.addRow(self.parallax_enabled)
        
        # Parallax настройки
        self.parallax_widget = QWidget()
        parallax_layout = QFormLayout()
        
        self.parallax_layers = QSpinBox()
        self.parallax_layers.setRange(2, 5)
        self.parallax_layers.setValue(3)
        parallax_layout.addRow("Слои глубины:", self.parallax_layers)
        
        self.parallax_speed = QDoubleSpinBox()
        self.parallax_speed.setRange(0.1, 3.0)
        self.parallax_speed.setValue(1.0)
        self.parallax_speed.setSingleStep(0.1)
        parallax_layout.addRow("Скорость:", self.parallax_speed)
        
        self.parallax_direction = QComboBox()
        self.parallax_direction.addItems(["horizontal", "vertical", "diagonal"])
        parallax_layout.addRow("Направление:", self.parallax_direction)
        
        self.parallax_widget.setLayout(parallax_layout)
        self.parallax_widget.setVisible(False)
        group_layout.addRow(self.parallax_widget)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _on_color_correction_toggled(self, checked: bool):
        """Обработчик переключения цветокоррекции"""
        self.color_widget.setVisible(checked)
    
    def _on_parallax_toggled(self, checked: bool):
        """Обработчик переключения parallax"""
        self.parallax_widget.setVisible(checked)
    
    def _load_channel_effects(self):
        """Загружает настройки эффектов канала"""
        channel_name = self.channel_combo.currentText()
        if not channel_name:
            return
        
        self.current_channel = next((ch for ch in self.channels if ch.name == channel_name), None)
        if not self.current_channel:
            return
        
        effects = self.current_channel.effects
        
        # Ken Burns
        for effect_id, widget in self.kb_effects.items():
            widget.setChecked(effect_id in effects.ken_burns)
        
        self.kb_intensity.setValue(effects.ken_burns_intensity)
        self.kb_rotation.setValue(effects.rotation_angle)
        self.kb_smooth.setValue(int(effects.kb_smooth_factor * 100))
        self.kb_randomize.setChecked(effects.kb_randomize)
        self.kb_smart_crop.setChecked(effects.smart_crop)
        self.kb_easing.setCurrentText(effects.easing_type)
        
        # Переходы
        for trans_id, widget in self.transitions.items():
            widget.setChecked(trans_id in effects.transitions)
        
        self.trans_duration.setValue(effects.transition_duration)
        self.trans_overlap.setValue(effects.trans_overlap)
        self.trans_randomize.setChecked(effects.trans_randomize)
        
        # Fade
        self.fade_in_check.setChecked(effects.fade_in_from_black)
        self.fade_in_duration.setValue(effects.fade_in_duration)
        self.fade_in_type.setCurrentText(effects.fade_in_type)
        self.fade_out_check.setChecked(effects.fade_out_to_black)
        self.fade_out_duration.setValue(effects.fade_out_duration)
        self.fade_out_type.setCurrentText(effects.fade_out_type)
        self.add_black_frame.setChecked(effects.add_black_frame)
        
        # Цветокоррекция
        self.color_correction.setChecked(effects.color_correction)
        self.color_filter.setCurrentText(effects.color_filter)
        self.vignette_check.setChecked(effects.vignette)
        self.vignette_intensity.setValue(effects.vignette_intensity)
        self.grain_check.setChecked(effects.grain)
        self.grain_intensity.setValue(effects.grain_intensity)
        self.blur_edges_check.setChecked(effects.blur_edges)
        self.blur_intensity.setValue(effects.blur_intensity)
        
        # Аудио
        self.audio_pitch.setCurrentText(effects.audio_pitch)
        self.audio_effect.setCurrentText(effects.audio_effect)
        self.audio_stereo.setChecked(effects.audio_stereo_enhance)
        self.audio_normalize.setChecked(effects.audio_normalize)
        self.audio_compressor.setChecked(effects.audio_compressor)
        self.audio_limiter.setChecked(effects.audio_limiter)
        
        # Анимация
        self.motion_blur.setChecked(effects.motion_blur)
        self.motion_blur_amount.setValue(effects.motion_blur_amount)
        self.parallax_enabled.setChecked(effects.enable_3d_parallax)
        self.parallax_layers.setValue(effects.parallax_depth_layers)
        self.parallax_speed.setValue(effects.parallax_speed)
        self.parallax_direction.setCurrentText(effects.parallax_direction)
    
    def _copy_effects(self):
        # Заглушка для копирования эффектов
        print("Копирование эффектов не реализовано")

    def _reset_effects(self):
        # Заглушка для сброса эффектов
        print("Сброс эффектов не реализован")

    def _save_effects(self):
        """Сохраняет настройки эффектов"""
        if not self.current_channel:
            self.show_warning("Выберите канал")
            return
        
        effects = self.current_channel.effects
        
        # Ken Burns
        if hasattr(self, "motion_intensity"):
            effects.motion_intensity = self.motion_intensity.value()
        else:
            effects.motion_intensity = 30
        effects.effect_frequency = self.effect_frequency.currentData()
        effects.effect_percent = self.effect_percent.value()
        effects.effect_every = self.effect_every.value()
        effects.capcut_timing = self.capcut_timing.currentData()
        effects.avoid_repetition = self.avoid_repetition.isChecked()
        
        # Валидация
        effects.validate()
        
        self.show_info(f"CapCut эффекты для канала '{self.current_channel.name}' сохранены")
    
    def _apply_preset(self, preset_id: str):
        """Применяет пресет эффектов"""
        presets = {
            "dynamic": {
                "scale": ["zoomBurst", "bounce"],
                "motion": ["shake", "wobble"],
                "digital": ["glitch"],
                "scale_amplitude": 25,
                "motion_intensity": 40,
                "frequency": "percent",
                "percent": 60,
                "timing": "random"
            },
            "smooth": {
                "scale": ["pulse", "wave", "breathe"],
                "motion": ["pendulum"],
                "digital": [],
                "scale_amplitude": 10,
                "motion_intensity": 20,
                "frequency": "every",
                "every": 3,
                "timing": "middle"
            },
            "epic": {
                "scale": ["zoomBurst", "elastic"],
                "motion": ["shake", "spin"],
                "digital": ["glitch", "chromatic"],
                "scale_amplitude": 30,
                "zoom_burst_start": 180,
                "zoom_burst_decay": 90,
                "motion_intensity": 50,
                "frequency": "all",
                "timing": "start"
            },
            "minimal": {
                "scale": ["pulse"],
                "motion": [],
                "digital": [],
                "scale_amplitude": 5,
                "motion_intensity": 10,
                "frequency": "percent",
                "percent": 30,
                "timing": "end"
            }
        }
        
        preset = presets.get(preset_id)
        if not preset:
            return
        
        # Применяем пресет
        for effect_id, widget in self.scale_effects.items():
            widget.setChecked(effect_id in preset.get("scale", []))
        
        for effect_id, widget in self.motion_effects.items():
            widget.setChecked(effect_id in preset.get("motion", []))
        
        for effect_id, widget in self.digital_effects.items():
            widget.setChecked(effect_id in preset.get("digital", []))
        
        self.scale_amplitude.setValue(preset.get("scale_amplitude", 15))
        
        if "zoom_burst_start" in preset:
            self.zoom_burst_start.setValue(preset["zoom_burst_start"])
        if "zoom_burst_decay" in preset:
            self.zoom_burst_decay.setValue(preset["zoom_burst_decay"])
        
        self.motion_intensity.setValue(preset.get("motion_intensity", 30))
        
        # Частота
        for i in range(self.effect_frequency.count()):
            if self.effect_frequency.itemData(i) == preset.get("frequency", "all"):
                self.effect_frequency.setCurrentIndex(i)
                break
        
        if "percent" in preset:
            self.effect_percent.setValue(preset["percent"])
        if "every" in preset:
            self.effect_every.setValue(preset["every"])
        
        # Тайминг
        for i in range(self.capcut_timing.count()):
            if self.capcut_timing.itemData(i) == preset.get("timing", "start"):
                self.capcut_timing.setCurrentIndex(i)
                break
        
        self.show_info(f"Применен пресет '{preset_id}'")

# ==================== ВКЛАДКА ОВЕРЛЕЕВ ====================

class OverlaysTab(BaseWidget):
    """Вкладка настройки оверлеев"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.current_channel: Optional[Channel] = None
        self.overlay_files: List[str] = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Управление оверлеями
        control_group = QGroupBox("🎭 Управление оверлеями")
        control_layout = QVBoxLayout()
        
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Папка с оверлеями:"))
        
        self.folder_selector = FilePathSelector(
            mode="folder",
            placeholder="Выберите папку с оверлеями..."
        )
        self.folder_selector.pathChanged.connect(self._scan_overlay_folder)
        folder_layout.addWidget(self.folder_selector)
        
        control_layout.addLayout(folder_layout)
        
        info_label = QLabel(
            "Поддерживаются: PNG (с прозрачностью), MP4, MOV, GIF"
        )
        info_label.setObjectName("infoLabel")
        control_layout.addWidget(info_label)
        
        # Статистика файлов
        self.files_info = QLabel("Файлов найдено: 0")
        control_layout.addWidget(self.files_info)
        
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)
        
        # Назначение оверлеев
        assign_group = QGroupBox("📺 Назначение оверлеев каналам")
        assign_layout = QVBoxLayout()
        
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("Канал:"))
        
        self.channel_combo = QComboBox()
        self.channel_combo.currentTextChanged.connect(self._load_channel_overlays)
        channel_layout.addWidget(self.channel_combo)
        channel_layout.addStretch()
        assign_layout.addLayout(channel_layout)
        
        # Настройки оверлеев
        self.overlay_widget = QWidget()
        overlay_layout = QVBoxLayout()
        
        # Список файлов
        files_group = QGroupBox("Доступные оверлеи")
        files_layout = QVBoxLayout()
        
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.MultiSelection)
        files_layout.addWidget(self.files_list)
        
        files_group.setLayout(files_layout)
        overlay_layout.addWidget(files_group)
        
        # Настройки наложения
        settings_group = QGroupBox("Настройки наложения")
        settings_layout = QFormLayout()
        
        # Режим наложения
        self.blend_mode = QComboBox()
        self.blend_mode.addItems([
            ("normal", "Обычный"),
            ("screen", "Экран"),
            ("overlay", "Перекрытие"),
            ("multiply", "Умножение"),
            ("add", "Сложение"),
            ("lighten", "Осветление"),
            ("darken", "Затемнение")
        ])
        self.blend_mode.setCurrentIndex(1)  # screen
        settings_layout.addRow("Режим наложения:", self.blend_mode)
        
        # Прозрачность
        self.opacity_slider = SliderWithLabel(0, 100, 100)
        settings_layout.addRow("Прозрачность:", self.opacity_slider)
        
        # Позиция
        self.position_combo = QComboBox()
        self.position_combo.addItems([
            ("center", "По центру"),
            ("top-left", "Сверху слева"),
            ("top-right", "Сверху справа"),
            ("bottom-left", "Снизу слева"),
            ("bottom-right", "Снизу справа")
        ])
        settings_layout.addRow("Позиция:", self.position_combo)
        
        # Масштаб
        self.scale_slider = SliderWithLabel(10, 200, 100)
        settings_layout.addRow("Масштаб:", self.scale_slider)
        
        # Поворот
        self.rotation_slider = SliderWithLabel(-180, 180, 0, "°")
        settings_layout.addRow("Поворот:", self.rotation_slider)
        
        # Опции
        self.randomize_check = QCheckBox("Случайный выбор оверлеев")
        settings_layout.addRow(self.randomize_check)
        
        self.stretch_check = QCheckBox("Растягивать на весь экран")
        self.stretch_check.setChecked(True)
        settings_layout.addRow(self.stretch_check)
        
        self.animate_check = QCheckBox("Анимировать оверлей")
        self.animate_check.toggled.connect(self._on_animate_toggled)
        settings_layout.addRow(self.animate_check)
        
        # Анимация
        self.animation_widget = QWidget()
        animation_layout = QHBoxLayout()
        animation_layout.setContentsMargins(0, 0, 0, 0)
        
        animation_layout.addWidget(QLabel("Тип анимации:"))
        self.animation_type = QComboBox()
        self.animation_type.addItems([
            ("fade", "Затухание"),
            ("slide", "Сдвиг"),
            ("zoom", "Масштабирование"),
            ("rotate", "Вращение")
        ])
        animation_layout.addWidget(self.animation_type)
        animation_layout.addStretch()
        
        self.animation_widget.setLayout(animation_layout)
        self.animation_widget.setVisible(False)
        settings_layout.addRow(self.animation_widget)
        
        settings_group.setLayout(settings_layout)
        overlay_layout.addWidget(settings_group)
        
        # Кнопка сохранения
        save_btn = QPushButton("💾 Сохранить настройки оверлеев")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_overlays)
        overlay_layout.addWidget(save_btn)
        
        self.overlay_widget.setLayout(overlay_layout)
        self.overlay_widget.setVisible(False)
        assign_layout.addWidget(self.overlay_widget)
        
        assign_group.setLayout(assign_layout)
        layout.addWidget(assign_group)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self._update_channel_combo()
    
    def _update_channel_combo(self):
        """Обновляет список каналов"""
        current = self.channel_combo.currentText()
        self.channel_combo.clear()
        self.channel_combo.addItems([ch.name for ch in self.channels])
        
        if current in [ch.name for ch in self.channels]:
            self.channel_combo.setCurrentText(current)
    
    def _scan_overlay_folder(self, folder: str):
        """Сканирует папку с оверлеями"""
        if not folder:
            return
        
        from utils import FileUtils
        
        overlay_files = []
        folder_path = Path(folder)
        
        for file_path in folder_path.iterdir():
            if file_path.is_file() and FileUtils.is_overlay(file_path):
                overlay_files.append(file_path.name)
        
        self.overlay_files = sorted(overlay_files)
        self.files_info.setText(f"Файлов найдено: {len(self.overlay_files)}")
        
        # Обновляем список
        self._update_files_list()
    
    def _update_files_list(self):
        """Обновляет список файлов"""
        self.files_list.clear()
        
        for file_name in self.overlay_files:
            # Добавляем иконку по типу файла
            ext = Path(file_name).suffix.lower()
            if ext == '.png':
                icon = "🖼️"
            elif ext in ['.mp4', '.mov']:
                icon = "🎬"
            elif ext == '.gif':
                icon = "🎞️"
            else:
                icon = "📄"
            
            self.files_list.addItem(f"{icon} {file_name}")
    
    def _on_animate_toggled(self, checked: bool):
        """Обработчик переключения анимации"""
        self.animation_widget.setVisible(checked)
    
    def _load_channel_overlays(self):
        """Загружает настройки оверлеев канала"""
        channel_name = self.channel_combo.currentText()
        if not channel_name:
            self.overlay_widget.setVisible(False)
            return
        
        self.current_channel = next((ch for ch in self.channels if ch.name == channel_name), None)
        if not self.current_channel:
            return
        
        self.overlay_widget.setVisible(True)
        overlays = self.current_channel.overlays
        
        # Загружаем настройки
        if overlays.folder:
            self.folder_selector.set_path(overlays.folder)
        
        # Режим наложения
        for i in range(self.blend_mode.count()):
            if self.blend_mode.itemData(i) == overlays.blend_mode:
                self.blend_mode.setCurrentIndex(i)
                break
        
        self.opacity_slider.setValue(overlays.opacity)
        
        # Позиция
        for i in range(self.position_combo.count()):
            if self.position_combo.itemData(i) == overlays.position:
                self.position_combo.setCurrentIndex(i)
                break
        
        self.scale_slider.setValue(overlays.scale)
        self.rotation_slider.setValue(overlays.rotation)
        self.randomize_check.setChecked(overlays.randomize)
        self.stretch_check.setChecked(overlays.stretch)
        self.animate_check.setChecked(overlays.animate)
        
        # Тип анимации
        for i in range(self.animation_type.count()):
            if self.animation_type.itemData(i) == overlays.animation_type:
                self.animation_type.setCurrentIndex(i)
                break
        
        # Выделяем выбранные файлы
        self.files_list.clearSelection()
        for i in range(self.files_list.count()):
            item_text = self.files_list.item(i).text()
            # Убираем иконку для сравнения
            file_name = item_text.split(' ', 1)[1] if ' ' in item_text else item_text
            if file_name in overlays.files:
                self.files_list.item(i).setSelected(True)
    
    def _save_overlays(self):
        """Сохраняет настройки оверлеев"""
        if not self.current_channel:
            self.show_warning("Выберите канал")
            return
        
        # Собираем выбранные файлы
        selected_files = []
        for item in self.files_list.selectedItems():
            # Убираем иконку
            text = item.text()
            file_name = text.split(' ', 1)[1] if ' ' in text else text
            selected_files.append(file_name)
        
        overlays = self.current_channel.overlays
        
        overlays.enabled = len(selected_files) > 0
        overlays.folder = self.folder_selector.get_path()
        overlays.files = selected_files
        overlays.blend_mode = self.blend_mode.currentData()
        overlays.opacity = self.opacity_slider.value()
        overlays.position = self.position_combo.currentData()
        overlays.scale = self.scale_slider.value()
        overlays.rotation = self.rotation_slider.value()
        overlays.randomize = self.randomize_check.isChecked()
        overlays.stretch = self.stretch_check.isChecked()
        overlays.animate = self.animate_check.isChecked()
        overlays.animation_type = self.animation_type.currentData()
        
        # Валидация
        overlays.validate()
        
        self.show_info(f"Настройки оверлеев для канала '{self.current_channel.name}' сохранены")

# ==================== ВКЛАДКА НАСТРОЕК ====================

class SettingsTab(BaseWidget):
    """Вкладка настроек приложения"""
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Пути к программам
        paths_group = QGroupBox("📁 Пути к программам")
        paths_layout = QFormLayout()
        
        # FFmpeg
        self.ffmpeg_selector = FilePathSelector(
            mode="file",
            filter="Executable files (*.exe);;All files (*.*)",
            placeholder="Путь к FFmpeg..."
        )
        
        ffmpeg_layout = QHBoxLayout()
        ffmpeg_layout.addWidget(self.ffmpeg_selector)
        
        check_btn = QPushButton("✓ Проверить")
        check_btn.clicked.connect(self._check_ffmpeg)
        ffmpeg_layout.addWidget(check_btn)
        
        paths_layout.addRow("FFmpeg:", ffmpeg_layout)
        
        paths_group.setLayout(paths_layout)
        scroll_layout.addWidget(paths_group)
        
        # Производительность
        performance_group = QGroupBox("⚡ Производительность")
        performance_layout = QFormLayout()
        
        self.use_gpu_check = QCheckBox("Использовать GPU ускорение")
        self.use_gpu_check.setChecked(True)
        performance_layout.addRow(self.use_gpu_check)
        
        # GPU информация
        self.gpu_info = QLabel("Проверка GPU...")
        self.gpu_info.setObjectName("infoLabel")
        performance_layout.addRow("Доступные GPU:", self.gpu_info)
        
        self.two_pass_check = QCheckBox("Двухпроходное кодирование (лучше качество)")
        performance_layout.addRow(self.two_pass_check)
        
        self.preview_res = QComboBox()
        self.preview_res.addItems(["360p", "480p", "720p", "Оригинал"])
        self.preview_res.setCurrentText("480p")
        performance_layout.addRow("Разрешение превью:", self.preview_res)
        
        performance_group.setLayout(performance_layout)
        scroll_layout.addWidget(performance_group)
        
        # Обработка файлов
        files_group = QGroupBox("📄 Обработка файлов")
        files_layout = QFormLayout()
        
        self.safe_filenames = QCheckBox("Безопасные имена файлов (транслитерация)")
        self.safe_filenames.setChecked(True)
        files_layout.addRow(self.safe_filenames)
        
        self.keep_temp_files = QCheckBox("Сохранять временные файлы")
        files_layout.addRow(self.keep_temp_files)
        
        self.auto_cleanup = QCheckBox("Автоочистка старых рендеров")
        files_layout.addRow(self.auto_cleanup)
        
        files_group.setLayout(files_layout)
        scroll_layout.addWidget(files_group)
        
        # Интерфейс
        ui_group = QGroupBox("🎨 Интерфейс")
        ui_layout = QFormLayout()
        
        theme_layout = QHBoxLayout()
        self.dark_theme = QRadioButton("🌙 Темная тема")
        self.dark_theme.setChecked(True)
        theme_layout.addWidget(self.dark_theme)
        
        self.light_theme = QRadioButton("☀️ Светлая тема")
        self.light_theme.setEnabled(False)  # Пока не реализовано
        theme_layout.addWidget(self.light_theme)
        
        ui_layout.addRow("Тема:", theme_layout)
        
        self.show_tooltips = QCheckBox("Показывать подсказки")
        self.show_tooltips.setChecked(True)
        ui_layout.addRow(self.show_tooltips)
        
        ui_group.setLayout(ui_layout)
        scroll_layout.addWidget(ui_group)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Сохранить настройки")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_settings)
        buttons_layout.addWidget(save_btn)
        
        reset_btn = QPushButton("🔄 Сбросить")
        reset_btn.clicked.connect(self._reset_settings)
        buttons_layout.addWidget(reset_btn)
        
        export_btn = QPushButton("📤 Экспорт")
        export_btn.clicked.connect(self._export_settings)
        buttons_layout.addWidget(export_btn)
        
        import_btn = QPushButton("📥 Импорт")
        import_btn.clicked.connect(self._import_settings)
        buttons_layout.addWidget(import_btn)
        
        buttons_layout.addStretch()
        scroll_layout.addLayout(buttons_layout)
        
        # О программе
        about_group = QGroupBox("ℹ️ О программе")
        about_layout = QVBoxLayout()
        
        about_text = """<b>Auto Montage Builder Pro</b><br>
Enhanced Python Edition v5.0.0<br><br>

<b>Возможности:</b><br>
• Автоматическая расстановка файлов на таймлайне<br>
• Поддержка видео файлов с зацикливанием<br>
• Ken Burns эффекты с плавной анимацией<br>
• CapCut-style эффекты и анимации<br>
• Продвинутые переходы между клипами<br>
• GPU ускорение<br><br>

<b>Автор:</b> AutoMontage Team<br>
<b>Поддержка:</b> automontage@support.com
"""
        
        about_label = QLabel(about_text)
        about_label.setWordWrap(True)
        about_layout.addWidget(about_label)
        
        about_group.setLayout(about_layout)
        scroll_layout.addWidget(about_group)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
        
        # Проверяем GPU
        self._check_gpu_support()
    
    def load_settings(self, settings: dict):
        """Загружает настройки"""
        from utils import FFmpegUtils
        
        self.ffmpeg_selector.set_path(
            settings.get("ffmpeg_path", FFmpegUtils.get_ffmpeg_path())
        )
        self.use_gpu_check.setChecked(settings.get("use_gpu", True))
        self.two_pass_check.setChecked(settings.get("two_pass", False))
        self.preview_res.setCurrentText(settings.get("preview_resolution", "480p"))
        self.safe_filenames.setChecked(settings.get("safe_filenames", True))
        self.keep_temp_files.setChecked(settings.get("keep_temp_files", False))
        self.auto_cleanup.setChecked(settings.get("auto_cleanup", False))
        self.show_tooltips.setChecked(settings.get("show_tooltips", True))
        self.dark_theme.setChecked(settings.get("dark_theme", True))
    
    def get_settings(self) -> dict:
        """Возвращает текущие настройки"""
        return {
            "ffmpeg_path": self.ffmpeg_selector.get_path(),
            "use_gpu": self.use_gpu_check.isChecked(),
            "two_pass": self.two_pass_check.isChecked(),
            "preview_resolution": self.preview_res.currentText(),
            "safe_filenames": self.safe_filenames.isChecked(),
            "keep_temp_files": self.keep_temp_files.isChecked(),
            "auto_cleanup": self.auto_cleanup.isChecked(),
            "show_tooltips": self.show_tooltips.isChecked(),
            "dark_theme": self.dark_theme.isChecked()
        }
    
    def _check_ffmpeg(self):
        """Проверяет FFmpeg"""
        from utils import FFmpegUtils
        
        ffmpeg_path = self.ffmpeg_selector.get_path()
        if not ffmpeg_path:
            ffmpeg_path = FFmpegUtils.get_ffmpeg_path()
        
        version = FFmpegUtils.get_ffmpeg_version()
        if version:
            self.show_info(f"FFmpeg найден!\n{version}")
        else:
            self.show_error("FFmpeg не найден или не работает")
    
    def _check_gpu_support(self):
        """Проверяет поддержку GPU"""
        from utils import FFmpegUtils
        
        gpu_support = FFmpegUtils.check_gpu_support()
        
        gpu_text = []
        if gpu_support.get('nvidia'):
            gpu_text.append("✅ NVIDIA")
        if gpu_support.get('amd'):
            gpu_text.append("✅ AMD")
        if gpu_support.get('intel'):
            gpu_text.append("✅ Intel")
        if gpu_support.get('videotoolbox'):
            gpu_text.append("✅ VideoToolbox")
        
        if not gpu_text:
            gpu_text.append("❌ GPU ускорение недоступно")
        
        self.gpu_info.setText(" • ".join(gpu_text))
    
    def _save_settings(self):
        """Сохраняет настройки"""
        self.settings_changed.emit()
        self.show_info("Настройки сохранены")
    
    def _reset_settings(self):
        """Сбрасывает настройки"""
        if self.confirm_action("Сбросить все настройки к значениям по умолчанию?"):
            from models import DataManager
            data_manager = DataManager()
            default_settings = data_manager.get_default_settings()
            self.load_settings(default_settings)
            self.settings_changed.emit()
            self.show_info("Настройки сброшены")
    
    def _export_settings(self):
        """Экспортирует настройки"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт настроек",
            f"settings_{time.strftime('%Y%m%d_%H%M%S')}.json",
            "JSON files (*.json)"
        )
        
        if file_path:
            import json
            settings = self.get_settings()
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                self.show_info(f"Настройки экспортированы: {file_path}")
            except Exception as e:
                self.show_error(f"Ошибка экспорта: {str(e)}")
    
    def _import_settings(self):
        """Импортирует настройки"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт настроек",
            "", "JSON files (*.json)"
        )
        
        if file_path:
            import json
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.load_settings(settings)
                self.settings_changed.emit()
                self.show_info("Настройки импортированы")
            except Exception as e:
                self.show_error(f"Ошибка импорта: {str(e)}")
                ken_burns = [eid for eid, w in self.kb_effects.items() if w.isChecked()]
        effects.ken_burns_intensity = self.kb_intensity.value()
        effects.rotation_angle = self.kb_rotation.value()
        effects.kb_smooth_factor = self.kb_smooth.value() / 100.0
        effects.kb_randomize = self.kb_randomize.isChecked()
        effects.smart_crop = self.kb_smart_crop.isChecked()
        effects.easing_type = self.kb_easing.currentText()
        
        # Переходы
        effects.transitions = [tid for tid, w in self.transitions.items() if w.isChecked()]
        effects.transition_duration = self.trans_duration.value()
        effects.trans_overlap = self.trans_overlap.value()
        effects.trans_randomize = self.trans_randomize.isChecked()
        
        # Fade
        effects.fade_in_from_black = self.fade_in_check.isChecked()
        effects.fade_in_duration = self.fade_in_duration.value()
        effects.fade_in_type = self.fade_in_type.currentText()
        effects.fade_out_to_black = self.fade_out_check.isChecked()
        effects.fade_out_duration = self.fade_out_duration.value()
        effects.fade_out_type = self.fade_out_type.currentText()
        effects.add_black_frame = self.add_black_frame.isChecked()
        
        # Цветокоррекция
        effects.color_correction = self.color_correction.isChecked()
        effects.color_filter = self.color_filter.currentText()
        effects.vignette = self.vignette_check.isChecked()
        effects.vignette_intensity = self.vignette_intensity.value()
        effects.grain = self.grain_check.isChecked()
        effects.grain_intensity = self.grain_intensity.value()
        effects.blur_edges = self.blur_edges_check.isChecked()
        effects.blur_intensity = self.blur_intensity.value()
        
        # Аудио
        effects.audio_pitch = self.audio_pitch.currentText()
        effects.audio_effect = self.audio_effect.currentText()
        effects.audio_stereo_enhance = self.audio_stereo.isChecked()
        effects.audio_normalize = self.audio_normalize.isChecked()
        effects.audio_compressor = self.audio_compressor.isChecked()
        effects.audio_limiter = self.audio_limiter.isChecked()
        
        # Анимация
        effects.motion_blur = self.motion_blur.isChecked()
        effects.motion_blur_amount = self.motion_blur_amount.value()
        effects.enable_3d_parallax = self.parallax_enabled.isChecked()
        effects.parallax_depth_layers = self.parallax_layers.value()
        effects.parallax_speed = self.parallax_speed.value()
        effects.parallax_direction = self.parallax_direction.currentText()
        
        # Валидация
        effects.validate()
        
        self.show_info(f"Настройки эффектов для канала '{self.current_channel.name}' сохранены")
    
    def _copy_effects(self):
        # Заглушка для копирования эффектов
        print("Копирование эффектов не реализовано")

    def _reset_effects(self):
        """Сбрасывает настройки эффектов"""
        if not self.current_channel:
            return
        
        if self.confirm_action("Сбросить все настройки эффектов к значениям по умолчанию?"):
            self.current_channel.effects = EffectSettings()
            self._load_channel_effects()
            self.show_info("Настройки эффектов сброшены")
    
    def _copy_effects(self):
        """Копирует эффекты в другой канал"""
        if not self.current_channel:
            return
        
        other_channels = [ch for ch in self.channels if ch.id != self.current_channel.id]
        if not other_channels:
            self.show_info("Нет других каналов для копирования")
            return
        
        channel_names = [ch.name for ch in other_channels]
        target_name, ok = QInputDialog.getItem(
            self, "Копирование настроек",
            "Выберите канал для копирования настроек:",
            channel_names, 0, False
        )
        
        if ok and target_name:
            target_channel = next((ch for ch in other_channels if ch.name == target_name), None)
            if target_channel:
                from dataclasses import asdict
                target_channel.effects = EffectSettings(**asdict(self.current_channel.effects))
                self.show_info(f"Настройки скопированы в канал '{target_name}'")

# ==================== ВКЛАДКА CAPCUT ЭФФЕКТОВ ====================

class CapCutTab(BaseWidget):
    """Вкладка CapCut эффектов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.current_channel: Optional[Channel] = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Выбор канала
        channel_layout = QHBoxLayout()
        channel_layout.addWidget(QLabel("📺 Канал:"))
        
        self.channel_combo = QComboBox()
        self.channel_combo.currentTextChanged.connect(self._load_channel_effects)
        channel_layout.addWidget(self.channel_combo)
        channel_layout.addStretch()
        layout.addLayout(channel_layout)
        
        # Прокручиваемая область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        
        # Анимации масштаба
        scale_group = CollapsibleGroupBox("🔍 Анимации масштаба")
        scale_layout = QVBoxLayout()
        
        scale_grid = QGridLayout()
        
        scale_effects = [
            ("zoomBurst", "Zoom Burst", "Резкий зум с затуханием"),
            ("pulse", "Pulse", "Пульсация"),
            ("bounce", "Bounce", "Отскок"),
            ("elastic", "Elastic", "Эластичный"),
            ("wave", "Wave", "Волна"),
            ("breathe", "Breathe", "Дыхание")
        ]
        
        self.scale_effects = {}
        for i, (effect_id, label, desc) in enumerate(scale_effects):
            widget = EffectCheckBox(effect_id, label, desc)
            self.scale_effects[effect_id] = widget
            scale_grid.addWidget(widget, i // 2, i % 2)
        
        scale_layout.addLayout(scale_grid)
        
        # Настройки масштаба
        scale_settings = QFormLayout()
        
        self.scale_amplitude = SliderWithLabel(0, 50, 15)
        scale_settings.addRow("Амплитуда:", self.scale_amplitude)
        
        self.zoom_burst_start = SliderWithLabel(100, 200, 150)
        scale_settings.addRow("Начальный зум:", self.zoom_burst_start)
        
        self.zoom_burst_decay = SliderWithLabel(0, 100, 80)
        scale_settings.addRow("Скорость затухания:", self.zoom_burst_decay)
        
        scale_layout.addLayout(scale_settings)
        scale_group.setLayout(scale_layout)
        scroll_layout.addWidget(scale_group)
        
        # Движение и тряска
        motion_group = CollapsibleGroupBox("🎯 Движение и тряска")
        motion_layout = QVBoxLayout()
        
        motion_grid = QGridLayout()
        
        motion_effects = [
            ("shake", "Shake", "Тряска камеры"),
            ("wobble", "Wobble", "Покачивание"),
            ("pendulum", "Pendulum", "Маятник"),
            ("swing", "Swing", "Раскачивание"),
            ("spin", "Spin", "Вращение"),
            ("flip", "Flip", "Переворот")
        ]
        
        self.motion_effects = {}
        for i, (effect_id, label, desc) in enumerate(motion_effects):
            widget = EffectCheckBox(effect_id, label, desc)
            self.motion_effects[effect_id] = widget
            motion_grid.addWidget(widget, i // 2, i % 2)
        
        motion_layout.addLayout(motion_grid)
        
        # Настройки движения
        motion_settings = QFormLayout()
        
        self.motion_intensity = SliderWithLabel(0, 100, 30)
        motion_settings.addRow("Интенсивность:", self.motion_intensity)
        
        motion_layout.addLayout(motion_settings)
        motion_group.setLayout(motion_layout)
        scroll_layout.addWidget(motion_group)
        
        # Цифровые эффекты
        digital_group = CollapsibleGroupBox("💫 Цифровые эффекты")
        digital_layout = QVBoxLayout()
        
        digital_grid = QGridLayout()
        
        digital_effects = [
            ("glitch", "Glitch", "Цифровой сбой"),
            ("chromatic", "Chromatic", "Хроматическая аберрация"),
            ("rgbSplit", "RGB Split", "Разделение RGB"),
            ("distortion", "Distortion", "Искажение"),
            ("zoomBlur", "Zoom Blur", "Радиальное размытие"),
            ("pixelate", "Pixelate", "Пикселизация")
        ]
        
        self.digital_effects = {}
        for i, (effect_id, label, desc) in enumerate(digital_effects):
            widget = EffectCheckBox(effect_id, label, desc)
            self.digital_effects[effect_id] = widget
            digital_grid.addWidget(widget, i // 2, i % 2)
        
        digital_layout.addLayout(digital_grid)
        digital_group.setLayout(digital_layout)
        scroll_layout.addWidget(digital_group)
        
        # Частота применения
        frequency_group = CollapsibleGroupBox("📊 Частота применения эффектов")
        frequency_layout = QFormLayout()
        
        self.effect_frequency = QComboBox()
        self.effect_frequency.addItems([
            ("all", "Ко всем клипам"),
            ("percent", "К проценту клипов"),
            ("every", "К каждому N-му клипу"),
            ("random", "Случайно")
        ])
        self.effect_frequency.currentIndexChanged.connect(self._on_frequency_changed)
        frequency_layout.addRow("Применять:", self.effect_frequency)
        
        # Процент
        self.percent_widget = QWidget()
        percent_layout = QHBoxLayout()
        percent_layout.setContentsMargins(0, 0, 0, 0)
        self.effect_percent = SliderWithLabel(0, 100, 50)
        percent_layout.addWidget(QLabel("Процент клипов:"))
        percent_layout.addWidget(self.effect_percent)
        self.percent_widget.setLayout(percent_layout)
        self.percent_widget.setVisible(False)
        frequency_layout.addRow(self.percent_widget)
        
        # Каждый N
        self.every_widget = QWidget()
        every_layout = QHBoxLayout()
        every_layout.setContentsMargins(0, 0, 0, 0)
        every_layout.addWidget(QLabel("Каждый:"))
        self.effect_every = QSpinBox()
        self.effect_every.setRange(2, 10)
        self.effect_every.setValue(3)
        every_layout.addWidget(self.effect_every)
        every_layout.addWidget(QLabel("клип"))
        every_layout.addStretch()
        self.every_widget.setLayout(every_layout)
        self.every_widget.setVisible(False)
        frequency_layout.addRow(self.every_widget)
        
        # Тайминг
        self.capcut_timing = QComboBox()
        self.capcut_timing.addItems([
            ("start", "В начале клипа"),
            ("middle", "В середине клипа"),
            ("end", "В конце клипа"),
            ("random", "Случайно")
        ])
        frequency_layout.addRow("Момент применения:", self.capcut_timing)
        
        self.avoid_repetition = QCheckBox("Избегать повторения эффектов подряд")
        self.avoid_repetition.setChecked(True)
        frequency_layout.addRow(self.avoid_repetition)
        
        frequency_group.setLayout(frequency_layout)
        scroll_layout.addWidget(frequency_group)
        
        # Пресеты
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Пресеты:"))
        
        presets = [
            ("dynamic", "🎬 Динамичный"),
            ("smooth", "🌊 Плавный"),
            ("epic", "⚡ Эпичный"),
            ("minimal", "⚪ Минимальный")
        ]
        
        for preset_id, label in presets:
            btn = QPushButton(label)
            btn.clicked.connect(lambda checked, p=preset_id: self._apply_preset(p))
            presets_layout.addWidget(btn)
        
        presets_layout.addStretch()
        scroll_layout.addLayout(presets_layout)
        
        # Кнопка сохранения
        save_btn = QPushButton("💾 Сохранить CapCut эффекты")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save_effects)
        scroll_layout.addWidget(save_btn)
        
        scroll_layout.addStretch()
        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        
        layout.addWidget(scroll)
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self._update_channel_combo()
    
    def _update_channel_combo(self):
        """Обновляет список каналов"""
        current = self.channel_combo.currentText()
        self.channel_combo.clear()
        self.channel_combo.addItems([ch.name for ch in self.channels])
        
        if current in [ch.name for ch in self.channels]:
            self.channel_combo.setCurrentText(current)
    
    def _on_frequency_changed(self, index: int):
        """Обработчик изменения частоты"""
        frequency = self.effect_frequency.currentData()
        self.percent_widget.setVisible(frequency == "percent")
        self.every_widget.setVisible(frequency == "every")
    
    def _load_channel_effects(self):
        """Загружает эффекты канала"""
        channel_name = self.channel_combo.currentText()
        if not channel_name:
            return
        
        self.current_channel = next((ch for ch in self.channels if ch.name == channel_name), None)
        if not self.current_channel:
            return
        
        effects = self.current_channel.effects
        
        # Загружаем эффекты
        for effect_id, widget in self.scale_effects.items():
            widget.setChecked(effect_id in effects.capcut_effects)
        
        for effect_id, widget in self.motion_effects.items():
            widget.setChecked(effect_id in effects.motion_effects)
        
        for effect_id, widget in self.digital_effects.items():
            widget.setChecked(
                effect_id in effects.capcut_effects or 
                effect_id in effects.motion_effects
            )
        
        # Настройки
        self.scale_amplitude.setValue(effects.scale_amplitude)
        self.zoom_burst_start.setValue(effects.zoom_burst_start)
        self.zoom_burst_decay.setValue(effects.zoom_burst_decay)
        if hasattr(self, "motion_intensity"):
            self.motion_intensity.setValue(effects.motion_intensity)
        
        # Частота
        for i in range(self.effect_frequency.count()):
            if self.effect_frequency.itemData(i) == effects.effect_frequency:
                self.effect_frequency.setCurrentIndex(i)
                break
        
        self.effect_percent.setValue(effects.effect_percent)
        self.effect_every.setValue(effects.effect_every)
        
        for i in range(self.capcut_timing.count()):
            if self.capcut_timing.itemData(i) == effects.capcut_timing:
                self.capcut_timing.setCurrentIndex(i)
                break
        
        self.avoid_repetition.setChecked(effects.avoid_repetition)
    
    def _copy_effects(self):
        # Заглушка для копирования эффектов
        print("Копирование эффектов не реализовано")

    def _reset_effects(self):
        # Заглушка для сброса эффектов
        print("Сброс эффектов не реализован")

    def _save_effects(self):
        """Сохраняет эффекты"""
        if not self.current_channel:
            self.show_warning("Выберите канал")
            return
        
        effects = self.current_channel.effects
        
        # Собираем выбранные эффекты
        capcut_effects = []
        motion_effects = []
        
        for effect_id, widget in self.scale_effects.items():
            if widget.isChecked():
                capcut_effects.append(effect_id)
        
        for effect_id, widget in self.motion_effects.items():
            if widget.isChecked():
                motion_effects.append(effect_id)
        
        for effect_id, widget in self.digital_effects.items():
            if widget.isChecked() and effect_id not in capcut_effects:
                capcut_effects.append(effect_id)
        
        # Обновляем настройки
        effects.capcut_effects = capcut_effects
        effects.motion_effects = motion_effects
        effects.scale_amplitude = self.scale_amplitude.value()
        effects.zoom_burst_start = self.zoom_burst_start.value()
        effects.zoom_burst_decay = self.zoom_burst_decay.value()
        if hasattr(self, "motion_intensity"):
            effects.motion_intensity = self.motion_intensity.value()
        else:
            effects.motion_intensity = 30
        effects.effect_frequency = self.effect_frequency.currentData()
        effects.effect_percent = self.effect_percent.value()
        effects.effect_every = self.effect_every.value()
        effects.capcut_timing = self.capcut_timing.currentData()
        effects.avoid_repetition = self.avoid_repetition.isChecked()
        
        # Валидация
        effects.validate()
        
        self.show_info(f"CapCut эффекты для канала '{self.current_channel.name}' сохранены")