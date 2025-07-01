# 🎬 Auto Montage Builder Pro - Enhanced Python Edition

Профессиональный инструмент для автоматического создания видеомонтажа с продвинутыми эффектами и GPU-ускорением.

## 📋 Возможности

- ✅ **Автоматическая расстановка файлов на таймлайне**
- 🎥 **Поддержка видео файлов с зацикливанием**
- 🎬 **Ken Burns эффекты** с плавной анимацией (60 FPS)
- ✨ **CapCut-style эффекты** и анимации
- 🔄 **Продвинутые переходы** между клипами
- 🌑 **Fade In/Out эффекты**
- 🎯 **3D Parallax эффекты** (экспериментально)
- 🎭 **Видео и изображения оверлеи**
- 🎵 **Обработка аудио** с эффектами
- ⚡ **GPU ускорение** (NVIDIA, AMD, Intel)
- 🎨 **Современный интерфейс** на PySide6

## 🚀 Быстрый старт

### Требования

- Python 3.8+
- FFmpeg 4.0+
- 8 GB RAM (рекомендуется 16 GB)
- GPU с поддержкой аппаратного кодирования (опционально)

### Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/automontage/automontage-pro.git
cd automontage-pro
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Установите FFmpeg:
- **Windows**: Скачайте с [ffmpeg.org](https://ffmpeg.org/download.html) и добавьте в PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg` или `sudo yum install ffmpeg`

4. Запустите приложение:
```bash
python main.py
```

## 📁 Структура проекта

```
automontage-pro/
├── main.py              # Точка входа
├── models.py            # Модели данных
├── utils.py             # Утилиты
├── filters.py           # FFmpeg фильтры
├── engine.py            # Движок монтажа
├── gui_base.py          # Базовые GUI компоненты
├── gui_widgets.py       # Специализированные виджеты
├── gui_tabs.py          # Вкладки интерфейса
├── main_window.py       # Главное окно
├── requirements.txt     # Зависимости
└── README.md           # Документация
```

## 📖 Использование

### 1. Подготовка файлов

Организуйте файлы в папке проекта следующим образом:
```
project_folder/
├── 0001_image.jpg      # Изображение 1
├── 0001_audio.mp3      # Аудио для изображения 1
├── 0002_video.mp4      # Видео 2
├── 0002_audio.mp3      # Аудио для видео 2
├── 0003_image.png      # Изображение 3
├── 0003_audio.mp3      # Аудио для изображения 3
└── ...
```

**Важно**: Первые 4 цифры в имени файла определяют пару медиа + аудио.

### 2. Создание канала

1. Откройте вкладку **"Каналы"**
2. Нажмите **"➕ Создать канал"**
3. Выберите шаблон (YouTube, Shorts, Instagram, Cinematic)
4. Настройте параметры экспорта

### 3. Настройка эффектов

#### Ken Burns эффекты
- **Zoom In/Out** - плавное приближение/отдаление
- **Pan** - движение по изображению
- **Rotate** - вращение
- **Parallax** - эффект параллакса

#### CapCut эффекты
- **Zoom Burst** - резкий зум с затуханием
- **Pulse** - пульсация
- **Shake** - тряска камеры
- **Glitch** - цифровые помехи

### 4. Генерация монтажа

1. Выберите папку проекта
2. Нажмите **"🔍 Сканировать"**
3. Выберите каналы для генерации
4. Нажмите **"🎬 СОЗДАТЬ МОНТАЖ"**

## 🎨 Примеры настроек

### YouTube канал (16:9)
```json
{
  "resolution": "1920x1080",
  "fps": 30,
  "bitrate": 8,
  "effects": {
    "ken_burns": ["zoomIn", "panRight"],
    "transitions": ["fade", "dissolve"],
    "color_filter": "cinematic"
  }
}
```

### Shorts/Reels (9:16)
```json
{
  "resolution": "1080x1920",
  "fps": 30,
  "bitrate": 10,
  "effects": {
    "ken_burns": ["zoomIn", "zoomOut"],
    "capcut_effects": ["zoomBurst", "shake"],
    "transitions": ["zoom", "slide"]
  }
}
```

## ⚙️ Продвинутые настройки

### GPU ускорение

Приложение автоматически определяет доступные GPU:
- **NVIDIA**: h264_nvenc, hevc_nvenc
- **AMD**: h264_amf, hevc_amf
- **Intel**: h264_qsv, hevc_qsv

### Обработка аудио

Доступные эффекты:
- Изменение тональности: от -3 до +3 полутонов
- Эффекты: bass, reverb, echo, chorus, telephone, underwater, radio, vintage
- Нормализация громкости
- Компрессор и лимитер

### Оверлеи

Поддерживаемые форматы:
- PNG с альфа-каналом
- Анимированные GIF
- Видео (MP4, MOV)

Режимы наложения:
- Screen (экран)
- Overlay (перекрытие)
- Multiply (умножение)
- Add (сложение)

## 🛠️ Решение проблем

### FFmpeg не найден
```bash
# Windows
set PATH=%PATH%;C:\path\to\ffmpeg\bin

# macOS/Linux
export PATH=$PATH:/path/to/ffmpeg/bin
```

### Ошибка импорта PySide6
```bash
pip install --upgrade PySide6
```

### Недостаточно памяти
- Уменьшите разрешение экспорта
- Отключите Motion Blur
- Используйте пресет "Быстро"

## 📊 Производительность

### Рекомендуемые настройки по производительности

| Система | Качество | Настройки |
|---------|----------|-----------|
| Слабая (< 8GB RAM) | Быстро | 720p, без motion blur |
| Средняя (8-16GB RAM) | Баланс | 1080p, базовые эффекты |
| Мощная (> 16GB RAM + GPU) | Максимум | 4K, все эффекты |

### Время генерации (примерно)

| Количество пар | 720p | 1080p | 4K |
|----------------|------|-------|-----|
| 10 | 2-3 мин | 3-5 мин | 8-12 мин |
| 50 | 10-15 мин | 15-25 мин | 40-60 мин |
| 100 | 20-30 мин | 30-50 мин | 80-120 мин |

*С GPU ускорением время сокращается на 40-60%*

## 🤝 Вклад в проект

Мы приветствуем вклад в развитие проекта! 

### Как помочь:
1. Fork репозитория
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

### Идеи для улучшений:
- [ ] AI-powered scene detection
- [ ] Больше переходов и эффектов
- [ ] Поддержка плагинов
- [ ] Веб-интерфейс
- [ ] Мобильное приложение

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 👥 Авторы

- **AutoMontage Team** - *Основная разработка*

## 🙏 Благодарности

- FFmpeg команде за отличный инструмент
- Qt/PySide6 за прекрасный GUI фреймворк
- Всем контрибьюторам и пользователям

## 📞 Контакты

- Email: automontage@support.com
- GitHub: [github.com/automontage](https://github.com/automontage)
- Discord: [discord.gg/automontage](https://discord.gg/automontage)

---

**Сделано с ❤️ AutoMontage Team**