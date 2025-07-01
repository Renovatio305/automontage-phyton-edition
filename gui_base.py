#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Базовые GUI компоненты для Auto Montage Builder Pro
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
except ImportError:
    print("Установите PySide6: pip install PySide6")
    import sys
    sys.exit(1)

logger = logging.getLogger(__name__)

# ==================== СТИЛИ ====================

class StyleManager:
    """Менеджер стилей для современного интерфейса"""
    
    @staticmethod
    def get_dark_theme() -> str:
        """Возвращает темную тему"""
        return """
        QMainWindow {
            background-color: #1a1a1a;
        }
        
        QWidget {
            background-color: #1a1a1a;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 12px;
        }
        
        QTabWidget {
            background-color: #1a1a1a;
        }
        
        QTabWidget::pane {
            border: 1px solid #333;
            background-color: #1a1a1a;
            border-radius: 4px;
        }
        
        QTabBar::tab {
            background-color: #2d2d2d;
            color: #b0b0b0;
            padding: 12px 20px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        
        QTabBar::tab:selected {
            background-color: #00d4aa;
            color: #000;
            font-weight: bold;
        }
        
        QTabBar::tab:hover {
            background-color: #3d3d3d;
            color: #fff;
        }
        
        QPushButton {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444;
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: 500;
            min-height: 24px;
        }
        
        QPushButton:hover {
            background-color: #3d3d3d;
            border-color: #555;
        }
        
        QPushButton:pressed {
            background-color: #252525;
        }
        
        QPushButton:disabled {
            background-color: #1a1a1a;
            color: #666;
            border-color: #333;
        }
        
        QPushButton#primaryButton {
            background-color: #00d4aa;
            color: #000;
            border: none;
            font-weight: bold;
        }
        
        QPushButton#primaryButton:hover {
            background-color: #00e8bb;
        }
        
        QPushButton#primaryButton:pressed {
            background-color: #00b090;
        }
        
        QPushButton#dangerButton {
            background-color: #d32f2f;
            color: white;
            border: none;
        }
        
        QPushButton#dangerButton:hover {
            background-color: #e53935;
        }
        
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444;
            padding: 6px 10px;
            border-radius: 4px;
            selection-background-color: #00d4aa;
            selection-color: #000;
        }
        
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #00d4aa;
            outline: none;
        }
        
        QComboBox {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #444;
            padding: 6px 10px;
            border-radius: 4px;
            min-height: 24px;
        }
        
        QComboBox:hover {
            border-color: #555;
        }
        
        QComboBox:focus {
            border-color: #00d4aa;
        }
        
        QComboBox::drop-down {
            border: none;
            width: 20px;
        }
        
        QComboBox::down-arrow {
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid #888;
            margin-right: 5px;
        }
        
        QCheckBox, QRadioButton {
            spacing: 8px;
            color: #e0e0e0;
        }
        
        QCheckBox::indicator, QRadioButton::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #666;
            background-color: #2d2d2d;
        }
        
        QCheckBox::indicator {
            border-radius: 3px;
        }
        
        QRadioButton::indicator {
            border-radius: 9px;
        }
        
        QCheckBox::indicator:checked, QRadioButton::indicator:checked {
            background-color: #00d4aa;
            border-color: #00d4aa;
        }
        
        QSlider::groove:horizontal {
            height: 6px;
            background-color: #2d2d2d;
            border-radius: 3px;
        }
        
        QSlider::handle:horizontal {
            width: 18px;
            height: 18px;
            background-color: #00d4aa;
            border-radius: 9px;
            margin: -6px 0;
        }
        
        QSlider::handle:horizontal:hover {
            background-color: #00e8bb;
        }
        
        QProgressBar {
            background-color: #2d2d2d;
            border: 1px solid #444;
            border-radius: 4px;
            text-align: center;
            height: 24px;
        }
        
        QProgressBar::chunk {
            background-color: #00d4aa;
            border-radius: 3px;
        }
        
        QGroupBox {
            font-weight: bold;
            border: 1px solid #444;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 10px;
            color: #00d4aa;
        }
        
        QListWidget, QTreeWidget, QTableWidget {
            background-color: #2d2d2d;
            border: 1px solid #444;
            border-radius: 4px;
            outline: none;
        }
        
        QListWidget::item, QTreeWidget::item, QTableWidget::item {
            padding: 6px;
            border-bottom: 1px solid #333;
        }
        
        QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
            background-color: #00d4aa;
            color: #000;
        }
        
        QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
            background-color: #3d3d3d;
        }
        
        QScrollBar:vertical {
            background-color: #2d2d2d;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #555;
            border-radius: 6px;
            min-height: 20px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #666;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        
        QLabel {
            color: #e0e0e0;
        }
        
        QLabel#titleLabel {
            font-size: 24px;
            font-weight: bold;
            color: #00d4aa;
            padding: 20px 0;
        }
        
        QLabel#sectionLabel {
            font-size: 16px;
            font-weight: bold;
            color: #00d4aa;
            padding: 10px 0;
        }
        
        QLabel#infoLabel {
            color: #888;
            font-size: 11px;
        }
        
        QToolTip {
            background-color: #2d2d2d;
            color: #e0e0e0;
            border: 1px solid #00d4aa;
            padding: 5px;
            border-radius: 4px;
        }
        
        QMessageBox {
            background-color: #1a1a1a;
        }
        
        QMessageBox QPushButton {
            min-width: 80px;
        }
        """
    
    @staticmethod
    def get_light_theme() -> str:
        """Возвращает светлую тему (заготовка)"""
        # TODO: Реализовать светлую тему
        return StyleManager.get_dark_theme()

