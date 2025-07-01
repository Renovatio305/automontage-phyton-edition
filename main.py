#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Montage Builder Pro - Enhanced Python Edition
Точка входа приложения

Автор: AutoMontage Team
Версия: 5.0.0
"""

import sys
import os
from pathlib import Path

# Добавляем текущую директорию в путь поиска модулей
sys.path.insert(0, str(Path(__file__).parent))

# Проверяем зависимости
def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    missing_deps = []
    
    # Проверяем PySide6
    try:
        import PySide6
    except ImportError:
        missing_deps.append("PySide6")
    
    # Проверяем numpy (опционально)
    try:
        import numpy
    except ImportError:
        print("Предупреждение: numpy не установлен. Некоторые функции могут быть недоступны.")
    
    if missing_deps:
        print(f"Ошибка: Отсутствуют необходимые зависимости: {', '.join(missing_deps)}")
        print("\nУстановите их с помощью команды:")
        print(f"pip install {' '.join(missing_deps)}")
        sys.exit(1)

# Проверяем FFmpeg
def check_ffmpeg():
    """Проверяет наличие FFmpeg"""
    from utils import FFmpegUtils
    
    if not FFmpegUtils.check_ffmpeg_installed():
        print("Предупреждение: FFmpeg не найден в системе!")
        print("Скачайте FFmpeg с https://ffmpeg.org/download.html")
        print("и добавьте его в PATH или поместите в папку с программой.")
        
        # Показываем диалог
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)
            QMessageBox.warning(
                None, 
                "FFmpeg не найден",
                "FFmpeg не найден в системе!\n\n"
                "Скачайте FFmpeg с https://ffmpeg.org/download.html\n"
                "и добавьте его в PATH или поместите в папку с программой."
            )
        except:
            pass

# Главная функция
def main():
    """Главная функция приложения"""
    # Проверяем зависимости
    check_dependencies()
    
    # Проверяем FFmpeg
    check_ffmpeg()
    
    # Импортируем и запускаем главное окно
    from main_window import main as run_app
    run_app()

if __name__ == "__main__":
    main()