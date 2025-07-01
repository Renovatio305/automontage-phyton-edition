#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Главное окно приложения Auto Montage Builder Pro
"""

import sys
import time
import logging
from typing import List, Optional
from pathlib import Path

from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *

from models import Channel, DataManager
from engine import MontageEngine
from gui_base import StyleManager, SignalEmitter, AboutDialog, ProgressDialog
from gui_tabs import (
    GenerationTab, ChannelsTab, EffectsTab, 
    CapCutTab, OverlaysTab, SettingsTab
)
from utils import setup_logging

logger = logging.getLogger(__name__)

# ==================== ПОТОК ГЕНЕРАЦИИ ====================

class GenerationThread(QThread):
    """Поток для генерации монтажа"""
    
    def __init__(self, engine: MontageEngine, channels: List[Channel], 
                 test_mode: bool = False, process_audio: bool = True,
                 parent=None):
        super().__init__(parent)
        self.engine = engine
        self.channels = channels
        self.test_mode = test_mode
        self.process_audio = process_audio
        self.signals = SignalEmitter()
        self.is_cancelled = False
        
    def run(self):
        try:
            # Подготовка аудио
            if self.process_audio and not self.test_mode:
                self.signals.progress_updated.emit(0, "Подготовка аудио вариантов...")
                success = self.engine.prepare_audio_variants(self.channels)
                if not success or self.is_cancelled:
                    self.signals.generation_finished.emit(
                        False, "Ошибка подготовки аудио"
                    )
                    return
            
            # Генерация для каждого канала
            total_channels = len(self.channels)
            for i, channel in enumerate(self.channels):
                if self.is_cancelled:
                    break
                
                channel_progress = (i / total_channels) * 100
                self.signals.progress_updated.emit(
                    channel_progress,
                    f"Генерация канала {i+1}/{total_channels}: {channel.name}"
                )
                
                # Устанавливаем callback для прогресса внутри канала
                def channel_progress_callback(progress, message):
                    # Масштабируем прогресс канала
                    total_progress = channel_progress + (progress / total_channels)
                    self.signals.progress_updated.emit(total_progress, message)
                
                self.engine.set_progress_callback(channel_progress_callback)
                
                # Генерируем монтаж
                output_path = self.engine.generate_channel_montage(channel, self.test_mode)
                
                if not output_path:
                    self.signals.generation_finished.emit(
                        False, f"Ошибка генерации канала {channel.name}"
                    )
                    return
                
                self.signals.log_message.emit(
                    f"Канал '{channel.name}' готов: {output_path}", "info"
                )
            
            if self.is_cancelled:
                self.signals.generation_finished.emit(False, "Генерация отменена")
            else:
                self.signals.generation_finished.emit(
                    True, "Генерация завершена успешно!"
                )
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"Ошибка в потоке генерации: {error_details}")
            self.signals.error_occurred.emit(str(e))
            self.signals.generation_finished.emit(False, f"Ошибка: {str(e)}")
    
    def cancel(self):
        """Отменяет генерацию"""
        self.is_cancelled = True

# ==================== ГЛАВНОЕ ОКНО ====================

class AutoMontageMainWindow(QMainWindow):
    """Главное окно приложения"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Auto Montage Builder Pro - Enhanced Edition")
        self.setMinimumSize(1400, 900)
        
        # Инициализация
        self.data_manager = DataManager()
        self.channels = []
        self.settings = {}
        self.project_folder = None
        self.engine = None
        self.generation_thread = None
        
        # Применяем тему
        self.setStyleSheet(StyleManager.get_dark_theme())
        
        # Загружаем данные
        self.load_data()
        
        # Создаем интерфейс
        self.setup_ui()
        
        # Центрируем окно
        self.center_window()
        
        # Показываем приветствие
        self.show_welcome_message()
    
    def setup_ui(self):
        """Создает интерфейс"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок
        self.create_header(main_layout)
        
        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        
        # Создаем вкладки
        self.generation_tab = GenerationTab()
        self.generation_tab.generate_requested.connect(self.start_generation)
        self.tabs.addTab(self.generation_tab, "🎬 Генерация")
        
        self.channels_tab = ChannelsTab()
        self.channels_tab.channels_changed.connect(self.on_channels_changed)
        self.tabs.addTab(self.channels_tab, "📺 Каналы")
        
        self.effects_tab = EffectsTab()
        self.tabs.addTab(self.effects_tab, "🎨 Эффекты")
        
        self.capcut_tab = CapCutTab()
        self.tabs.addTab(self.capcut_tab, "✨ CapCut FX")
        
        self.overlays_tab = OverlaysTab()
        self.tabs.addTab(self.overlays_tab, "🎭 Оверлеи")
        
        self.settings_tab = SettingsTab()
        self.settings_tab.settings_changed.connect(self.save_settings)
        self.tabs.addTab(self.settings_tab, "⚙️ Настройки")
        
        main_layout.addWidget(self.tabs)
        
        # Статус бар
        self.create_status_bar()
        
        central_widget.setLayout(main_layout)
        
        # Передаем данные вкладкам
        self.update_tabs_data()
        
        # Подключаем сигналы
        self.connect_signals()
    
    def create_header(self, layout: QVBoxLayout):
        """Создает заголовок приложения"""
        header = QWidget()
        header.setObjectName("header")
        header.setStyleSheet("""
            #header {
                background-color: #0d0d0d;
                border-bottom: 2px solid #00d4aa;
            }
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        # Логотип и название
        logo_label = QLabel("🎬")
        logo_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(logo_label)
        
        title_label = QLabel("AUTO MONTAGE BUILDER PRO")
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #00d4aa;
            letter-spacing: 2px;
        """)
        header_layout.addWidget(title_label)
        
        version_label = QLabel("v5.0.0")
        version_label.setStyleSheet("color: #666; font-size: 14px;")
        header_layout.addWidget(version_label)
        
        header_layout.addStretch()
        
        # Кнопки быстрого доступа
        help_btn = QPushButton("❓")
        help_btn.setToolTip("Справка")
        help_btn.setFixedSize(32, 32)
        help_btn.clicked.connect(self.show_help)
        header_layout.addWidget(help_btn)
        
        about_btn = QPushButton("ℹ️")
        about_btn.setToolTip("О программе")
        about_btn.setFixedSize(32, 32)
        about_btn.clicked.connect(self.show_about)
        header_layout.addWidget(about_btn)
        
        header.setLayout(header_layout)
        layout.addWidget(header)
    
    def create_status_bar(self):
        """Создает статус бар"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Основное сообщение
        self.status_message = QLabel("Готов к работе")
        self.status_bar.addWidget(self.status_message)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        # Информация о проекте
        self.project_info = QLabel("Проект не выбран")
        self.status_bar.addPermanentWidget(self.project_info)
        
        self.status_bar.addPermanentWidget(QLabel(" | "))
        
        # Информация о ресурсах
        self.resource_info = QLabel("")
        self.status_bar.addPermanentWidget(self.resource_info)
        
        # Обновляем информацию о ресурсах
        self.update_resource_info()
        
        # Таймер для обновления ресурсов
        self.resource_timer = QTimer()
        self.resource_timer.timeout.connect(self.update_resource_info)
        self.resource_timer.start(5000)  # Каждые 5 секунд
    
    def connect_signals(self):
        """Подключает сигналы"""
        # Проект
        project_panel = self.generation_tab.get_project_info_panel()
        project_panel.folder_changed.connect(self.on_project_folder_changed)
        project_panel.scan_requested.connect(self.scan_project)
    
    def center_window(self):
        """Центрирует окно на экране"""
        screen = QApplication.primaryScreen().geometry()
        size = self.geometry()
        self.move(
            (screen.width() - size.width()) // 2,
            (screen.height() - size.height()) // 2
        )
    
    def load_data(self):
        """Загружает данные приложения"""
        # Загружаем каналы
        self.channels = self.data_manager.load_channels()
        
        # Загружаем настройки
        self.settings = self.data_manager.load_settings()
    
    def save_data(self):
        """Сохраняет данные приложения"""
        # Сохраняем каналы
        self.data_manager.save_channels(self.channels)
        
        # Сохраняем настройки
        self.data_manager.save_settings(self.settings)
    
    def update_tabs_data(self):
        """Обновляет данные во всех вкладках"""
        self.generation_tab.set_channels(self.channels)
        self.channels_tab.set_channels(self.channels)
        self.effects_tab.set_channels(self.channels)
        self.capcut_tab.set_channels(self.channels)
        self.overlays_tab.set_channels(self.channels)
        self.settings_tab.load_settings(self.settings)
    
    def on_channels_changed(self):
        """Обработчик изменения каналов"""
        # Получаем обновленные каналы из вкладки
        self.channels = self.channels_tab.channels
        self.save_data()
        self.update_tabs_data()
    
    def save_settings(self):
        """Сохраняет настройки"""
        self.settings = self.settings_tab.get_settings()
        self.save_data()
    
    def on_project_folder_changed(self, folder: str):
        """Обработчик изменения папки проекта"""
        self.project_folder = folder
        self.project_info.setText(f"Проект: {Path(folder).name}")
        
        # Создаем движок для проекта
        self.engine = MontageEngine(folder)
    
    def scan_project(self):
        """Сканирует проект"""
        if not self.engine:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите папку проекта")
            return
        
        project_panel = self.generation_tab.get_project_info_panel()
        include_videos = project_panel.get_include_videos()
        
        # Сканируем
        result = self.engine.scan_project_folder(include_videos)
        
        # Обновляем информацию
        project_panel.update_info(result)
        
        if result['pairs'] > 0:
            self.status_message.setText(f"Найдено пар файлов: {result['pairs']}")
        else:
            self.status_message.setText("Пары файлов не найдены")
    
    def start_generation(self, channels: List[Channel], test_mode: bool):
        """Запускает генерацию монтажа"""
        if not self.engine:
            QMessageBox.warning(self, "Предупреждение", "Сначала выберите папку проекта")
            return
        
        if not self.engine.media_pairs:
            QMessageBox.warning(self, "Предупреждение", "Не найдено пар файлов для монтажа")
            return
        
        # Проверяем настройки
        process_audio = self.generation_tab.get_process_audio_setting()
        
        # Запускаем в отдельном потоке
        self.generation_thread = GenerationThread(
            self.engine, channels, test_mode, process_audio
        )
        
        # Подключаем сигналы
        self.generation_thread.signals.progress_updated.connect(
            self.generation_tab.update_progress
        )
        self.generation_thread.signals.log_message.connect(
            self.generation_tab.add_log_message
        )
        self.generation_thread.signals.generation_finished.connect(
            self.on_generation_finished
        )
        self.generation_thread.signals.error_occurred.connect(
            self.on_generation_error
        )
        
        # Отключаем cancel
        cancel_btn = self.generation_tab.cancel_btn
        cancel_btn.clicked.connect(self.cancel_generation)
        
        # Запускаем
        self.generation_tab.start_generation()
        self.generation_thread.start()
        
        self.status_message.setText("Генерация монтажа...")
    
    def cancel_generation(self):
        """Отменяет генерацию"""
        if self.generation_thread and self.generation_thread.isRunning():
            self.generation_thread.cancel()
            self.generation_tab.add_log_message("Отмена генерации...", "warning")
    
    def on_generation_finished(self, success: bool, message: str):
        """Обработчик завершения генерации"""
        self.generation_tab.finish_generation()
        
        if success:
            self.generation_tab.add_log_message(message, "info")
            QMessageBox.information(self, "Успех", message)
            self.status_message.setText("Генерация завершена")
            
            # Открываем папку с рендерами
            if self.engine:
                renders_folder = self.engine.renders_folder
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(renders_folder)))
        else:
            self.generation_tab.add_log_message(message, "error")
            QMessageBox.critical(self, "Ошибка", message)
            self.status_message.setText("Ошибка генерации")
    
    def on_generation_error(self, error: str):
        """Обработчик ошибки генерации"""
        self.generation_tab.add_log_message(f"Критическая ошибка: {error}", "error")
    
    def update_resource_info(self):
        """Обновляет информацию о ресурсах"""
        from utils import SystemUtils, Converters
        
        # CPU
        cpu_count = SystemUtils.get_cpu_count()
        
        # Память
        mem_info = SystemUtils.get_memory_info()
        if mem_info['total'] > 0:
            mem_used = Converters.bytes_to_human(mem_info['used'])
            mem_total = Converters.bytes_to_human(mem_info['total'])
            mem_percent = mem_info['percent']
            
            self.resource_info.setText(
                f"CPU: {cpu_count} | "
                f"RAM: {mem_used}/{mem_total} ({mem_percent:.0f}%)"
            )
    
    def show_welcome_message(self):
        """Показывает приветственное сообщение"""
        if self.settings.get('show_welcome', True):
            welcome_text = """
            <h2>Добро пожаловать в Auto Montage Builder Pro!</h2>
            <p>Для начала работы:</p>
            <ol>
            <li>Выберите папку проекта с медиа файлами</li>
            <li>Создайте или выберите каналы для генерации</li>
            <li>Настройте эффекты и параметры</li>
            <li>Нажмите "Создать монтаж"</li>
            </ol>
            <p><b>Совет:</b> Используйте тестовый режим для быстрой проверки настроек!</p>
            """
            
            msg = QMessageBox(self)
            msg.setWindowTitle("Добро пожаловать!")
            msg.setTextFormat(Qt.RichText)
            msg.setText(welcome_text)
            msg.setIcon(QMessageBox.Information)
            
            # Добавляем чекбокс
            cb = QCheckBox("Не показывать при запуске")
            msg.setCheckBox(cb)
            
            msg.exec()
            
            if cb.isChecked():
                self.settings['show_welcome'] = False
                self.save_settings()
    
    def show_help(self):
        """Показывает справку"""
        help_text = """
        <h2>Справка по Auto Montage Builder Pro</h2>
        
        <h3>Подготовка файлов:</h3>
        <p>Файлы должны быть пронумерованы в формате:<br>
        <code>0001_image.jpg + 0001_audio.mp3</code><br>
        <code>0002_video.mp4 + 0002_audio.mp3</code></p>
        
        <h3>Горячие клавиши:</h3>
        <ul>
        <li><b>Ctrl+N</b> - Новый канал</li>
        <li><b>Ctrl+S</b> - Сохранить настройки</li>
        <li><b>Ctrl+G</b> - Начать генерацию</li>
        <li><b>F1</b> - Справка</li>
        </ul>
        
        <h3>Советы:</h3>
        <ul>
        <li>Используйте GPU ускорение для быстрой генерации</li>
        <li>Экспериментируйте с Ken Burns эффектами</li>
        <li>CapCut эффекты добавят динамики</li>
        <li>Сохраняйте пресеты для быстрого доступа</li>
        </ul>
        """
        
        QMessageBox.information(self, "Справка", help_text)
    
    def show_about(self):
        """Показывает окно "О программе"""""
        dialog = AboutDialog(self)
        dialog.exec()
    
    def closeEvent(self, event: QCloseEvent):
        """Обработчик закрытия окна"""
        # Проверяем, идет ли генерация
        if self.generation_thread and self.generation_thread.isRunning():
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Генерация еще не завершена. Вы уверены, что хотите выйти?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Отменяем генерацию
            self.generation_thread.cancel()
            self.generation_thread.wait()
        
        # Сохраняем данные
        self.save_data()
        
        # Сохраняем геометрию окна
        self.settings['window_geometry'] = self.saveGeometry().toBase64().data().decode()
        self.settings['window_state'] = self.saveState().toBase64().data().decode()
        self.save_settings()
        
        event.accept()
    
    def showEvent(self, event: QShowEvent):
        """Обработчик показа окна"""
        super().showEvent(event)
        
        # Восстанавливаем геометрию окна
        if 'window_geometry' in self.settings:
            try:
                geometry = QByteArray.fromBase64(
                    self.settings['window_geometry'].encode()
                )
                self.restoreGeometry(geometry)
            except:
                pass
        
        if 'window_state' in self.settings:
            try:
                state = QByteArray.fromBase64(
                    self.settings['window_state'].encode()
                )
                self.restoreState(state)
            except:
                pass

# ==================== ТОЧКА ВХОДА ====================

def main():
    """Главная функция приложения"""
    # Настройка логирования
    setup_logging()
    
    # Создаем приложение
    app = QApplication(sys.argv)
    
    # Настройка приложения
    app.setApplicationName("Auto Montage Builder Pro")
    app.setApplicationVersion("5.0.0")
    app.setOrganizationName("AutoMontage Team")
    
    # Настройка иконки (если есть)
    icon_path = Path(__file__).parent / "icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Создаем главное окно
    window = AutoMontageMainWindow()
    window.show()
    
    # Запускаем приложение
    sys.exit(app.exec())

if __name__ == "__main__":
    main()