# ==================== СИГНАЛЫ ====================

class SignalEmitter(QObject):
    """Эмиттер сигналов для потокобезопасного обновления UI"""
    progress_updated = Signal(float, str)
    log_message = Signal(str, str)
    generation_finished = Signal(bool, str)
    error_occurred = Signal(str)
    warning_occurred = Signal(str)
    info_message = Signal(str)

# ==================== ВИДЖЕТЫ ====================

class EffectCheckBox(QWidget):
    """Чекбокс с описанием для эффектов"""
    
    toggled = Signal(bool)
    
    def __init__(self, effect_id: str, label: str, description: str = "", parent=None):
        super().__init__(parent)
        self.effect_id = effect_id
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.checkbox = QCheckBox(label)
        self.checkbox.toggled.connect(self.toggled.emit)
        layout.addWidget(self.checkbox)
        
        if description:
            info_label = QLabel(description)
            info_label.setObjectName("infoLabel")
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def setChecked(self, checked: bool):
        self.checkbox.setChecked(checked)
    
    def isChecked(self) -> bool:
        return self.checkbox.isChecked()
    
    def setEnabled(self, enabled: bool):
        self.checkbox.setEnabled(enabled)
        super().setEnabled(enabled)

class SliderWithLabel(QWidget):
    """Слайдер с отображением значения"""
    
    valueChanged = Signal(int)
    
    def __init__(self, min_val: int, max_val: int, default: int, 
                 suffix: str = "%", parent=None):
        super().__init__(parent)
        self.suffix = suffix
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(default)
        self.slider.valueChanged.connect(self._on_value_changed)
        
        self.label = QLabel(f"{default}{suffix}")
        self.label.setFixedWidth(50)
        self.label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.slider)
        layout.addWidget(self.label)
        
        self.setLayout(layout)
    
    def _on_value_changed(self, value):
        self.label.setText(f"{value}{self.suffix}")
        self.valueChanged.emit(value)
    
    def value(self) -> int:
        return self.slider.value()
    
    def setValue(self, value: int):
        self.slider.setValue(value)
    
    def setEnabled(self, enabled: bool):
        self.slider.setEnabled(enabled)
        self.label.setEnabled(enabled)
        super().setEnabled(enabled)

