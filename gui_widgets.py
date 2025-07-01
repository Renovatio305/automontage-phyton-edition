#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Специализированные виджеты для Auto Montage Builder Pro
"""

import time
import logging
from typing import List, Dict, Optional, Set
from pathlib import Path

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from models import Channel, EffectSettings, ExportSettings, OverlaySettings
from gui_base import BaseWidget

logger = logging.getLogger(__name__)

# ==================== КАРТОЧКИ КАНАЛОВ ====================

class ChannelCard(QFrame):
    """Карточка канала для отображения в списке"""
    
    clicked = Signal()
    edit_requested = Signal(str)
    delete_requested = Signal(str)
    duplicate_requested = Signal(str)
    export_requested = Signal(str)
    
    def __init__(self, channel: Channel, selected: bool = False, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.selected = selected
        self.setup_ui()
        self.update_style()
    
    def setup_ui(self):
        self.setFrameStyle(QFrame.Box)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Заголовок с кнопками действий
        header_layout = QHBoxLayout()
        
        # Иконка и название
        icon_label = QLabel()
        icon_map = {
            "youtube": "📺",
            "shorts": "📱", 
            "instagram": "📷",
            "cinematic": "🎬"
        }
        icon = icon_map.get(self.channel.template, "📹")
        icon_label.setText(icon)
        icon_label.setStyleSheet("font-size: 20px;")
        header_layout.addWidget(icon_label)
        
        name_label = QLabel(self.channel.name)
        name_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Кнопки действий
        self._create_action_buttons(header_layout)
        
        layout.addLayout(header_layout)
        
        # Описание
        if self.channel.description:
            desc_label = QLabel(self.channel.description)
            desc_label.setObjectName("infoLabel")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        # Информация о настройках
        info_label = QLabel(
            f"{self.channel.export.resolution} • "
            f"{self.channel.export.fps}fps • "
            f"{self.channel.export.bitrate}Mbps"
        )
        info_label.setObjectName("infoLabel")
        layout.addWidget(info_label)
        
        # Теги эффектов
        tags_widget = self._create_tags_widget()
        layout.addWidget(tags_widget)
        
        self.setLayout(layout)
    
    def _create_action_buttons(self, layout: QHBoxLayout):
        """Создает кнопки действий"""
        button_style = """
            QPushButton {
                background: transparent;
                border: none;
                font-size: 16px;
                padding: 4px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """
        
        # Кнопка редактирования
        edit_btn = QPushButton("✏️")
        edit_btn.setToolTip("Редактировать канал")
        edit_btn.setStyleSheet(button_style)
        edit_btn.setFixedSize(28, 28)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.channel.id))
        layout.addWidget(edit_btn)
        
        # Кнопка дублирования
        duplicate_btn = QPushButton("📋")
        duplicate_btn.setToolTip("Дублировать канал")
        duplicate_btn.setStyleSheet(button_style)
        duplicate_btn.setFixedSize(28, 28)
        duplicate_btn.clicked.connect(lambda: self.duplicate_requested.emit(self.channel.id))
        layout.addWidget(duplicate_btn)
        
        # Кнопка экспорта
        export_btn = QPushButton("📤")
        export_btn.setToolTip("Экспортировать канал")
        export_btn.setStyleSheet(button_style)
        export_btn.setFixedSize(28, 28)
        export_btn.clicked.connect(lambda: self.export_requested.emit(self.channel.id))
        layout.addWidget(export_btn)
        
        # Кнопка удаления
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("Удалить канал")
        delete_btn.setStyleSheet(button_style + """
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        delete_btn.setFixedSize(28, 28)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.channel.id))
        layout.addWidget(delete_btn)
    
    def _create_tags_widget(self) -> QWidget:
        """Создает виджет с тегами эффектов"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        tag_style = """
            QLabel {
                padding: 2px 8px;
                border-radius: 10px;
                font-size: 11px;
            }
        """
        
        # Ken Burns
        if self.channel.effects.ken_burns:
            tag = QLabel("Ken Burns")
            tag.setStyleSheet(tag_style + "background: #00d4aa22; color: #00d4aa;")
            layout.addWidget(tag)
        
        # CapCut FX
        if self.channel.effects.capcut_effects:
            tag = QLabel("CapCut FX")
            tag.setStyleSheet(tag_style + "background: #ff4fe622; color: #ff4fe6;")
            layout.addWidget(tag)
        
        # Оверлеи
        if self.channel.overlays.enabled:
            tag = QLabel("Оверлеи")
            tag.setStyleSheet(tag_style + "background: #4fc3f722; color: #4fc3f7;")
            layout.addWidget(tag)
        
        # 3D
        if self.channel.effects.enable_3d_parallax:
            tag = QLabel("3D")
            tag.setStyleSheet(tag_style + "background: #ffd54f22; color: #ffd54f;")
            layout.addWidget(tag)
        
        # Цветокоррекция
        if self.channel.effects.color_correction:
            tag = QLabel(self.channel.effects.color_filter.title())
            tag.setStyleSheet(tag_style + "background: #ab47bc22; color: #ab47bc;")
            layout.addWidget(tag)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def update_style(self):
        """Обновляет стиль карточки"""
        if self.selected:
            self.setStyleSheet("""
                ChannelCard {
                    background-color: #00d4aa22;
                    border: 2px solid #00d4aa;
                    border-radius: 8px;
                    padding: 12px;
                }
            """)
        else:
            self.setStyleSheet("""
                ChannelCard {
                    background-color: #2d2d2d;
                    border: 1px solid #444;
                    border-radius: 8px;
                    padding: 12px;
                }
                ChannelCard:hover {
                    background-color: #3d3d3d;
                    border-color: #555;
                }
            """)
    
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)
    
    def set_selected(self, selected: bool):
        """Устанавливает состояние выбора"""
        self.selected = selected
        self.update_style()

# ==================== ДИАЛОГ КАНАЛА ====================

class ChannelDialog(QDialog):
    """Диалог создания/редактирования канала"""
    
    def __init__(self, channel: Optional[Channel] = None, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.is_edit_mode = channel is not None
        
        self.setWindowTitle("Редактировать канал" if self.is_edit_mode else "Новый канал")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        
        self.setup_ui()
        
        if self.is_edit_mode:
            self.load_channel_data()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Основная информация
        info_group = QGroupBox("📋 Основная информация")
        info_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Например: YouTube канал")
        info_layout.addRow("Название:", self.name_edit)
        
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Краткое описание канала")
        info_layout.addRow("Описание:", self.description_edit)
        
        self.template_combo = QComboBox()
        self.template_combo.addItems([
            ("youtube", "YouTube (16:9)"),
            ("shorts", "Shorts/Reels (9:16)"),
            ("instagram", "Instagram (1:1)"),
            ("cinematic", "Cinematic (21:9)"),
            ("custom", "Пользовательский")
        ])
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        info_layout.addRow("Шаблон:", self.template_combo)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Настройки экспорта
        export_group = QGroupBox("🎬 Настройки экспорта")
        export_layout = QFormLayout()
        
        # Разрешение
        resolution_layout = QHBoxLayout()
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080", "3840x2160", "2560x1440", "1280x720",
            "1080x1920", "1080x1080", "720x1280", "custom"
        ])
        self.resolution_combo.currentTextChanged.connect(self._on_resolution_changed)
        resolution_layout.addWidget(self.resolution_combo)
        
        self.custom_resolution_widget = QWidget()
        custom_res_layout = QHBoxLayout()
        custom_res_layout.setContentsMargins(0, 0, 0, 0)
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(320, 7680)
        self.width_spin.setValue(1920)
        custom_res_layout.addWidget(QLabel("Ш:"))
        custom_res_layout.addWidget(self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(240, 4320)
        self.height_spin.setValue(1080)
        custom_res_layout.addWidget(QLabel("В:"))
        custom_res_layout.addWidget(self.height_spin)
        
        self.custom_resolution_widget.setLayout(custom_res_layout)
        self.custom_resolution_widget.setVisible(False)
        resolution_layout.addWidget(self.custom_resolution_widget)
        
        export_layout.addRow("Разрешение:", resolution_layout)
        
        # FPS
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 120)
        self.fps_spin.setValue(30)
        self.fps_spin.setSuffix(" fps")
        export_layout.addRow("Частота кадров:", self.fps_spin)
        
        # Битрейт
        self.bitrate_spin = QSpinBox()
        self.bitrate_spin.setRange(1, 100)
        self.bitrate_spin.setValue(8)
        self.bitrate_spin.setSuffix(" Mbps")
        export_layout.addRow("Битрейт:", self.bitrate_spin)
        
        # Качество
        self.quality_combo = QComboBox()
        self.quality_combo.addItems([
            ("veryfast", "Очень быстро"),
            ("faster", "Быстро"),
            ("fast", "Быстро+"),
            ("medium", "Баланс"),
            ("slow", "Качество"),
            ("slower", "Качество+"),
            ("veryslow", "Максимум")
        ])
        self.quality_combo.setCurrentIndex(3)  # medium
        export_layout.addRow("Пресет качества:", self.quality_combo)
        
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        
        # Быстрые эффекты
        effects_group = QGroupBox("✨ Быстрая настройка эффектов")
        effects_layout = QVBoxLayout()
        
        self.enable_ken_burns = QCheckBox("Включить Ken Burns эффекты")
        effects_layout.addWidget(self.enable_ken_burns)
        
        self.enable_transitions = QCheckBox("Включить переходы между клипами")
        effects_layout.addWidget(self.enable_transitions)
        
        self.enable_capcut = QCheckBox("Включить CapCut эффекты")
        effects_layout.addWidget(self.enable_capcut)
        
        self.enable_color = QCheckBox("Включить цветокоррекцию")
        effects_layout.addWidget(self.enable_color)
        
        effects_group.setLayout(effects_layout)
        layout.addWidget(effects_group)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("Сохранить" if self.is_edit_mode else "Создать")
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._validate_and_accept)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _on_template_changed(self, index: int):
        """Обработчик изменения шаблона"""
        template = self.template_combo.currentData()
        
        template_settings = {
            "youtube": {"resolution": "1920x1080", "fps": 30, "bitrate": 8},
            "shorts": {"resolution": "1080x1920", "fps": 30, "bitrate": 10},
            "instagram": {"resolution": "1080x1080", "fps": 30, "bitrate": 6},
            "cinematic": {"resolution": "3840x2160", "fps": 24, "bitrate": 20}
        }
        
        if template in template_settings:
            settings = template_settings[template]
            self.resolution_combo.setCurrentText(settings["resolution"])
            self.fps_spin.setValue(settings["fps"])
            self.bitrate_spin.setValue(settings["bitrate"])
    
    def _on_resolution_changed(self, text: str):
        """Обработчик изменения разрешения"""
        self.custom_resolution_widget.setVisible(text == "custom")
    
    def _validate_and_accept(self):
        """Валидация и сохранение"""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Предупреждение", "Введите название канала")
            return
        
        self.accept()
    
    def load_channel_data(self):
        """Загружает данные канала"""
        if not self.channel:
            return
        
        self.name_edit.setText(self.channel.name)
        self.description_edit.setText(self.channel.description)
        
        # Находим соответствующий шаблон
        for i in range(self.template_combo.count()):
            if self.template_combo.itemData(i) == self.channel.template:
                self.template_combo.setCurrentIndex(i)
                break
        
        # Экспорт настройки
        self.resolution_combo.setCurrentText(self.channel.export.resolution)
        if self.channel.export.resolution == "custom":
            self.width_spin.setValue(self.channel.export.custom_width)
            self.height_spin.setValue(self.channel.export.custom_height)
        
        self.fps_spin.setValue(self.channel.export.fps)
        self.bitrate_spin.setValue(self.channel.export.bitrate)
        
        # Находим качество
        for i in range(self.quality_combo.count()):
            if self.quality_combo.itemData(i) == self.channel.export.quality.preset:
                self.quality_combo.setCurrentIndex(i)
                break
        
        # Эффекты
        self.enable_ken_burns.setChecked(bool(self.channel.effects.ken_burns))
        self.enable_transitions.setChecked(bool(self.channel.effects.transitions))
        self.enable_capcut.setChecked(bool(self.channel.effects.capcut_effects))
        self.enable_color.setChecked(self.channel.effects.color_correction)
    
    def get_channel(self) -> Channel:
        """Возвращает настроенный канал"""
        from models import Channel, ExportSettings, VideoQuality, EffectSettings
        
        if self.channel:
            # Обновляем существующий
            channel = self.channel
        else:
            # Создаем новый
            channel = Channel(
                id=f"channel_{int(time.time())}",
                name="",
                description="",
                template="youtube"
            )
        
        # Основная информация
        channel.name = self.name_edit.text().strip()
        channel.description = self.description_edit.text().strip()
        channel.template = self.template_combo.currentData() or "youtube"
        
        # Экспорт настройки
        resolution = self.resolution_combo.currentText()
        if resolution == "custom":
            channel.export.custom_width = self.width_spin.value()
            channel.export.custom_height = self.height_spin.value()
        channel.export.resolution = resolution
        channel.export.fps = self.fps_spin.value()
        channel.export.bitrate = self.bitrate_spin.value()
        channel.export.quality.preset = self.quality_combo.currentData() or "medium"
        
        # Быстрые эффекты
        if self.enable_ken_burns.isChecked() and not channel.effects.ken_burns:
            channel.effects.ken_burns = ["zoomIn", "panRight"]
        elif not self.enable_ken_burns.isChecked():
            channel.effects.ken_burns = []
        
        if self.enable_transitions.isChecked() and not channel.effects.transitions:
            channel.effects.transitions = ["fade", "dissolve"]
        elif not self.enable_transitions.isChecked():
            channel.effects.transitions = []
        
        if self.enable_capcut.isChecked() and not channel.effects.capcut_effects:
            channel.effects.capcut_effects = ["zoomBurst", "bounce"]
        elif not self.enable_capcut.isChecked():
            channel.effects.capcut_effects = []
        
        channel.effects.color_correction = self.enable_color.isChecked()
        if self.enable_color.isChecked() and channel.effects.color_filter == "none":
            channel.effects.color_filter = "cinematic"
        
        # Валидация
        channel.validate()
        
        return channel

# ==================== ПАНЕЛЬ ПРОЕКТА ====================

class ProjectInfoPanel(BaseWidget):
    """Панель информации о проекте"""
    
    scan_requested = Signal()
    folder_changed = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.project_folder = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Выбор папки
        folder_group = QGroupBox("📁 Папка проекта")
        folder_layout = QVBoxLayout()
        
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Выберите папку с медиа файлами...")
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.browse_btn)
        
        self.scan_btn = QPushButton("🔍 Сканировать")
        self.scan_btn.clicked.connect(self.scan_requested.emit)
        self.scan_btn.setEnabled(False)
        path_layout.addWidget(self.scan_btn)
        
        folder_layout.addLayout(path_layout)
        
        # Опции сканирования
        self.include_videos_check = QCheckBox("Включить видео файлы")
        self.include_videos_check.setChecked(True)
        folder_layout.addWidget(self.include_videos_check)
        
        folder_group.setLayout(folder_layout)
        layout.addWidget(folder_group)
        
        # Информация о проекте
        info_group = QGroupBox("📊 Информация о проекте")
        info_layout = QVBoxLayout()
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setPlainText("Выберите папку проекта и нажмите 'Сканировать'")
        info_layout.addWidget(self.info_text)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        self.setLayout(layout)
    
    def _browse_folder(self):
        """Выбор папки проекта"""
        folder = QFileDialog.getExistingDirectory(
            self, "Выберите папку проекта",
            str(self.project_folder) if self.project_folder else ""
        )
        
        if folder:
            self.set_project_folder(folder)
    
    def set_project_folder(self, folder: str):
        """Устанавливает папку проекта"""
        self.project_folder = Path(folder)
        self.path_edit.setText(str(self.project_folder))
        self.scan_btn.setEnabled(True)
        self.folder_changed.emit(folder)
    
    def update_info(self, scan_result: Dict[str, int]):
        """Обновляет информацию о проекте"""
        info_text = f"""📊 Результаты сканирования:

✅ Изображений: {scan_result.get('images', 0)}
🎥 Видео: {scan_result.get('videos', 0)}
🎵 Аудио файлов: {scan_result.get('audio', 0)}
📎 Готовых пар: {scan_result.get('pairs', 0)}

Формат файлов:
• Изображения: 0001_image.jpg + 0001_audio.mp3
• Видео: 0002_video.mp4 + 0002_audio.mp3

Статус: {'✅ Готово к генерации' if scan_result.get('pairs', 0) > 0 else '⚠️ Не найдено пар файлов'}"""
        
        self.info_text.setPlainText(info_text)
    
    def get_include_videos(self) -> bool:
        """Возвращает флаг включения видео"""
        return self.include_videos_check.isChecked()

# ==================== ПАНЕЛЬ ВЫБОРА КАНАЛОВ ====================

class ChannelSelectionPanel(BaseWidget):
    """Панель для выбора каналов для генерации"""
    
    selection_changed = Signal(set)  # Set[str] - IDs выбранных каналов
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.channels: List[Channel] = []
        self.selected_ids: Set[str] = set()
        self.channel_cards: Dict[str, ChannelCard] = {}
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Заголовок с кнопками
        header_layout = QHBoxLayout()
        
        title = QLabel("📺 Выберите каналы для генерации")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.select_all)
        header_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("Снять выделение")
        deselect_all_btn.clicked.connect(self.deselect_all)
        header_layout.addWidget(deselect_all_btn)
        
        layout.addLayout(header_layout)
        
        # Прокручиваемая область для карточек
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        self.cards_widget = QWidget()
        self.cards_layout = QGridLayout()
        self.cards_layout.setSpacing(10)
        self.cards_widget.setLayout(self.cards_layout)
        
        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll)
        
        # Информация о выборе
        self.selection_info = QLabel("Выбрано каналов: 0")
        self.selection_info.setObjectName("infoLabel")
        layout.addWidget(self.selection_info)
        
        self.setLayout(layout)
    
    def set_channels(self, channels: List[Channel]):
        """Устанавливает список каналов"""
        self.channels = channels
        self._rebuild_cards()
    
    def _rebuild_cards(self):
        """Перестраивает карточки каналов"""
        # Очищаем старые карточки
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.channel_cards.clear()
        
        # Создаем новые карточки
        columns = 2
        for i, channel in enumerate(self.channels):
            card = ChannelCard(channel, channel.id in self.selected_ids)
            card.clicked.connect(lambda ch_id=channel.id: self._toggle_selection(ch_id))
            
            self.channel_cards[channel.id] = card
            self.cards_layout.addWidget(card, i // columns, i % columns)
        
        # Добавляем растяжку в конец
        self.cards_layout.setRowStretch(len(self.channels) // columns + 1, 1)
        
        self._update_selection_info()
    
    def _toggle_selection(self, channel_id: str):
        """Переключает выбор канала"""
        if channel_id in self.selected_ids:
            self.selected_ids.remove(channel_id)
        else:
            self.selected_ids.add(channel_id)
        
        # Обновляем визуальное состояние
        if channel_id in self.channel_cards:
            card = self.channel_cards[channel_id]
            card.set_selected(channel_id in self.selected_ids)
        
        self._update_selection_info()
        self.selection_changed.emit(self.selected_ids.copy())
    
    def select_all(self):
        """Выбирает все каналы"""
        self.selected_ids = {ch.id for ch in self.channels}
        for channel_id, card in self.channel_cards.items():
            card.set_selected(True)
        self._update_selection_info()
        self.selection_changed.emit(self.selected_ids.copy())
    
    def deselect_all(self):
        """Снимает выделение со всех каналов"""
        self.selected_ids.clear()
        for card in self.channel_cards.values():
            card.set_selected(False)
        self._update_selection_info()
        self.selection_changed.emit(self.selected_ids.copy())
    
    def _update_selection_info(self):
        """Обновляет информацию о выборе"""
        count = len(self.selected_ids)
        self.selection_info.setText(f"Выбрано каналов: {count}")
    
    def get_selected_channels(self) -> List[Channel]:
        """Возвращает выбранные каналы"""
        return [ch for ch in self.channels if ch.id in self.selected_ids]