class FilePathSelector(QWidget):
    """Виджет для выбора пути к файлу или папке"""
    
    pathChanged = Signal(str)
    
    def __init__(self, mode: str = "file", filter: str = "", 
                 placeholder: str = "", parent=None):
        super().__init__(parent)
        self.mode = mode  # "file", "folder", "save"
        self.filter = filter
        
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(placeholder)
        self.path_edit.setReadOnly(True)
        layout.addWidget(self.path_edit)
        
        self.browse_btn = QPushButton("Обзор...")
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn)
        
        self.setLayout(layout)
    
    def _browse(self):
        if self.mode == "file":
            path, _ = QFileDialog.getOpenFileName(
                self, "Выберите файл", "", self.filter
            )
        elif self.mode == "folder":
            path = QFileDialog.getExistingDirectory(
                self, "Выберите папку"
            )
        elif self.mode == "save":
            path, _ = QFileDialog.getSaveFileName(
                self, "Сохранить как", "", self.filter
            )
        else:
            return
        
        if path:
            self.set_path(path)
    
    def set_path(self, path: str):
        self.path_edit.setText(path)
        self.pathChanged.emit(path)
    
    def get_path(self) -> str:
        return self.path_edit.text()
    
    def clear(self):
        self.path_edit.clear()
        self.pathChanged.emit("")

class CollapsibleGroupBox(QGroupBox):
    """Сворачиваемый GroupBox"""
    
    def __init__(self, title: str = "", parent=None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        
        # Сохраняем оригинальную высоту
        self.expanded_height = None
        
        self.toggled.connect(self._on_toggled)
    
    def _on_toggled(self, checked: bool):
        if checked:
            # Разворачиваем
            if self.expanded_height:
                self.setMaximumHeight(self.expanded_height)
        else:
            # Сворачиваем
            if not self.expanded_height:
                self.expanded_height = self.height()
            self.setMaximumHeight(30)  # Высота заголовка

class ProgressDialog(QDialog):
    """Диалог прогресса операции"""
    
    cancelled = Signal()
    
    def __init__(self, title: str = "Обработка...", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(400)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Текст статуса
        self.status_label = QLabel("Инициализация...")
        layout.addWidget(self.status_label)
        
        # Прогресс бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)
        
        # Детали (скрытый по умолчанию)
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(150)
        self.details_text.setVisible(False)
        layout.addWidget(self.details_text)
        
        # Кнопки
        button_layout = QHBoxLayout()
        
        self.details_btn = QPushButton("Показать детали")
        self.details_btn.setCheckable(True)
        self.details_btn.toggled.connect(self.details_text.setVisible)
        button_layout.addWidget(self.details_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.cancelled.emit)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, value: float, text: str = ""):
        """Обновляет прогресс"""
        self.progress_bar.setValue(int(value))
        if text:
            self.status_label.setText(text)
    
    def add_detail(self, text: str):
        """Добавляет детальную информацию"""
        self.details_text.append(text)
    
    def set_completed(self):
        """Устанавливает состояние завершения"""
        self.progress_bar.setValue(100)
        self.status_label.setText("Завершено!")
        self.cancel_btn.setText("Закрыть")
        self.cancel_btn.clicked.disconnect()
        self.cancel_btn.clicked.connect(self.accept)

class LogWidget(QTextEdit):
    """Виджет для отображения логов"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setMaximumHeight(200)
        
        # Настройка шрифта
        font = QFont("Consolas", 9)
        self.setFont(font)
    
    def add_message(self, message: str, level: str = "info"):
        """Добавляет сообщение в лог"""
        import time
        timestamp = time.strftime("%H:%M:%S")
        
        # Определяем цвет по уровню
        color_map = {
            "error": "#ff5252",
            "warning": "#ffa726",
            "info": "#66bb6a",
            "debug": "#888888"
        }
        color = color_map.get(level, "#e0e0e0")
        
        # Форматируем HTML
        html = f'<span style="color: {color}">[{timestamp}]</span> {message}'
        self.append(html)
        
        # Прокручиваем вниз
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Очищает лог"""
        self.clear()

# ==================== ДИАЛОГИ ====================

class AboutDialog(QDialog):
    """Диалог 'О программе'"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("О программе")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Логотип и название
        title_label = QLabel("🎬 AUTO MONTAGE BUILDER PRO")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Версия
        version_label = QLabel("Enhanced Python Edition v5.0.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 14px; color: #888;")
        layout.addWidget(version_label)
        
        # Описание
        about_text = QTextEdit()
        about_text.setReadOnly(True)
        about_text.setHtml("""
        <h3>Возможности:</h3>
        <ul>
            <li>Автоматическая расстановка файлов на таймлайне</li>
            <li>Поддержка видео файлов с зацикливанием</li>
            <li>Ken Burns эффекты с плавной анимацией (60 FPS)</li>
            <li>CapCut-style эффекты и анимации</li>
            <li>Продвинутые переходы между клипами</li>
            <li>Fade In/Out эффекты</li>
            <li>3D Parallax эффекты (экспериментально)</li>
            <li>Видео и изображения оверлеи</li>
            <li>Обработка аудио с эффектами</li>
            <li>GPU ускорение (NVIDIA, AMD, Intel)</li>
            <li>Современный интерфейс на PySide6</li>
        </ul>
        
        <h3>Системные требования:</h3>
        <ul>
            <li>Python 3.8+</li>
            <li>FFmpeg 4.0+</li>
            <li>PySide6</li>
            <li>8 GB RAM (рекомендуется 16 GB)</li>
            <li>GPU с поддержкой аппаратного кодирования (опционально)</li>
        </ul>
        
        <p style="margin-top: 20px;">
        <b>Автор:</b> AutoMontage Team<br>
        <b>Лицензия:</b> MIT License<br>
        <b>Поддержка:</b> automontage@support.com
        </p>
        """)
        layout.addWidget(about_text)
        
        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)
        
        self.setLayout(layout)

class ErrorDialog(QMessageBox):
    """Диалог для отображения ошибок с деталями"""
    
    def __init__(self, title: str, message: str, details: str = "", parent=None):
        super().__init__(parent)
        self.setIcon(QMessageBox.Critical)
        self.setWindowTitle(title)
        self.setText(message)
        
        if details:
            self.setDetailedText(details)
        
        self.setStandardButtons(QMessageBox.Ok)

# ==================== БАЗОВЫЕ КЛАССЫ ====================

class BaseThread(QThread):
    """Базовый класс для потоков с обработкой ошибок"""
    
    error_occurred = Signal(str, str)  # message, details
    progress_updated = Signal(float, str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_cancelled = False
    
    def cancel(self):
        """Отменяет выполнение"""
        self.is_cancelled = True
    
    def handle_error(self, error: Exception, context: str = ""):
        """Обрабатывает ошибку"""
        import traceback
        
        message = f"Ошибка в {context}: {str(error)}" if context else str(error)
        details = traceback.format_exc()
        
        logger.error(f"{message}\n{details}")
        self.error_occurred.emit(message, details)

class BaseWidget(QWidget):
    """Базовый класс для виджетов с общей функциональностью"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = QSettings("AutoMontage", "AutoMontageBuilderPro")
    
    def save_state(self, key: str):
        """Сохраняет состояние виджета"""
        # Переопределить в наследниках
        pass
    
    def restore_state(self, key: str):
        """Восстанавливает состояние виджета"""
        # Переопределить в наследниках
        pass
    
    def show_error(self, message: str, details: str = ""):
        """Показывает диалог ошибки"""
        dialog = ErrorDialog("Ошибка", message, details, self)
        dialog.exec()
    
    def show_warning(self, message: str):
        """Показывает предупреждение"""
        QMessageBox.warning(self, "Предупреждение", message)
    
    def show_info(self, message: str):
        """Показывает информационное сообщение"""
        QMessageBox.information(self, "Информация", message)
    
    def confirm_action(self, message: str, title: str = "Подтверждение") -> bool:
        """Запрашивает подтверждение действия"""
        reply = QMessageBox.question(
            self, title, message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        return reply == QMessageBox.Yes